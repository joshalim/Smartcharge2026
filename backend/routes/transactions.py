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

# Default pricing
CONNECTOR_TYPE_PRICING = {
    "CCS2": 2500.0,
    "CHADEMO": 2000.0,
    "J1772": 1500.0
}
SPECIAL_ACCOUNTS = ["PORTERIA", "Jorge Iluminacion", "John Iluminacion"]


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


async def get_pricing(account: str, connector: str, connector_type: Optional[str] = None, user_id: Optional[str] = None) -> float:
    """Get price per kWh based on account, connector, and user's pricing group"""
    
    async with async_session() as session:
        # Check if user has a pricing group assigned
        if user_id:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            if user and user.pricing_group_id:
                group_result = await session.execute(
                    select(PricingGroup).where(PricingGroup.id == user.pricing_group_id)
                )
                group = group_result.scalar_one_or_none()
                if group and group.connector_pricing and connector_type:
                    if connector_type in group.connector_pricing:
                        return group.connector_pricing[connector_type]
        
        # Check if account is in special group
        if account in SPECIAL_ACCOUNTS:
            if connector_type and connector_type in CONNECTOR_TYPE_PRICING:
                return CONNECTOR_TYPE_PRICING[connector_type]
            return 500.0
        
        # Check for custom pricing
        result = await session.execute(
            select(PricingRule).where(
                PricingRule.account == account,
                PricingRule.connector == connector
            )
        )
        pricing = result.scalar_one_or_none()
        if pricing:
            return pricing.price_per_kwh
        
        # Check for default pricing
        result = await session.execute(
            select(PricingRule).where(
                PricingRule.account == account,
                PricingRule.connector == "default"
            )
        )
        default_pricing = result.scalar_one_or_none()
        if default_pricing:
            return default_pricing.price_per_kwh
        
        # Fall back to connector type pricing
        if connector_type and connector_type in CONNECTOR_TYPE_PRICING:
            return CONNECTOR_TYPE_PRICING[connector_type]
        
        return 500.0


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
    """Create a new transaction"""
    price_per_kwh = await get_pricing(tx_data.account, tx_data.connector, tx_data.connector_type)
    cost = tx_data.meter_value * price_per_kwh
    charging_duration = calculate_charging_duration(tx_data.start_time, tx_data.end_time)
    
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
            payment_status="UNPAID"
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
    """Import transactions from Excel file. 
    Required columns: TxID, Station, Connector, Account, Start Time, End Time, Meter value(kW.h)
    All other columns are ignored.
    """
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")
    
    try:
        import pandas as pd
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
    
    # Define required columns with flexible matching (case-insensitive, space-insensitive)
    required_columns = {
        'txid': 'TxID',
        'station': 'Station', 
        'connector': 'Connector',
        'account': 'Account',
        'start time': 'Start Time',
        'starttime': 'Start Time',
        'end time': 'End Time',
        'endtime': 'End Time',
        'meter value(kw.h)': 'Meter value(kW.h)',
        'metervalue(kw.h)': 'Meter value(kW.h)',
        'meter value (kw.h)': 'Meter value(kW.h)',
        'meter value': 'Meter value(kW.h)',
        'metervalue': 'Meter value(kW.h)',
        'kwh': 'Meter value(kW.h)',
        'kw.h': 'Meter value(kW.h)',
        'energy': 'Meter value(kW.h)',
        'energy (kwh)': 'Meter value(kW.h)',
        'energy(kwh)': 'Meter value(kW.h)',
    }
    
    # Normalize dataframe columns - create mapping from original to standard names
    df_columns_lower = {col.lower().strip(): col for col in df.columns}
    column_mapping = {}
    found_columns = set()
    
    for df_col_lower, df_col_orig in df_columns_lower.items():
        if df_col_lower in required_columns:
            standard_name = required_columns[df_col_lower]
            column_mapping[df_col_orig] = standard_name
            found_columns.add(standard_name)
    
    # Apply column renaming
    if column_mapping:
        df = df.rename(columns=column_mapping)
    
    # Check for missing required columns
    required_standard = {'TxID', 'Station', 'Connector', 'Account', 'Start Time', 'End Time', 'Meter value(kW.h)'}
    missing_columns = required_standard - found_columns
    
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(sorted(missing_columns))}. Found columns: {', '.join(df.columns.tolist())}"
        )
    
    errors = []
    imported = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel row (1-indexed + header)
        
        # Parse meter value
        try:
            meter_value_raw = row['Meter value(kW.h)']
            if pd.isna(meter_value_raw):
                meter_value = 0.0
            else:
                # Handle string values with commas (European format)
                if isinstance(meter_value_raw, str):
                    meter_value_raw = meter_value_raw.replace(',', '.').strip()
                meter_value = float(meter_value_raw)
        except (ValueError, TypeError) as e:
            errors.append(ImportValidationError(
                row=row_num,
                field="Meter value(kW.h)",
                message=f"Invalid number format: {row['Meter value(kW.h)']}"
            ))
            continue
        
        # Skip rows with 0 meter value
        if meter_value == 0:
            skipped += 1
            continue
        
        # Validate TxID
        if pd.isna(row['TxID']) or str(row['TxID']).strip() == '':
            errors.append(ImportValidationError(
                row=row_num,
                field="TxID",
                message="TxID is required"
            ))
            continue
        
        tx_id = str(row['TxID']).strip()
        
        async with async_session() as session:
            # Check if transaction already exists
            result = await session.execute(
                select(Transaction).where(Transaction.tx_id == tx_id)
            )
            if result.scalar_one_or_none():
                skipped += 1
                continue
            
            # Extract values with safe defaults
            account = str(row['Account']).strip() if not pd.isna(row['Account']) else ""
            connector = str(row['Connector']).strip() if not pd.isna(row['Connector']) else ""
            station = str(row['Station']).strip() if not pd.isna(row['Station']) else ""
            
            # Connector type is optional - check if present
            connector_type = None
            if 'Connector Type' in df.columns and not pd.isna(row.get('Connector Type')):
                connector_type = str(row['Connector Type']).strip()
            
            # Calculate pricing
            price_per_kwh = await get_pricing(account, connector, connector_type)
            cost = meter_value * price_per_kwh
            
            # Parse times
            start_time = str(row['Start Time']) if not pd.isna(row['Start Time']) else ""
            end_time = str(row['End Time']) if not pd.isna(row['End Time']) else ""
            charging_duration = calculate_charging_duration(start_time, end_time)
            
            # Create transaction
            new_tx = Transaction(
                id=str(uuid.uuid4()),
                tx_id=tx_id,
                station=station,
                connector=connector,
                connector_type=connector_type,
                account=account,
                start_time=start_time,
                end_time=end_time,
                meter_value=meter_value,
                charging_duration=charging_duration,
                cost=round(cost, 2),
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
