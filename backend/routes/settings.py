"""
Settings routes - PayU, SendGrid, Invoice webhook configuration
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
import uuid

from sqlalchemy import select
from database import async_session, Settings

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


class InvoiceWebhookSettings(BaseModel):
    webhook_url: Optional[str] = None
    api_key: Optional[str] = None
    enabled: bool = False


# Routes
@router.get("/payu", response_model=PayUSettings)
async def get_payu_settings(current_user: UserResponse = Depends(require_role("admin"))):
    """Get PayU configuration"""
    async with async_session() as session:
        result = await session.execute(
            select(Settings).where(Settings.type == "payu")
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            return PayUSettings()
        
        return PayUSettings(
            api_key=settings.api_key,
            api_login=settings.api_login,
            merchant_id=settings.merchant_id,
            account_id=settings.account_id,
            test_mode=settings.test_mode if settings.test_mode is not None else True
        )


@router.put("/payu")
async def update_payu_settings(
    settings_data: PayUSettings,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Update PayU configuration"""
    async with async_session() as session:
        result = await session.execute(
            select(Settings).where(Settings.type == "payu")
        )
        settings = result.scalar_one_or_none()
        
        if settings:
            settings.api_key = settings_data.api_key
            settings.api_login = settings_data.api_login
            settings.merchant_id = settings_data.merchant_id
            settings.account_id = settings_data.account_id
            settings.test_mode = settings_data.test_mode
        else:
            settings = Settings(
                id=str(uuid.uuid4()),
                type="payu",
                api_key=settings_data.api_key,
                api_login=settings_data.api_login,
                merchant_id=settings_data.merchant_id,
                account_id=settings_data.account_id,
                test_mode=settings_data.test_mode
            )
            session.add(settings)
        
        await session.commit()
        return {"message": "PayU settings updated successfully"}


@router.get("/sendgrid", response_model=SendGridSettings)
async def get_sendgrid_settings(current_user: UserResponse = Depends(require_role("admin"))):
    """Get SendGrid configuration"""
    async with async_session() as session:
        result = await session.execute(
            select(Settings).where(Settings.type == "sendgrid")
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            return SendGridSettings()
        
        return SendGridSettings(
            api_key=settings.api_key,
            sender_email=settings.sender_email,
            sender_name=settings.sender_name
        )


@router.put("/sendgrid")
async def update_sendgrid_settings(
    settings_data: SendGridSettings,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Update SendGrid configuration"""
    async with async_session() as session:
        result = await session.execute(
            select(Settings).where(Settings.type == "sendgrid")
        )
        settings = result.scalar_one_or_none()
        
        if settings:
            settings.api_key = settings_data.api_key
            settings.sender_email = settings_data.sender_email
            settings.sender_name = settings_data.sender_name
        else:
            settings = Settings(
                id=str(uuid.uuid4()),
                type="sendgrid",
                api_key=settings_data.api_key,
                sender_email=settings_data.sender_email,
                sender_name=settings_data.sender_name
            )
            session.add(settings)
        
        await session.commit()
        return {"message": "SendGrid settings updated successfully"}


@router.get("/invoice-webhook", response_model=InvoiceWebhookSettings)
async def get_invoice_webhook_settings(current_user: UserResponse = Depends(require_role("admin"))):
    """Get invoice webhook configuration"""
    async with async_session() as session:
        result = await session.execute(
            select(Settings).where(Settings.type == "invoice_webhook")
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            return InvoiceWebhookSettings()
        
        return InvoiceWebhookSettings(
            webhook_url=getattr(settings, 'sender_email', None),  # Using sender_email field for webhook_url
            api_key=settings.api_key,
            enabled=settings.enabled if settings.enabled is not None else False
        )


@router.put("/invoice-webhook")
async def update_invoice_webhook_settings(
    settings_data: InvoiceWebhookSettings,
    current_user: UserResponse = Depends(require_role("admin"))
):
    """Update invoice webhook configuration"""
    async with async_session() as session:
        result = await session.execute(
            select(Settings).where(Settings.type == "invoice_webhook")
        )
        settings = result.scalar_one_or_none()
        
        if settings:
            settings.sender_email = settings_data.webhook_url  # Using sender_email field for webhook_url
            settings.api_key = settings_data.api_key
            settings.enabled = settings_data.enabled
        else:
            settings = Settings(
                id=str(uuid.uuid4()),
                type="invoice_webhook",
                sender_email=settings_data.webhook_url,
                api_key=settings_data.api_key,
                enabled=settings_data.enabled
            )
            session.add(settings)
        
        await session.commit()
        return {"message": "Invoice webhook settings updated successfully"}
