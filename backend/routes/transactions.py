"""
Transaction management routes
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import uuid
from io import BytesIO

from sqlalchemy import select, delete, func
from database import async_session, Transaction, PricingRule, PricingGroup, User

from routes.auth import get_current_user, require_role, UserResponse

router = APIRouter(prefix="/transactions", tags=["Transactions"])


# Pydantic Models
class TransactionResponse(BaseModel):
    id: str
    tx_id: str
    station: str
    connector: str
    connector_type: Optional[str] = None
    account: str
    start_time: str
    end_time: str
    meter_value: float
    charging_duration: Optional[str] = None
    cost: float
    payment_status: str = "UNPAID"
    payment_type: Optional[str] = None
    payment_date: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class TransactionCreate(BaseModel):
    tx_id: str
    station: str
    connector: str
    connector_type: Optional[str] = None
    account: str
    start_time: str
    end_time: str
    meter_value: float


class TransactionUpdate(BaseModel):
    station: Optional[str] = None
    connector: Optional[str] = None
    connector_type: Optional[str] = None
    account: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    meter_value: Optional[float] = None
    payment_status: Optional[str] = None
    payment_type: Optional[str] = None
    payment_date: Optional[str] = None


class BulkDeleteRequest(BaseModel):
    ids: List[str]


class ImportValidationError(BaseModel):
    row: int
    field: str
    message: str


class ImportResult(BaseModel):
    success: bool
    imported_count: int
    skipped_count: int
    errors: List[ImportValidationError]


class TransactionImportItem(BaseModel):
    TxID: str
    Station: str
    Connector: str
    Account: str
    Start_Time: Optional[str] = None
    End_Time: Optional[str] = None
    Meter_value_kWh: Optional[float] = None
    
    class Config:
        extra = 'allow'  # Allow extra fields to be ignored


class TransactionImportRequest(BaseModel):
    transactions: List[dict]  # Accept raw dict to handle various column names


def calculate_charging_duration(start_time: str, end_time: str) -> str:
    """Calculate duration between start and end times"""
    try:
        start = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        end = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        duration = end - start
        hours = duration.seconds // 3600
        minutes = (duration.seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    except:
        return "N/A"


async def deduct_rfid_balance(account: str, cost: float) -> dict:
    """
    Deduct cost from user's RFID balance based on account.
    Account can be user's name, email, or RFID card number.
    Returns dict with deduction status.
    """
    if cost <= 0:
        return {"deducted": False, "reason": "No cost to deduct"}
    
    async with async_session() as session:
        # Try to find user by RFID card number, name, or email
        result = await session.execute(
            select(User).where(
                (User.rfid_card_number == account) |
                (User.name == account) |
                (User.email == account)
            )
        )
        user = result.scalar_one_or_none()
        
        if not user:
            return {"deducted": False, "reason": "User not found"}
        
        if not user.rfid_card_number:
            return {"deducted": False, "reason": "User has no RFID card"}
        
        if user.rfid_status != "active":
            return {"deducted": False, "reason": f"RFID card is {user.rfid_status}"}
        
        current_balance = user.rfid_balance or 0
        if current_balance < cost:
            return {
                "deducted": False, 
                "reason": f"Insufficient balance: {current_balance} < {cost}",
                "user_id": user.id,
                "balance": current_balance
            }
        
        # Deduct balance
        user.rfid_balance = current_balance - cost
        await session.commit()
        
        return {
            "deducted": True,
            "user_id": user.id,
            "previous_balance": current_balance,
            "new_balance": user.rfid_balance,
            "amount_deducted": cost
        }


async def get_pricing(account: str, connector: str, connector_type: Optional[str] = None, user_id: Optional[str] = None) -> float:
    """
    Get price per kWh based on account, connector type, and user's pricing group.
    
    Default pricing (PORTERIA):
    - CCS = 2500 COP/kWh
    - CHADEMO = 2000 COP/kWh
    - J1772 = 1500 COP/kWh
    - Default = 500 COP/kWh
    """
    # Default pricing by connector type
    DEFAULT_CONNECTOR_PRICING = {
        'CCS': 2500.0,
        'CCS2': 2500.0,
        'CHADEMO': 2000.0,
        'J1772': 1500.0,
        'TYPE2': 1500.0,
        'Type2': 1500.0,
    }
    
    # Normalize connector type for matching
    connector_normalized = (connector or '').upper().strip()
    connector_type_normalized = (connector_type or '').upper().strip()
    
    # Check which one to use for pricing
    pricing_key = connector_type_normalized or connector_normalized
    
    async with async_session() as session:
        # First, try to find user by account and check their pricing group
        user_result = await session.execute(
            select(User).where(
                (User.name == account) |
                (User.email == account) |
                (User.rfid_card_number == account)
            )
        )
        user = user_result.scalar_one_or_none()
        
        if user and user.pricing_group_id:
            # Get user's pricing group
            group_result = await session.execute(
                select(PricingGroup).where(PricingGroup.id == user.pricing_group_id)
            )
            group = group_result.scalar_one_or_none()
            if group and group.connector_pricing:
                # Check for exact match in pricing group
                for key, price in group.connector_pricing.items():
                    if key.upper() == pricing_key:
                        return float(price)
        
        # Check for custom pricing rules
        result = await session.execute(
            select(PricingRule).where(
                PricingRule.account == account,
                PricingRule.connector == connector
            )
        )
        pricing = result.scalar_one_or_none()
        if pricing:
            return pricing.price_per_kwh
        
        # Check for account-level default pricing
        result = await session.execute(
            select(PricingRule).where(
                PricingRule.account == account,
                PricingRule.connector == "*"
            )
        )
        pricing = result.scalar_one_or_none()
        if pricing:
            return pricing.price_per_kwh
        
        # Use default connector type pricing
        for key, price in DEFAULT_CONNECTOR_PRICING.items():
            if key.upper() == pricing_key:
                return price
        
        # Default fallback for unknown connector types
        return 2000.0


def transaction_to_response(tx: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=tx.id,
        tx_id=tx.tx_id,
        station=tx.station,
        connector=tx.connector,
        connector_type=tx.connector_type,
        account=tx.account,
        start_time=tx.start_time or "",
        end_time=tx.end_time or "",
        meter_value=tx.meter_value or 0,
        charging_duration=tx.charging_duration,
        cost=tx.cost or 0,
        payment_status=tx.payment_status or "UNPAID",
        payment_type=tx.payment_type,
        payment_date=tx.payment_date,
        created_at=tx.created_at.isoformat() if tx.created_at else ""
    )


# Routes
@router.get("", response_model=List[TransactionResponse])
async def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    station: Optional[str] = None,
    account: Optional[str] = None,
    payment_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get transactions with optional filtering"""
    async with async_session() as session:
        query = select(Transaction)
        
        if station:
            query = query.where(Transaction.station == station)
        if account:
            query = query.where(Transaction.account == account)
        if payment_status:
            query = query.where(Transaction.payment_status == payment_status)
        if start_date:
            query = query.where(Transaction.start_time >= start_date)
        if end_date:
            query = query.where(Transaction.start_time <= end_date)
        
        query = query.order_by(Transaction.start_time.desc())
        query = query.offset(skip).limit(limit)
        
        result = await session.execute(query)
        transactions = result.scalars().all()
        
        return [transaction_to_response(tx) for tx in transactions]


@router.post("", response_model=TransactionResponse)
async def create_transaction(
    tx_data: TransactionCreate,
    current_user: UserResponse = Depends(require_role("admin", "user"))
):
    """Create a new transaction and deduct from RFID balance if applicable"""
    price_per_kwh = await get_pricing(tx_data.account, tx_data.connector, tx_data.connector_type)
    cost = tx_data.meter_value * price_per_kwh
    charging_duration = calculate_charging_duration(tx_data.start_time, tx_data.end_time)
    
    # Determine payment status based on RFID balance deduction
    payment_status = "UNPAID"
    deduction_result = await deduct_rfid_balance(tx_data.account, round(cost, 2))
    
    if deduction_result.get("deducted"):
        payment_status = "PAID"
    
    async with async_session() as session:
        new_tx = Transaction(
            id=str(uuid.uuid4()),
            tx_id=tx_data.tx_id,
            station=tx_data.station,
            connector=tx_data.connector,
            connector_type=tx_data.connector_type,
            account=tx_data.account,
            start_time=tx_data.start_time,
            end_time=tx_data.end_time,
            meter_value=tx_data.meter_value,
            charging_duration=charging_duration,
            cost=round(cost, 2),
            payment_status=payment_status
        )
        session.add(new_tx)
        await session.commit()
        await session.refresh(new_tx)
        
        return transaction_to_response(new_tx)


@router.patch("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    tx_data: TransactionUpdate,
    current_user: UserResponse = Depends(require_role("admin", "user"))
):
    """Update a transaction"""
    async with async_session() as session:
        result = await session.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        tx = result.scalar_one_or_none()
        
        if not tx:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        # Update fields
        for field, value in tx_data.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(tx, field, value)
        
        # Recalculate cost if needed
        if any([tx_data.meter_value, tx_data.account, tx_data.connector, tx_data.connector_type]):
            meter_value = tx_data.meter_value or tx.meter_value
            account = tx_data.account or tx.account
            connector = tx_data.connector or tx.connector
            connector_type = tx_data.connector_type or tx.connector_type
            
            price_per_kwh = await get_pricing(account, connector, connector_type)
            tx.cost = round(meter_value * price_per_kwh, 2)
        
        # Recalculate duration if times changed
        if tx_data.start_time or tx_data.end_time:
            start_time = tx_data.start_time or tx.start_time
            end_time = tx_data.end_time or tx.end_time
            tx.charging_duration = calculate_charging_duration(start_time, end_time)
        
        await session.commit()
        await session.refresh(tx)
        
        return transaction_to_response(tx)


@router.delete("/{transaction_id}")
async def delete_transaction(
    transaction_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Delete a transaction (Admin only)"""
    async with async_session() as session:
        result = await session.execute(
            delete(Transaction).where(Transaction.id == transaction_id)
        )
        await session.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Transaction not found")
        
        return {"message": "Transaction deleted successfully"}


@router.post("/bulk-delete")
async def bulk_delete_transactions(
    request: BulkDeleteRequest,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Delete multiple transactions (Admin only)"""
    if not request.ids:
        raise HTTPException(status_code=400, detail="No transaction IDs provided")
    
    if len(request.ids) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 transactions can be deleted at once")
    
    async with async_session() as session:
        result = await session.execute(
            delete(Transaction).where(Transaction.id.in_(request.ids))
        )
        await session.commit()
        
        return {
            "message": f"Successfully deleted {result.rowcount} transaction(s)",
            "deleted_count": result.rowcount
        }


@router.post("/import", response_model=ImportResult)
async def import_transactions(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(require_role("admin", "user"))
):
    """
    Import transactions from Excel file.
    Required columns: TxID, Station, Connector, Account, Start Time, End Time, Meter value(kW.h)
    All other columns are ignored. Duplicates (same TxID) are skipped.
    """
    import pandas as pd
    
    # Validate file extension
    filename = file.filename.lower()
    if not (filename.endswith('.xlsx') or filename.endswith('.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")
    
    # Read file content
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
    
    # Normalize column names - strip whitespace and convert to lowercase for matching
    df.columns = df.columns.str.strip()
    original_columns = list(df.columns)
    
    # Create a mapping from various possible column names to standard names
    column_aliases = {
        'txid': 'TxID',
        'tx_id': 'TxID',
        'transaction_id': 'TxID',
        'transactionid': 'TxID',
        'station': 'Station',
        'charger': 'Station',
        'charger_id': 'Station',
        'connector': 'Connector',
        'connector_id': 'Connector',
        'account': 'Account',
        'user': 'Account',
        'rfid': 'Account',
        'start time': 'Start Time',
        'starttime': 'Start Time',
        'start_time': 'Start Time',
        'end time': 'End Time',
        'endtime': 'End Time',
        'end_time': 'End Time',
        'meter value(kw.h)': 'Meter value(kW.h)',
        'meter value (kw.h)': 'Meter value(kW.h)',
        'metervalue(kw.h)': 'Meter value(kW.h)',
        'meter value': 'Meter value(kW.h)',
        'metervalue': 'Meter value(kW.h)',
        'energy': 'Meter value(kW.h)',
        'energy (kwh)': 'Meter value(kW.h)',
        'energy(kwh)': 'Meter value(kW.h)',
        'kwh': 'Meter value(kW.h)',
        'kw.h': 'Meter value(kW.h)',
    }
    
    # Build rename mapping
    rename_map = {}
    for col in original_columns:
        col_lower = col.lower().strip()
        if col_lower in column_aliases:
            rename_map[col] = column_aliases[col_lower]
    
    # Apply renaming
    if rename_map:
        df = df.rename(columns=rename_map)
    
    # Check required columns
    required = ['TxID', 'Station', 'Connector', 'Account', 'Start Time', 'End Time', 'Meter value(kW.h)']
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing)}. Found: {', '.join(df.columns.tolist())}"
        )
    
    # Process rows
    errors = []
    imported = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel row number (1-indexed + header)
        
        # Get TxID
        tx_id_raw = row['TxID']
        if pd.isna(tx_id_raw) or str(tx_id_raw).strip() == '':
            errors.append(ImportValidationError(row=row_num, field="TxID", message="TxID is required"))
            continue
        tx_id = str(tx_id_raw).strip()
        
        # Get meter value
        meter_raw = row['Meter value(kW.h)']
        try:
            if pd.isna(meter_raw):
                meter_value = 0.0
            elif isinstance(meter_raw, str):
                # Handle comma decimal separator
                meter_value = float(meter_raw.replace(',', '.').strip())
            else:
                meter_value = float(meter_raw)
        except (ValueError, TypeError):
            errors.append(ImportValidationError(row=row_num, field="Meter value", message=f"Invalid number: {meter_raw}"))
            continue
        
        # Skip zero meter value
        if meter_value == 0:
            skipped += 1
            continue
        
        # Check for duplicate TxID
        async with async_session() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.tx_id == tx_id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                skipped += 1
                continue
            
            # Extract other fields with safe defaults
            station = str(row['Station']).strip() if not pd.isna(row['Station']) else ""
            connector = str(row['Connector']).strip() if not pd.isna(row['Connector']) else ""
            account = str(row['Account']).strip() if not pd.isna(row['Account']) else ""
            start_time = str(row['Start Time']).strip() if not pd.isna(row['Start Time']) else ""
            end_time = str(row['End Time']).strip() if not pd.isna(row['End Time']) else ""
            
            # Calculate pricing and duration
            price_per_kwh = await get_pricing(account, connector, None)
            cost = round(meter_value * price_per_kwh, 2)
            duration = calculate_charging_duration(start_time, end_time)
            
            # Create transaction
            new_tx = Transaction(
                id=str(uuid.uuid4()),
                tx_id=tx_id,
                station=station,
                connector=connector,
                account=account,
                start_time=start_time,
                end_time=end_time,
                meter_value=meter_value,
                charging_duration=duration,
                cost=cost,
                payment_status="UNPAID"
            )
            
            session.add(new_tx)
            await session.commit()
            imported += 1
    
    return ImportResult(
        success=len(errors) == 0,
        imported_count=imported,
        skipped_count=skipped,
        errors=errors
    )


@router.post("/import-json", response_model=ImportResult)
async def import_transactions_json(
    request: TransactionImportRequest,
    current_user: UserResponse = Depends(require_role("admin", "user"))
):
    """
    Import transactions from JSON (parsed Excel data from frontend).
    Required fields: TxID, Station, Connector, Account, Start Time, End Time, Meter value(kW.h)
    Duplicates (same TxID) are skipped.
    """
    errors = []
    imported = 0
    skipped = 0
    
    for idx, row in enumerate(request.transactions):
        row_num = idx + 2  # Excel row number
        
        # Get TxID
        tx_id = str(row.get('TxID', '')).strip()
        if not tx_id:
            errors.append(ImportValidationError(row=row_num, field="TxID", message="TxID is required"))
            continue
        
        # Get meter value
        meter_raw = row.get('Meter value(kW.h)', 0)
        try:
            if isinstance(meter_raw, str):
                meter_value = float(meter_raw.replace(',', '.').strip()) if meter_raw.strip() else 0.0
            else:
                meter_value = float(meter_raw) if meter_raw else 0.0
        except (ValueError, TypeError):
            errors.append(ImportValidationError(row=row_num, field="Meter value", message=f"Invalid number: {meter_raw}"))
            continue
        
        # Skip zero meter value
        if meter_value == 0:
            skipped += 1
            continue
        
        # Check for duplicate
        async with async_session() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.tx_id == tx_id)
            )
            if result.scalar_one_or_none():
                skipped += 1
                continue
            
            # Extract fields
            station = str(row.get('Station', '')).strip()
            connector = str(row.get('Connector', '')).strip()
            account = str(row.get('Account', '')).strip()
            start_time = str(row.get('Start Time', '')).strip()
            end_time = str(row.get('End Time', '')).strip()
            
            # Calculate pricing and duration
            price_per_kwh = await get_pricing(account, connector, None)
            cost = round(meter_value * price_per_kwh, 2)
            duration = calculate_charging_duration(start_time, end_time)
            
            # Try to deduct from RFID balance
            payment_status = "UNPAID"
            deduction_result = await deduct_rfid_balance(account, cost)
            if deduction_result.get("deducted"):
                payment_status = "PAID"
            
            # Create transaction
            new_tx = Transaction(
                id=str(uuid.uuid4()),
                tx_id=tx_id,
                station=station,
                connector=connector,
                account=account,
                start_time=start_time,
                end_time=end_time,
                meter_value=meter_value,
                charging_duration=duration,
                cost=cost,
                payment_status=payment_status
            )
            
            session.add(new_tx)
            await session.commit()
            imported += 1
    
    return ImportResult(
        success=len(errors) == 0,
        imported_count=imported,
        skipped_count=skipped,
        errors=errors
    )
