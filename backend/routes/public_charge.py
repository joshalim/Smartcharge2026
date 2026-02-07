"""
Public charging routes - QR code based charging without login
Includes BOLD.CO Colombia payment integration
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid
import httpx
import os
import time

from sqlalchemy import select
from database import async_session, Charger, Transaction, Settings, BoldPayment, BoldWebhookLog

router = APIRouter(prefix="/public", tags=["Public Charging"])

# Get frontend URL from environment for redirects
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://chargev-admin.preview.emergentagent.com')

# BOLD.CO API Base URL
BOLD_API_URL = "https://integrations.api.bold.co"


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
    payment_url: Optional[str] = None
    payment_link_id: Optional[str] = None


# Pricing per connector type (COP per kWh)
CONNECTOR_PRICING = {
    'CCS': 2500.0,
    'CCS2': 2500.0,
    'CHADEMO': 2000.0,
    'J1772': 1500.0,
    'TYPE2': 1500.0,
}
DEFAULT_PRICE = 2000.0


async def get_bold_settings():
    """Get BOLD.CO settings from database"""
    async with async_session() as session:
        result = await session.execute(
            select(Settings).where(Settings.type == "bold")
        )
        settings = result.scalar_one_or_none()
        if settings:
            return {
                "api_key": settings.api_key,
                "test_mode": settings.test_mode if settings.test_mode is not None else True
            }
        return None


async def create_bold_payment_link(
    api_key: str,
    amount: float,
    reference: str,
    description: str,
    callback_url: str,
    payer_email: Optional[str] = None
) -> dict:
    """
    Create a payment link using BOLD.CO API
    
    API Documentation: https://developers.bold.co/pagos-en-linea/api-link-de-pagos
    
    Returns:
        dict with payment_link (ID) and url (checkout URL)
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"x-api-key {api_key}"
    }
    
    # Calculate expiration (24 hours from now in nanoseconds)
    expiration_nanoseconds = int((time.time() + 86400) * 1e9)
    
    payload = {
        "amount_type": "CLOSE",
        "amount": {
            "currency": "COP",
            "total_amount": int(amount),  # BOLD expects integer for COP
            "tip_amount": 0
        },
        "reference": reference,
        "description": description[:100],  # Max 100 characters
        "expiration_date": expiration_nanoseconds,
        "callback_url": callback_url,
        "payment_methods": ["CREDIT_CARD", "PSE", "BOTON_BANCOLOMBIA", "NEQUI"]
    }
    
    if payer_email:
        payload["payer_email"] = payer_email
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BOLD_API_URL}/online/link/v1",
            headers=headers,
            json=payload,
            timeout=30.0
        )
        
        if response.status_code in [200, 201]:
            data = response.json()
            if data.get("errors") and len(data["errors"]) > 0:
                raise HTTPException(status_code=400, detail=f"BOLD API error: {data['errors']}")
            
            return {
                "payment_link": data.get("payload", {}).get("payment_link"),
                "url": data.get("payload", {}).get("url")
            }
        else:
            error_msg = f"BOLD API error: {response.status_code} - {response.text}"
            print(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)


async def get_bold_payment_status(api_key: str, payment_link_id: str) -> dict:
    """
    Get payment link status from BOLD.CO API
    
    Status values:
    - ACTIVE: Link is available for payment
    - PROCESSING: Payment in progress
    - PAID: Payment successful
    - REJECTED: Payment rejected
    - CANCELLED: Payment cancelled
    - EXPIRED: Link expired
    """
    headers = {
        "Authorization": f"x-api-key {api_key}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{BOLD_API_URL}/online/link/v1/{payment_link_id}",
            headers=headers,
            timeout=30.0
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "UNKNOWN"}


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
        
        # Validate minimum amount (BOLD.CO minimum is 1000 COP)
        if request.amount < 1000:
            raise HTTPException(status_code=400, detail="Minimum amount is $1,000 COP")
        
        # Calculate energy based on amount and connector type
        connector_upper = request.connector_type.upper()
        price_per_kwh = CONNECTOR_PRICING.get(connector_upper, DEFAULT_PRICE)
        
        # Create session ID with timestamp for uniqueness
        timestamp = int(time.time())
        session_id = f"QR-{uuid.uuid4().hex[:8].upper()}-{timestamp}"
        
        # Create a pending transaction
        new_tx = Transaction(
            id=str(uuid.uuid4()),
            tx_id=session_id,
            station=request.charger_id,
            connector=request.connector_type,
            account=request.email or request.phone or request.placa or "QR-Guest",
            start_time=datetime.now(timezone.utc).isoformat(),
            end_time="",
            meter_value=0,
            charging_duration="",
            cost=request.amount,
            payment_status="PENDING"
        )
        
        session.add(new_tx)
        
        # Get BOLD settings and create payment link
        bold_settings = await get_bold_settings()
        payment_url = None
        payment_link_id = None
        
        if bold_settings and bold_settings.get("api_key"):
            description = f"EV Charging - {charger.name or request.charger_id} - {request.connector_type}"
            callback_url = f"{FRONTEND_URL}/payment/result?session_id={session_id}"
            
            try:
                bold_response = await create_bold_payment_link(
                    api_key=bold_settings["api_key"],
                    amount=request.amount,
                    reference=session_id,
                    description=description,
                    callback_url=callback_url,
                    payer_email=request.email
                )
                
                payment_url = bold_response.get("url")
                payment_link_id = bold_response.get("payment_link")
                
                # Store BOLD payment record
                bold_payment = BoldPayment(
                    id=str(uuid.uuid4()),
                    reference_code=session_id,
                    payment_link_id=payment_link_id,
                    user_id=None,
                    amount=request.amount,
                    buyer_name=request.placa or "Guest",
                    buyer_email=request.email or "guest@smartcharge.co",
                    buyer_phone=request.phone,
                    status="ACTIVE"
                )
                session.add(bold_payment)
                
            except HTTPException as e:
                # Log error but don't fail - session is created even without payment link
                print(f"BOLD payment link creation failed: {e.detail}")
            except Exception as e:
                print(f"BOLD payment link creation error: {e}")
        
        await session.commit()
        
        return ChargeSession(
            session_id=session_id,
            charger_id=request.charger_id,
            connector_type=request.connector_type,
            amount=request.amount,
            status="pending_payment",
            created_at=datetime.now(timezone.utc).isoformat(),
            payment_url=payment_url,
            payment_link_id=payment_link_id
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
        
        # If payment is still pending, check BOLD API for updates
        if tx.payment_status == "PENDING":
            bold_settings = await get_bold_settings()
            if bold_settings and bold_settings.get("api_key"):
                # Get BOLD payment record
                bold_result = await session.execute(
                    select(BoldPayment).where(BoldPayment.reference_code == session_id)
                )
                bold_payment = bold_result.scalar_one_or_none()
                
                if bold_payment and bold_payment.payment_link_id:
                    try:
                        bold_status = await get_bold_payment_status(
                            bold_settings["api_key"],
                            bold_payment.payment_link_id
                        )
                        
                        # Map BOLD status to our status
                        status_mapping = {
                            "PAID": "PAID",
                            "REJECTED": "DECLINED",
                            "CANCELLED": "CANCELLED",
                            "EXPIRED": "EXPIRED",
                            "ACTIVE": "PENDING",
                            "PROCESSING": "PENDING"
                        }
                        
                        bold_status_value = bold_status.get("status", "ACTIVE")
                        new_status = status_mapping.get(bold_status_value, "PENDING")
                        
                        if new_status != tx.payment_status:
                            tx.payment_status = new_status
                            bold_payment.status = bold_status_value
                            bold_payment.bold_response = bold_status
                            await session.commit()
                    except Exception as e:
                        print(f"Error checking BOLD status: {e}")
        
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
    """Confirm payment for a session (manual confirmation)"""
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


@router.post("/bold-webhook")
async def bold_webhook(request: Request):
    """
    Handle BOLD.CO webhook callbacks
    
    BOLD sends webhook notifications for payment status changes.
    Configure webhook URL in BOLD merchant dashboard.
    """
    try:
        body = await request.json()
        
        # Extract relevant fields from BOLD webhook
        reference = body.get("reference") or body.get("id")
        status = body.get("status")
        transaction_id = body.get("transaction_id")
        
        if not reference:
            raise HTTPException(status_code=400, detail="Missing reference")
        
        async with async_session() as session:
            # Log the webhook
            webhook_log = BoldWebhookLog(
                id=str(uuid.uuid4()),
                reference_code=reference,
                webhook_data=body
            )
            session.add(webhook_log)
            
            # Update transaction status
            result = await session.execute(
                select(Transaction).where(Transaction.tx_id == reference)
            )
            tx = result.scalar_one_or_none()
            
            if tx:
                # Map BOLD status to our status
                status_mapping = {
                    "PAID": "PAID",
                    "REJECTED": "DECLINED",
                    "CANCELLED": "CANCELLED",
                    "EXPIRED": "EXPIRED",
                    "ACTIVE": "PENDING",
                    "PROCESSING": "PENDING"
                }
                new_status = status_mapping.get(status, tx.payment_status)
                tx.payment_status = new_status
            
            # Update BOLD payment record
            bold_result = await session.execute(
                select(BoldPayment).where(BoldPayment.reference_code == reference)
            )
            bold_payment = bold_result.scalar_one_or_none()
            
            if bold_payment:
                bold_payment.status = status or bold_payment.status
                bold_payment.bold_transaction_id = transaction_id
                bold_payment.bold_response = body
            
            await session.commit()
        
        return {"status": "received"}
    
    except Exception as e:
        print(f"BOLD webhook error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/bold-callback")
async def bold_callback(request: Request):
    """Handle BOLD.CO callback redirect after payment"""
    params = dict(request.query_params)
    
    session_id = params.get("session_id")
    
    if session_id:
        # Check payment status
        async with async_session() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.tx_id == session_id)
            )
            tx = result.scalar_one_or_none()
            
            if tx:
                # Get BOLD settings and check payment status
                bold_settings = await get_bold_settings()
                if bold_settings and bold_settings.get("api_key"):
                    bold_result = await session.execute(
                        select(BoldPayment).where(BoldPayment.reference_code == session_id)
                    )
                    bold_payment = bold_result.scalar_one_or_none()
                    
                    if bold_payment and bold_payment.payment_link_id:
                        try:
                            bold_status = await get_bold_payment_status(
                                bold_settings["api_key"],
                                bold_payment.payment_link_id
                            )
                            
                            status_mapping = {
                                "PAID": "PAID",
                                "REJECTED": "DECLINED",
                                "CANCELLED": "CANCELLED",
                                "EXPIRED": "EXPIRED"
                            }
                            
                            bold_status_value = bold_status.get("status", "ACTIVE")
                            if bold_status_value in status_mapping:
                                tx.payment_status = status_mapping[bold_status_value]
                                bold_payment.status = bold_status_value
                                bold_payment.bold_response = bold_status
                                await session.commit()
                        except Exception as e:
                            print(f"Error checking BOLD status on callback: {e}")
    
    # Redirect to payment result page
    redirect_url = f"{FRONTEND_URL}/payment/result?session_id={session_id}"
    return RedirectResponse(url=redirect_url)
