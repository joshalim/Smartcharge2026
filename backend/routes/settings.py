"""
Settings routes - PayU, SendGrid, Invoice webhook configuration (MongoDB)
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timezone

from database import get_db, Settings

from routes.auth import require_role, UserResponse

router = APIRouter(prefix="/settings", tags=["Settings"])


# Pydantic Models
class PayUSettings(BaseModel):
    api_key: Optional[str] = None
    api_login: Optional[str] = None
    merchant_id: Optional[str] = None
    account_id: Optional[str] = None
    test_mode: bool = True


class SendGridSettings(BaseModel):
    api_key: Optional[str] = None
    sender_email: Optional[str] = None
    sender_name: Optional[str] = None
    enabled: bool = False


class InvoiceWebhookSettings(BaseModel):
    webhook_url: Optional[str] = None
    api_key: Optional[str] = None
    enabled: bool = False


# Routes
@router.get("/payu", response_model=PayUSettings)
async def get_payu_settings(current_user: UserResponse = Depends(require_role("admin"))):
    """Get PayU configuration"""
    db = await get_db()
    settings = await db.settings.find_one({"type": "payu"})
    
    if not settings:
        return PayUSettings()
    
    return PayUSettings(
        api_key=settings.get('api_key'),
        api_login=settings.get('api_login'),
        merchant_id=settings.get('merchant_id'),
        account_id=settings.get('account_id'),
        test_mode=settings.get('test_mode', True)
    )


@router.put("/payu")
async def update_payu_settings(
    settings_data: PayUSettings,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Update PayU configuration"""
    db = await get_db()
    
    existing = await db.settings.find_one({"type": "payu"})
    
    update_data = {
        "type": "payu",
        "api_key": settings_data.api_key,
        "api_login": settings_data.api_login,
        "merchant_id": settings_data.merchant_id,
        "account_id": settings_data.account_id,
        "test_mode": settings_data.test_mode,
        "updated_at": datetime.now(timezone.utc)
    }
    
    if existing:
        await db.settings.update_one({"type": "payu"}, {"$set": update_data})
    else:
        update_data["id"] = str(uuid.uuid4())
        await db.settings.insert_one(update_data)
    
    return {"message": "PayU settings updated successfully"}


@router.get("/sendgrid", response_model=SendGridSettings)
async def get_sendgrid_settings(current_user: UserResponse = Depends(require_role("admin"))):
    """Get SendGrid configuration"""
    db = await get_db()
    settings = await db.settings.find_one({"type": "sendgrid"})
    
    if not settings:
        return SendGridSettings()
    
    return SendGridSettings(
        api_key=settings.get('api_key'),
        sender_email=settings.get('sender_email'),
        sender_name=settings.get('sender_name'),
        enabled=settings.get('enabled', False)
    )


@router.put("/sendgrid")
@router.post("/sendgrid")
async def update_sendgrid_settings(
    settings_data: SendGridSettings,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Update SendGrid configuration"""
    db = await get_db()
    
    existing = await db.settings.find_one({"type": "sendgrid"})
    
    update_data = {
        "type": "sendgrid",
        "api_key": settings_data.api_key,
        "sender_email": settings_data.sender_email,
        "sender_name": settings_data.sender_name,
        "enabled": settings_data.enabled,
        "updated_at": datetime.now(timezone.utc)
    }
    
    if existing:
        await db.settings.update_one({"type": "sendgrid"}, {"$set": update_data})
    else:
        update_data["id"] = str(uuid.uuid4())
        await db.settings.insert_one(update_data)
    
    return {"message": "SendGrid settings updated successfully"}


@router.get("/invoice-webhook", response_model=InvoiceWebhookSettings)
async def get_invoice_webhook_settings(current_user: UserResponse = Depends(require_role("admin"))):
    """Get invoice webhook configuration"""
    db = await get_db()
    settings = await db.settings.find_one({"type": "invoice_webhook"})
    
    if not settings:
        return InvoiceWebhookSettings()
    
    return InvoiceWebhookSettings(
        webhook_url=settings.get('webhook_url'),
        api_key=settings.get('api_key'),
        enabled=settings.get('enabled', False)
    )


@router.put("/invoice-webhook")
@router.post("/invoice-webhook")
async def update_invoice_webhook_settings(
    settings_data: InvoiceWebhookSettings,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Update invoice webhook configuration"""
    db = await get_db()
    
    existing = await db.settings.find_one({"type": "invoice_webhook"})
    
    update_data = {
        "type": "invoice_webhook",
        "webhook_url": settings_data.webhook_url,
        "api_key": settings_data.api_key,
        "enabled": settings_data.enabled,
        "updated_at": datetime.now(timezone.utc)
    }
    
    if existing:
        await db.settings.update_one({"type": "invoice_webhook"}, {"$set": update_data})
    else:
        update_data["id"] = str(uuid.uuid4())
        await db.settings.insert_one(update_data)
    
    return {"message": "Invoice webhook settings updated successfully"}
