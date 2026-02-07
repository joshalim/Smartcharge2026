"""
RFID Card management routes
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
import uuid
from io import BytesIO

from sqlalchemy import select, delete, func
from database import async_session, RFIDCard, RFIDHistory, User

from routes.auth import get_current_user, require_role, UserResponse

router = APIRouter(prefix="/rfid-cards", tags=["RFID Cards"])


# Pydantic Models
class RFIDCardResponse(BaseModel):
    id: str
    card_number: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    balance: float
    status: str
    is_active: bool
    created_at: str

    class Config:
        from_attributes = True


class RFIDCardCreate(BaseModel):
    card_number: str
    user_id: Optional[str] = None
    balance: float = 0


class RFIDCardUpdate(BaseModel):
    user_id: Optional[str] = None
    balance: Optional[float] = None
    status: Optional[str] = None
    is_active: Optional[bool] = None


class TopUpRequest(BaseModel):
    amount: float
    notes: Optional[str] = None


class RFIDHistoryResponse(BaseModel):
    id: str
    card_id: str
    transaction_type: str
    amount: float
    balance_before: float
    balance_after: float
    notes: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class RFIDImportResult(BaseModel):
    imported: int
    skipped: int
    errors: List[dict]


# Routes
@router.get("", response_model=List[RFIDCardResponse])
async def get_rfid_cards(current_user: UserResponse = Depends(get_current_user)):
    """Get all RFID cards"""
    async with async_session() as session:
        result = await session.execute(
            select(RFIDCard).order_by(RFIDCard.created_at.desc())
        )
        cards = result.scalars().all()
        
        response = []
        for card in cards:
            user_name = None
            if card.user_id:
                user_result = await session.execute(
                    select(User).where(User.id == card.user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    user_name = user.name
            
            response.append(RFIDCardResponse(
                id=card.id,
                card_number=card.card_number,
                user_id=card.user_id,
                user_name=user_name,
                balance=card.balance or 0,
                status=card.status or "active",
                is_active=card.is_active if card.is_active is not None else True,
                created_at=card.created_at.isoformat() if card.created_at else ""
            ))
        
        return response


@router.get("/{card_id}", response_model=RFIDCardResponse)
async def get_rfid_card(
    card_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get a single RFID card"""
    async with async_session() as session:
        result = await session.execute(
            select(RFIDCard).where(RFIDCard.id == card_id)
        )
        card = result.scalar_one_or_none()
        
        if not card:
            raise HTTPException(status_code=404, detail="RFID card not found")
        
        user_name = None
        if card.user_id:
            user_result = await session.execute(
                select(User).where(User.id == card.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                user_name = user.name
        
        return RFIDCardResponse(
            id=card.id,
            card_number=card.card_number,
            user_id=card.user_id,
            user_name=user_name,
            balance=card.balance or 0,
            status=card.status or "active",
            is_active=card.is_active if card.is_active is not None else True,
            created_at=card.created_at.isoformat() if card.created_at else ""
        )


@router.post("", response_model=RFIDCardResponse)
async def create_rfid_card(
    card_data: RFIDCardCreate,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Create a new RFID card (Admin only)"""
    async with async_session() as session:
        # Check if card number exists
        result = await session.execute(
            select(RFIDCard).where(RFIDCard.card_number == card_data.card_number)
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Card number already exists")
        
        # Verify user exists if provided
        user_name = None
        if card_data.user_id:
            user_result = await session.execute(
                select(User).where(User.id == card_data.user_id)
            )
            user = user_result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            user_name = user.name
        
        card = RFIDCard(
            id=str(uuid.uuid4()),
            card_number=card_data.card_number,
            user_id=card_data.user_id,
            balance=card_data.balance,
            status="active",
            is_active=True
        )
        session.add(card)
        await session.commit()
        await session.refresh(card)
        
        return RFIDCardResponse(
            id=card.id,
            card_number=card.card_number,
            user_id=card.user_id,
            user_name=user_name,
            balance=card.balance or 0,
            status=card.status,
            is_active=card.is_active,
            created_at=card.created_at.isoformat() if card.created_at else ""
        )


@router.patch("/{card_id}", response_model=RFIDCardResponse)
async def update_rfid_card(
    card_id: str,
    card_data: RFIDCardUpdate,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Update an RFID card (Admin only)"""
    async with async_session() as session:
        result = await session.execute(
            select(RFIDCard).where(RFIDCard.id == card_id)
        )
        card = result.scalar_one_or_none()
        
        if not card:
            raise HTTPException(status_code=404, detail="RFID card not found")
        
        if card_data.user_id is not None:
            if card_data.user_id:
                user_result = await session.execute(
                    select(User).where(User.id == card_data.user_id)
                )
                if not user_result.scalar_one_or_none():
                    raise HTTPException(status_code=404, detail="User not found")
            card.user_id = card_data.user_id
        
        if card_data.balance is not None:
            card.balance = card_data.balance
        if card_data.status is not None:
            card.status = card_data.status
        if card_data.is_active is not None:
            card.is_active = card_data.is_active
        
        await session.commit()
        await session.refresh(card)
        
        user_name = None
        if card.user_id:
            user_result = await session.execute(
                select(User).where(User.id == card.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                user_name = user.name
        
        return RFIDCardResponse(
            id=card.id,
            card_number=card.card_number,
            user_id=card.user_id,
            user_name=user_name,
            balance=card.balance or 0,
            status=card.status or "active",
            is_active=card.is_active if card.is_active is not None else True,
            created_at=card.created_at.isoformat() if card.created_at else ""
        )


@router.delete("/{card_id}")
async def delete_rfid_card(
    card_id: str,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Delete an RFID card (Admin only)"""
    async with async_session() as session:
        result = await session.execute(
            delete(RFIDCard).where(RFIDCard.id == card_id)
        )
        await session.commit()
        
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="RFID card not found")
        
        return {"message": "RFID card deleted successfully"}


@router.post("/{card_id}/topup", response_model=RFIDCardResponse)
async def topup_rfid_card(
    card_id: str,
    topup: TopUpRequest,
    current_user: UserResponse = Depends(require_role("admin", "user"))
):
    """Add balance to an RFID card"""
    if topup.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    async with async_session() as session:
        result = await session.execute(
            select(RFIDCard).where(RFIDCard.id == card_id)
        )
        card = result.scalar_one_or_none()
        
        if not card:
            raise HTTPException(status_code=404, detail="RFID card not found")
        
        balance_before = card.balance or 0
        card.balance = balance_before + topup.amount
        
        # Record history
        history = RFIDHistory(
            id=str(uuid.uuid4()),
            card_id=card_id,
            transaction_type="TOPUP",
            amount=topup.amount,
            balance_before=balance_before,
            balance_after=card.balance,
            notes=topup.notes
        )
        session.add(history)
        
        await session.commit()
        await session.refresh(card)
        
        user_name = None
        if card.user_id:
            user_result = await session.execute(
                select(User).where(User.id == card.user_id)
            )
            user = user_result.scalar_one_or_none()
            if user:
                user_name = user.name
        
        return RFIDCardResponse(
            id=card.id,
            card_number=card.card_number,
            user_id=card.user_id,
            user_name=user_name,
            balance=card.balance or 0,
            status=card.status or "active",
            is_active=card.is_active if card.is_active is not None else True,
            created_at=card.created_at.isoformat() if card.created_at else ""
        )


@router.get("/{card_id}/history", response_model=List[RFIDHistoryResponse])
async def get_rfid_history(
    card_id: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """Get transaction history for an RFID card"""
    async with async_session() as session:
        result = await session.execute(
            select(RFIDHistory)
            .where(RFIDHistory.card_id == card_id)
            .order_by(RFIDHistory.created_at.desc())
        )
        history = result.scalars().all()
        
        return [
            RFIDHistoryResponse(
                id=h.id,
                card_id=h.card_id,
                transaction_type=h.transaction_type,
                amount=h.amount,
                balance_before=h.balance_before,
                balance_after=h.balance_after,
                notes=h.notes,
                created_at=h.created_at.isoformat() if h.created_at else ""
            )
            for h in history
        ]


@router.post("/import", response_model=RFIDImportResult)
async def import_rfid_cards(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Import RFID cards from Excel/CSV file (Admin only)"""
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="File must be Excel (.xlsx, .xls) or CSV (.csv)")
    
    try:
        import pandas as pd
        contents = await file.read()
        if file.filename.endswith('.csv'):
            df = pd.read_csv(BytesIO(contents))
        else:
            df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    
    # Create case-insensitive column mapping
    df_columns_lower = {col.lower().strip(): col for col in df.columns}
    
    # Map columns
    card_col = balance_col = user_col = None
    
    for col_lower, col_orig in df_columns_lower.items():
        if col_lower in ['card number', 'card_number', 'cardnumber', 'rfid', 'card']:
            card_col = col_orig
        elif col_lower in ['balance', 'saldo', 'initial balance']:
            balance_col = col_orig
        elif col_lower in ['user', 'user email', 'user_email', 'email', 'usuario']:
            user_col = col_orig
    
    if not card_col:
        raise HTTPException(status_code=400, detail="Missing required column: Card Number")
    
    import pandas as pd
    
    imported = 0
    skipped = 0
    errors = []
    
    for idx, row in df.iterrows():
        row_num = idx + 2
        
        card_number = str(row[card_col]).strip() if not pd.isna(row[card_col]) else ""
        
        if not card_number:
            errors.append({"row": row_num, "field": "Card Number", "message": "Card number is required"})
            continue
        
        async with async_session() as session:
            # Check if card exists
            result = await session.execute(
                select(RFIDCard).where(RFIDCard.card_number == card_number)
            )
            if result.scalar_one_or_none():
                skipped += 1
                continue
            
            # Get balance
            balance = 0.0
            if balance_col and not pd.isna(row.get(balance_col)):
                try:
                    balance = float(row[balance_col])
                except:
                    pass
            
            # Get user by email if provided
            user_id = None
            if user_col and not pd.isna(row.get(user_col)):
                email = str(row[user_col]).strip().lower()
                user_result = await session.execute(
                    select(User).where(User.email == email)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    user_id = user.id
            
            card = RFIDCard(
                id=str(uuid.uuid4()),
                card_number=card_number,
                user_id=user_id,
                balance=balance,
                status="active",
                is_active=True
            )
            
            try:
                session.add(card)
                await session.commit()
                imported += 1
            except Exception as e:
                errors.append({"row": row_num, "field": "Database", "message": str(e)})
    
    return RFIDImportResult(imported=imported, skipped=skipped, errors=errors)
