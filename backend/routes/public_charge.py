"""
Public charging routes - QR code based charging without login
Includes PayU Colombia payment integration (MongoDB)
"""
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid
import hashlib
import os

from database import get_db, Charger, Transaction, Settings, PayUPayment, PayUWebhookLog

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
    db = await get_db()
    settings = await db.settings.find_one({"type": "payu"})
    if settings:
        return {
            "api_key": settings.get('api_key'),
            "api_login": settings.get('api_login'),
            "merchant_id": settings.get('merchant_id'),
            "account_id": settings.get('account_id'),
            "test_mode": settings.get('test_mode', True)
        }
    return None


def generate_payu_signature(api_key: str, merchant_id: str, reference_code: str, amount: float, currency: str = "COP") -> str:
    """Generate MD5 signature for PayU Colombia"""
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
    db = await get_db()
    charger = await db.chargers.find_one({"charger_id": charger_id})
    
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found")
    
    # Parse connectors
    connectors = charger.get('connectors', [])
    if isinstance(connectors, dict):
        connectors = list(connectors.values())
    
    return ChargerInfo(
        charger_id=charger['charger_id'],
        name=charger.get('name') or charger['charger_id'],
        location=charger.get('location'),
        status=charger.get('status', 'available'),
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
    db = await get_db()
    
    # Validate charger exists
    charger = await db.chargers.find_one({"charger_id": request.charger_id})
    
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found")
    
    charger_status = charger.get('status', 'available').lower()
    if charger_status not in ["available", "online"]:
        raise HTTPException(status_code=400, detail=f"Charger is not available. Status: {charger.get('status')}")
    
    # Calculate energy based on amount and connector type
    connector_upper = request.connector_type.upper()
    price_per_kwh = CONNECTOR_PRICING.get(connector_upper, DEFAULT_PRICE)
    
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
    
    await db.transactions.insert_one(new_tx.to_dict())
    
    # Get PayU settings and generate payment URL
    payu_settings = await get_payu_settings()
    payment_url = None
    
    if payu_settings and payu_settings.get("api_key") and payu_settings.get("merchant_id"):
        description = f"EV Charging - {charger.get('name') or request.charger_id} - {request.connector_type}"
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
        await db.payu_payments.insert_one(payu_payment.to_dict())
    
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
    db = await get_db()
    tx = await db.transactions.find_one({"tx_id": session_id})
    
    if not tx:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": tx['tx_id'],
        "charger_id": tx.get('station'),
        "connector_type": tx.get('connector'),
        "amount": tx.get('cost', 0),
        "payment_status": tx.get('payment_status', 'PENDING'),
        "start_time": tx.get('start_time'),
        "end_time": tx.get('end_time'),
        "meter_value": tx.get('meter_value', 0)
    }


@router.post("/session/{session_id}/confirm-payment")
async def confirm_payment(session_id: str):
    """Confirm payment for a session (called after PayU callback)"""
    db = await get_db()
    tx = await db.transactions.find_one({"tx_id": session_id})
    
    if not tx:
        raise HTTPException(status_code=404, detail="Session not found")
    
    await db.transactions.update_one(
        {"tx_id": session_id},
        {"$set": {"payment_status": "PAID"}}
    )
    
    return {
        "session_id": session_id,
        "status": "payment_confirmed",
        "message": "Payment confirmed. Charging can begin."
    }


@router.post("/payu-webhook")
async def payu_webhook(request: Request):
    """Handle PayU Colombia webhook callbacks"""
    try:
        db = await get_db()
        
        # Try to get form data (PayU sends as form)
        try:
            form_data = await request.form()
            body = dict(form_data)
        except:
            body = await request.json()
        
        # Extract relevant fields
        reference_code = body.get("reference_sale") or body.get("referenceCode")
        state_pol = body.get("state_pol") or body.get("transactionState")
        transaction_id = body.get("transaction_id") or body.get("transactionId")
        
        if not reference_code:
            raise HTTPException(status_code=400, detail="Missing reference_code")
        
        # Log the webhook
        webhook_log = PayUWebhookLog(
            id=str(uuid.uuid4()),
            reference_code=reference_code,
            webhook_data=body
        )
        await db.payu_webhook_logs.insert_one(webhook_log.to_dict())
        
        # Map PayU state to our status
        # 4 = APPROVED, 5 = EXPIRED, 6 = DECLINED, 7 = PENDING
        state_mapping = {
            "4": "PAID",
            "5": "EXPIRED",
            "6": "DECLINED",
            "7": "PENDING"
        }
        new_status = state_mapping.get(str(state_pol), "PENDING")
        
        # Update transaction status
        await db.transactions.update_one(
            {"tx_id": reference_code},
            {"$set": {"payment_status": new_status}}
        )
        
        # Update PayU payment record
        await db.payu_payments.update_one(
            {"reference_code": reference_code},
            {"$set": {
                "status": new_status,
                "payu_transaction_id": transaction_id,
                "payu_response": body
            }}
        )
        
        return {"status": "received"}
    
    except Exception as e:
        print(f"PayU webhook error: {e}")
        return {"status": "error", "message": str(e)}


@router.get("/payu-webhook")
async def payu_webhook_get(request: Request):
    """Handle PayU GET callback (response URL)"""
    db = await get_db()
    params = dict(request.query_params)
    
    reference_code = params.get("referenceCode")
    transaction_state = params.get("transactionState") or params.get("lapTransactionState")
    
    if reference_code and transaction_state:
        # 4 = APPROVED, 6 = DECLINED, 5 = EXPIRED
        state_mapping = {
            "4": "PAID",
            "5": "EXPIRED",
            "6": "DECLINED",
            "7": "PENDING"
        }
        new_status = state_mapping.get(str(transaction_state), "PENDING")
        
        await db.transactions.update_one(
            {"tx_id": reference_code},
            {"$set": {"payment_status": new_status}}
        )
    
    # Redirect to payment result page
    redirect_url = f"{FRONTEND_URL}/payment/result?referenceCode={reference_code}&transactionState={transaction_state}"
    return RedirectResponse(url=redirect_url)
