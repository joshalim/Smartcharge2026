"""
Public charging routes - QR code based charging without login
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid

from sqlalchemy import select
from database import async_session, Charger, Transaction, User

router = APIRouter(prefix="/public", tags=["Public Charging"])


class ChargerInfo(BaseModel):
    charger_id: str
    name: str
    location: Optional[str] = None
    status: str
    connectors: list


class StartChargeRequest(BaseModel):
    charger_id: str
    connector_type: str
    amount: float  # Amount in COP
    email: Optional[str] = None
    phone: Optional[str] = None
    placa: Optional[str] = None  # Vehicle registration


class ChargeSession(BaseModel):
    session_id: str
    charger_id: str
    connector_type: str
    amount: float
    status: str
    created_at: str


# Pricing per connector type (COP per kWh)
CONNECTOR_PRICING = {
    'CCS': 2500.0,
    'CCS2': 2500.0,
    'CHADEMO': 2000.0,
    'J1772': 1500.0,
    'TYPE2': 1500.0,
}
DEFAULT_PRICE = 2000.0


@router.get("/charger/{charger_id}", response_model=ChargerInfo)
async def get_charger_info(charger_id: str):
    """Get charger information for QR code page (no auth required)"""
    async with async_session() as session:
        result = await session.execute(
            select(Charger).where(Charger.charger_id == charger_id)
        )
        charger = result.scalar_one_or_none()
        
        if not charger:
            raise HTTPException(status_code=404, detail="Charger not found")
        
        # Parse connectors
        connectors = []
        if charger.connectors:
            if isinstance(charger.connectors, list):
                connectors = charger.connectors
            elif isinstance(charger.connectors, dict):
                connectors = list(charger.connectors.values())
        
        return ChargerInfo(
            charger_id=charger.charger_id,
            name=charger.name or charger.charger_id,
            location=charger.location,
            status=charger.status or "available",
            connectors=connectors
        )


@router.get("/pricing")
async def get_pricing():
    """Get pricing information for all connector types"""
    return {
        "pricing": CONNECTOR_PRICING,
        "default": DEFAULT_PRICE,
        "currency": "COP"
    }


@router.post("/start-charge", response_model=ChargeSession)
async def start_charge_session(request: StartChargeRequest):
    """Start a charging session from QR code (no auth required)"""
    
    # Validate charger exists
    async with async_session() as session:
        result = await session.execute(
            select(Charger).where(Charger.charger_id == request.charger_id)
        )
        charger = result.scalar_one_or_none()
        
        if not charger:
            raise HTTPException(status_code=404, detail="Charger not found")
        
        if charger.status not in ["available", "Available", "online", "Online"]:
            raise HTTPException(status_code=400, detail=f"Charger is not available. Status: {charger.status}")
        
        # Calculate energy based on amount and connector type
        connector_upper = request.connector_type.upper()
        price_per_kwh = CONNECTOR_PRICING.get(connector_upper, DEFAULT_PRICE)
        estimated_kwh = request.amount / price_per_kwh
        
        # Create session ID
        session_id = f"QR-{uuid.uuid4().hex[:8].upper()}"
        
        # Create a pending transaction
        new_tx = Transaction(
            id=str(uuid.uuid4()),
            tx_id=session_id,
            station=request.charger_id,
            connector=request.connector_type,
            account=request.email or request.phone or request.placa or "QR-Guest",
            start_time=datetime.now(timezone.utc).isoformat(),
            end_time="",
            meter_value=0,  # Will be updated when charging completes
            charging_duration="",
            cost=request.amount,
            payment_status="PENDING"
        )
        
        session.add(new_tx)
        await session.commit()
        
        return ChargeSession(
            session_id=session_id,
            charger_id=request.charger_id,
            connector_type=request.connector_type,
            amount=request.amount,
            status="pending_payment",
            created_at=datetime.now(timezone.utc).isoformat()
        )


@router.get("/session/{session_id}")
async def get_session_status(session_id: str):
    """Get charging session status"""
    async with async_session() as session:
        result = await session.execute(
            select(Transaction).where(Transaction.tx_id == session_id)
        )
        tx = result.scalar_one_or_none()
        
        if not tx:
            raise HTTPException(status_code=404, detail="Session not found")
        
        return {
            "session_id": tx.tx_id,
            "charger_id": tx.station,
            "connector_type": tx.connector,
            "amount": tx.cost,
            "payment_status": tx.payment_status,
            "start_time": tx.start_time,
            "end_time": tx.end_time,
            "meter_value": tx.meter_value
        }


@router.post("/session/{session_id}/confirm-payment")
async def confirm_payment(session_id: str):
    """Confirm payment for a session (called after PayU callback)"""
    async with async_session() as session:
        result = await session.execute(
            select(Transaction).where(Transaction.tx_id == session_id)
        )
        tx = result.scalar_one_or_none()
        
        if not tx:
            raise HTTPException(status_code=404, detail="Session not found")
        
        tx.payment_status = "PAID"
        await session.commit()
        
        return {
            "session_id": session_id,
            "status": "payment_confirmed",
            "message": "Payment confirmed. Charging can begin."
        }
