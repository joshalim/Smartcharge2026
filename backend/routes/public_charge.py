"""
Public charging routes - QR code based charging without login
Includes PayU Colombia payment integration
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid
import hashlib
import hmac
import os

from sqlalchemy import select
from database import async_session, Charger, Transaction, Settings, PayUPayment, PayUWebhookLog

router = APIRouter(prefix="/public", tags=["Public Charging"])

# Get frontend URL from environment for redirects
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'https://evadmin-dashboard.preview.emergentagent.com')


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


# Pricing per connector type (COP per kWh)
CONNECTOR_PRICING = {
    'CCS': 2500.0,
    'CCS2': 2500.0,
    'CHADEMO': 2000.0,
    'J1772': 1500.0,
    'TYPE2': 1500.0,
}
DEFAULT_PRICE = 2000.0


async def get_payu_settings():
    """Get PayU settings from database"""
    async with async_session() as session:
        result = await session.execute(
            select(Settings).where(Settings.type == "payu")
        )
        settings = result.scalar_one_or_none()
        if settings:
            return {
                "api_key": settings.api_key,
                "api_login": settings.api_login,
                "merchant_id": settings.merchant_id,
                "account_id": settings.account_id,
                "test_mode": settings.test_mode if settings.test_mode is not None else True
            }
        return None


def generate_payu_signature(api_key: str, merchant_id: str, reference_code: str, amount: float, currency: str = "COP") -> str:
    """Generate MD5 signature for PayU Colombia"""
    # PayU Colombia uses MD5 signature
    # Format: apiKey~merchantId~referenceCode~amount~currency
    amount_str = f"{amount:.2f}"
    signature_string = f"{api_key}~{merchant_id}~{reference_code}~{amount_str}~{currency}"
    return hashlib.md5(signature_string.encode()).hexdigest()


def generate_payu_form_url(payu_settings: dict, reference_code: str, amount: float, 
                           description: str, buyer_email: str, buyer_phone: str = None) -> str:
    """Generate PayU webcheckout form URL"""
    
    test_mode = payu_settings.get("test_mode", True)
    merchant_id = payu_settings.get("merchant_id", "")
    account_id = payu_settings.get("account_id", "")
    api_key = payu_settings.get("api_key", "")
    
    # PayU webcheckout URLs
    base_url = "https://sandbox.checkout.payulatam.com/ppp-web-gateway-payu/" if test_mode else "https://checkout.payulatam.com/ppp-web-gateway-payu/"
    
    # Generate signature
    signature = generate_payu_signature(api_key, merchant_id, reference_code, amount)
    
    # Build return URLs
    response_url = f"{FRONTEND_URL}/payment/result?session_id={reference_code}"
    confirmation_url = f"{FRONTEND_URL}/api/public/payu-webhook"
    
    # Build form parameters
    params = {
        "merchantId": merchant_id,
        "accountId": account_id,
        "description": description,
        "referenceCode": reference_code,
        "amount": f"{amount:.2f}",
        "tax": "0",
        "taxReturnBase": "0",
        "currency": "COP",
        "signature": signature,
        "test": "1" if test_mode else "0",
        "buyerEmail": buyer_email or "guest@smartcharge.co",
        "responseUrl": response_url,
        "confirmationUrl": confirmation_url,
    }
    
    if buyer_phone:
        params["telephone"] = buyer_phone
    
    # Build URL with parameters
    param_string = "&".join([f"{k}={v}" for k, v in params.items()])
    return f"{base_url}?{param_string}"


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
            meter_value=0,
            charging_duration="",
            cost=request.amount,
            payment_status="PENDING"
        )
        
        session.add(new_tx)
        
        # Get PayU settings and generate payment URL
        payu_settings = await get_payu_settings()
        payment_url = None
        
        if payu_settings and payu_settings.get("api_key") and payu_settings.get("merchant_id"):
            description = f"EV Charging - {charger.name or request.charger_id} - {request.connector_type}"
            payment_url = generate_payu_form_url(
                payu_settings=payu_settings,
                reference_code=session_id,
                amount=request.amount,
                description=description,
                buyer_email=request.email,
                buyer_phone=request.phone
            )
            
            # Store PayU payment record
            payu_payment = PayUPayment(
                id=str(uuid.uuid4()),
                reference_code=session_id,
                card_number=None,
                user_id=None,
                amount=request.amount,
                buyer_name=request.placa or "Guest",
                buyer_email=request.email or "guest@smartcharge.co",
                buyer_phone=request.phone,
                status="PENDING"
            )
            session.add(payu_payment)
        
        await session.commit()
        
        return ChargeSession(
            session_id=session_id,
            charger_id=request.charger_id,
            connector_type=request.connector_type,
            amount=request.amount,
            status="pending_payment",
            created_at=datetime.now(timezone.utc).isoformat(),
            payment_url=payment_url
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


@router.post("/payu-webhook")
async def payu_webhook(request: Request):
    """Handle PayU Colombia webhook callbacks"""
    try:
        # Try to get form data (PayU sends as form)
        try:
            form_data = await request.form()
            body = dict(form_data)
        except:
            # Fall back to JSON
            body = await request.json()
        
        # Extract relevant fields
        reference_code = body.get("reference_sale") or body.get("referenceCode")
        state_pol = body.get("state_pol") or body.get("transactionState")
        transaction_id = body.get("transaction_id") or body.get("transactionId")
        
        if not reference_code:
            raise HTTPException(status_code=400, detail="Missing reference_code")
        
        async with async_session() as session:
            # Log the webhook
            webhook_log = PayUWebhookLog(
                id=str(uuid.uuid4()),
                reference_code=reference_code,
                webhook_data=body
            )
            session.add(webhook_log)
            
            # Update transaction status
            result = await session.execute(
                select(Transaction).where(Transaction.tx_id == reference_code)
            )
            tx = result.scalar_one_or_none()
            
            if tx:
                # Map PayU state to our status
                # 4 = APPROVED, 5 = EXPIRED, 6 = DECLINED, 7 = PENDING
                state_mapping = {
                    "4": "PAID",
                    "5": "EXPIRED",
                    "6": "DECLINED",
                    "7": "PENDING"
                }
                new_status = state_mapping.get(str(state_pol), tx.payment_status)
                tx.payment_status = new_status
            
            # Update PayU payment record
            payu_result = await session.execute(
                select(PayUPayment).where(PayUPayment.reference_code == reference_code)
            )
            payu_payment = payu_result.scalar_one_or_none()
            
            if payu_payment:
                payu_payment.status = new_status if tx else "UNKNOWN"
                payu_payment.payu_transaction_id = transaction_id
                payu_payment.payu_response = body
            
            await session.commit()
        
        return {"status": "received"}
    
    except Exception as e:
        print(f"PayU webhook error: {e}")
        # Always return 200 to PayU to prevent retries
        return {"status": "error", "message": str(e)}


@router.get("/payu-webhook")
async def payu_webhook_get(request: Request):
    """Handle PayU GET callback (response URL)"""
    # PayU may redirect with GET parameters
    params = dict(request.query_params)
    
    reference_code = params.get("referenceCode")
    transaction_state = params.get("transactionState") or params.get("lapTransactionState")
    
    if reference_code and transaction_state:
        async with async_session() as session:
            result = await session.execute(
                select(Transaction).where(Transaction.tx_id == reference_code)
            )
            tx = result.scalar_one_or_none()
            
            if tx:
                # 4 = APPROVED
                if transaction_state == "4":
                    tx.payment_status = "PAID"
                elif transaction_state == "6":
                    tx.payment_status = "DECLINED"
                elif transaction_state == "5":
                    tx.payment_status = "EXPIRED"
                
                await session.commit()
    
    # Redirect to payment result page
    redirect_url = f"{FRONTEND_URL}/payment/result?referenceCode={reference_code}&transactionState={transaction_state}"
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url=redirect_url)
