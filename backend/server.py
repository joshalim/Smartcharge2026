from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, status, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import hashlib
import httpx
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import pandas as pd
import openpyxl
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
from fastapi.responses import StreamingResponse
from io import BytesIO
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

# PayU Colombia Configuration (Sandbox defaults)
PAYU_API_KEY = os.environ.get('PAYU_API_KEY', '4Vj8eK4rloUd272L48hsrarnUA')
PAYU_API_LOGIN = os.environ.get('PAYU_API_LOGIN', 'pRRXKOl8ikMmt9u')
PAYU_MERCHANT_ID = os.environ.get('PAYU_MERCHANT_ID', '508029')
PAYU_ACCOUNT_ID = os.environ.get('PAYU_ACCOUNT_ID', '512321')
PAYU_TEST_MODE = os.environ.get('PAYU_TEST_MODE', 'true').lower() == 'true'
PAYU_API_URL = 'https://sandbox.checkout.payulatam.com/ppp-web-gateway-payu/' if PAYU_TEST_MODE else 'https://checkout.payulatam.com/ppp-web-gateway-payu/'
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

security = HTTPBearer()

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Special pricing groups
SPECIAL_ACCOUNTS = ["PORTERIA", "Jorge Iluminacion", "John Iluminacion"]
CONNECTOR_TYPE_PRICING = {
    "CCS2": 2500.0,
    "CHADEMO": 2000.0,
    "J1772": 1500.0
}

class UserRole:
    ADMIN = "admin"
    USER = "user"
    VIEWER = "viewer"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: str = UserRole.USER

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    email: str
    name: str
    role: str
    pricing_group_id: Optional[str] = None
    created_at: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: User

class PricingRule(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    account: str
    connector: str
    price_per_kwh: float
    created_at: str

class PricingRuleCreate(BaseModel):
    account: str
    connector: str
    price_per_kwh: float

# Pricing Group Models
class ConnectorPricing(BaseModel):
    CCS2: float = 2500.0
    CHADEMO: float = 2000.0
    J1772: float = 1500.0

class PricingGroup(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    description: Optional[str] = None
    connector_pricing: dict
    user_count: int = 0
    created_at: str
    updated_at: Optional[str] = None

class PricingGroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    connector_pricing: ConnectorPricing

class PricingGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    connector_pricing: Optional[ConnectorPricing] = None

class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
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

class DashboardStats(BaseModel):
    total_transactions: int
    total_energy: float
    total_revenue: float
    paid_revenue: float
    unpaid_revenue: float
    active_stations: int
    unique_accounts: int
    payment_breakdown: dict
    recent_transactions: List[Transaction]

class ImportValidationError(BaseModel):
    row: int
    field: str
    message: str

class ImportResult(BaseModel):
    success: bool
    imported_count: int
    skipped_count: int
    errors: List[ImportValidationError]

class OCPPBootNotification(BaseModel):
    chargePointVendor: str
    chargePointModel: str
    chargePointSerialNumber: Optional[str] = None
    firmwareVersion: Optional[str] = None

class OCPPStartTransaction(BaseModel):
    connectorId: int
    idTag: str
    meterStart: int
    timestamp: str

class OCPPStopTransaction(BaseModel):
    transactionId: int
    idTag: str
    meterStop: int
    timestamp: str

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

class Charger(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    name: str
    location: str
    model: str
    serial_number: str
    connector_types: List[str]
    max_power: float
    status: str
    created_at: str

class ChargerCreate(BaseModel):
    name: str
    location: str
    model: str
    serial_number: str
    connector_types: List[str]
    max_power: float
    status: str = "Available"

class ChargerUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    model: Optional[str] = None
    serial_number: Optional[str] = None
    connector_types: Optional[List[str]] = None
    max_power: Optional[float] = None
    status: Optional[str] = None

class RemoteStartRequest(BaseModel):
    charger_id: str
    connector_id: int
    id_tag: str

class RemoteStopRequest(BaseModel):
    transaction_id: int

class ReportFilter(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    account: Optional[str] = None
    connector_type: Optional[str] = None
    payment_type: Optional[str] = None
    payment_status: Optional[str] = None

class ReportData(BaseModel):
    summary: dict
    by_account: List[dict]
    by_connector: List[dict]
    by_payment_type: List[dict]
    transactions: List[Transaction]

# RFID Card Models
class RFIDCard(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    card_number: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    balance: float
    status: str  # active, inactive, blocked
    low_balance_threshold: float = 10000.0  # Default 10,000 COP
    created_at: str

class RFIDCardCreate(BaseModel):
    card_number: str
    user_id: str
    balance: float = 0.0
    status: str = "active"
    low_balance_threshold: float = 10000.0

class RFIDCardUpdate(BaseModel):
    card_number: Optional[str] = None
    status: Optional[str] = None
    low_balance_threshold: Optional[float] = None

class RFIDTopUp(BaseModel):
    amount: float

# User Create/Update Models
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "user"

class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None

# PayU Payment Models
class PayUTopUpRequest(BaseModel):
    rfid_card_id: str
    amount: float
    buyer_name: str
    buyer_email: str
    buyer_phone: str

class PayUWebhook(BaseModel):
    model_config = ConfigDict(extra="allow")
    reference_sale: Optional[str] = None
    state_pol: Optional[str] = None
    response_code_pol: Optional[str] = None
    sign: Optional[str] = None
    merchant_id: Optional[str] = None
    value: Optional[str] = None
    currency: Optional[str] = None
    transaction_id: Optional[str] = None

# RFID Card History Model
class RFIDHistory(BaseModel):
    id: str
    card_id: str
    card_number: str
    type: str  # topup, charge, adjustment
    amount: float
    balance_before: float
    balance_after: float
    description: str
    reference_id: Optional[str] = None
    created_at: str

# Invoice Webhook Model
class InvoiceWebhookConfig(BaseModel):
    webhook_url: str
    api_key: Optional[str] = None
    enabled: bool = True

class InvoiceWebhookPayload(BaseModel):
    event_type: str  # transaction_completed
    transaction_id: str
    tx_id: str
    account: str
    station: str
    connector: str
    connector_type: Optional[str] = None
    start_time: str
    end_time: str
    charging_duration: Optional[str] = None
    meter_value: float
    cost: float
    payment_status: str
    payment_type: Optional[str] = None
    payment_date: Optional[str] = None
    rfid_card_number: Optional[str] = None
    user_email: Optional[str] = None
    created_at: str

# Settings Models
class PayUSettings(BaseModel):
    api_key: str
    api_login: str
    merchant_id: str
    account_id: str
    test_mode: bool = True

class SendGridSettings(BaseModel):
    api_key: str
    sender_email: str
    sender_name: str = "EV Charging System"
    enabled: bool = True

class AllSettings(BaseModel):
    payu: Optional[PayUSettings] = None
    sendgrid: Optional[SendGridSettings] = None
    invoice_webhook: Optional[InvoiceWebhookConfig] = None

# Email notification helper
async def send_low_balance_email(card: dict, user_email: str, user_name: str):
    """Send low balance notification email via SendGrid"""
    settings = await db.settings.find_one({"type": "sendgrid"}, {"_id": 0})
    
    if not settings or not settings.get("enabled") or not settings.get("api_key"):
        logging.warning("SendGrid not configured, skipping email notification")
        return False
    
    try:
        sg = SendGridAPIClient(settings["api_key"])
        
        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #EA580C; padding: 20px; text-align: center;">
                <h1 style="color: white; margin: 0;">⚡ EV Charging System</h1>
            </div>
            <div style="padding: 30px; background-color: #f8f9fa;">
                <h2 style="color: #333;">Low Balance Alert</h2>
                <p>Hello {user_name},</p>
                <p>Your RFID card <strong>{card.get('card_number')}</strong> has a low balance.</p>
                
                <div style="background-color: #fff; border: 1px solid #ddd; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0; font-size: 14px; color: #666;">Current Balance</p>
                    <p style="margin: 5px 0 0 0; font-size: 32px; font-weight: bold; color: #DC2626;">
                        $ {card.get('balance', 0):,.0f} COP
                    </p>
                    <p style="margin: 10px 0 0 0; font-size: 12px; color: #999;">
                        Threshold: $ {card.get('low_balance_threshold', 10000):,.0f} COP
                    </p>
                </div>
                
                <p>Please top up your card to continue using the charging service without interruption.</p>
                
                <p style="color: #666; font-size: 12px; margin-top: 30px;">
                    This is an automated notification from EV Charging System.<br>
                    Please do not reply to this email.
                </p>
            </div>
        </body>
        </html>
        """
        
        message = Mail(
            from_email=(settings.get("sender_email"), settings.get("sender_name", "EV Charging System")),
            to_emails=user_email,
            subject=f"⚠️ Low Balance Alert - RFID Card {card.get('card_number')}",
            html_content=html_content
        )
        
        response = sg.send(message)
        logging.info(f"Low balance email sent to {user_email}, status: {response.status_code}")
        return response.status_code == 202
        
    except Exception as e:
        logging.error(f"Failed to send low balance email: {str(e)}")
        return False

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = await db.users.find_one({"id": user_id}, {"_id": 0})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return User(**user)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_role(*allowed_roles: str):
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return role_checker

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
    
    # First check if user has a pricing group assigned
    if user_id:
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "pricing_group_id": 1})
        if user and user.get("pricing_group_id"):
            group = await db.pricing_groups.find_one({"id": user["pricing_group_id"]}, {"_id": 0})
            if group and group.get("connector_pricing") and connector_type:
                pricing = group["connector_pricing"]
                if connector_type in pricing:
                    return pricing[connector_type]
    
    # Check if account is in special group (legacy support)
    if account in SPECIAL_ACCOUNTS:
        if connector_type and connector_type in CONNECTOR_TYPE_PRICING:
            return CONNECTOR_TYPE_PRICING[connector_type]
        return 500.0
    
    # For other accounts, use custom pricing from database
    pricing = await db.pricing.find_one({"account": account, "connector": connector}, {"_id": 0})
    if pricing:
        return pricing['price_per_kwh']
    
    # Check for default pricing
    default_pricing = await db.pricing.find_one({"account": account, "connector": "default"}, {"_id": 0})
    if default_pricing:
        return default_pricing['price_per_kwh']
    
    # Fall back to connector type pricing
    if connector_type and connector_type in CONNECTOR_TYPE_PRICING:
        return CONNECTOR_TYPE_PRICING[connector_type]
    
    return 500.0

# Auth Routes
@api_router.post("/auth/register", response_model=User)
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user = {
        "id": str(uuid.uuid4()),
        "email": user_data.email,
        "password_hash": hash_password(user_data.password),
        "name": user_data.name,
        "role": user_data.role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(user)
    user_response = {k: v for k, v in user.items() if k != "password_hash"}
    return User(**user_response)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    access_token = create_access_token({"sub": user["id"]})
    user_response = {k: v for k, v in user.items() if k not in ["password_hash", "_id"]}
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=User(**user_response)
    )

@api_router.get("/auth/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# Pricing Routes
@api_router.get("/pricing", response_model=List[PricingRule])
async def get_pricing_rules(current_user: User = Depends(require_role(UserRole.ADMIN))):
    pricing_rules = await db.pricing.find({}, {"_id": 0}).to_list(100)
    return [PricingRule(**p) for p in pricing_rules]

@api_router.post("/pricing", response_model=PricingRule)
async def create_pricing_rule(
    pricing_data: PricingRuleCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    existing = await db.pricing.find_one({
        "account": pricing_data.account,
        "connector": pricing_data.connector
    })
    
    if existing:
        await db.pricing.update_one(
            {"account": pricing_data.account, "connector": pricing_data.connector},
            {"$set": {"price_per_kwh": pricing_data.price_per_kwh}}
        )
        existing["price_per_kwh"] = pricing_data.price_per_kwh
        return PricingRule(**{k: v for k, v in existing.items() if k != "_id"})
    
    pricing_rule = {
        "id": str(uuid.uuid4()),
        **pricing_data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.pricing.insert_one(pricing_rule)
    return PricingRule(**{k: v for k, v in pricing_rule.items() if k != "_id"})

@api_router.delete("/pricing/{pricing_id}")
async def delete_pricing_rule(
    pricing_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    result = await db.pricing.delete_one({"id": pricing_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pricing rule not found")
    return {"message": "Pricing rule deleted successfully"}

# Pricing Group Routes
@api_router.get("/pricing-groups", response_model=List[PricingGroup])
async def get_pricing_groups(current_user: User = Depends(require_role(UserRole.ADMIN))):
    """Get all pricing groups with user counts"""
    groups = await db.pricing_groups.find({}, {"_id": 0}).to_list(100)
    
    # Add user counts
    for group in groups:
        user_count = await db.users.count_documents({"pricing_group_id": group["id"]})
        group["user_count"] = user_count
    
    return [PricingGroup(**g) for g in groups]

@api_router.get("/pricing-groups/{group_id}", response_model=PricingGroup)
async def get_pricing_group(
    group_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Get a single pricing group"""
    group = await db.pricing_groups.find_one({"id": group_id}, {"_id": 0})
    if not group:
        raise HTTPException(status_code=404, detail="Pricing group not found")
    
    user_count = await db.users.count_documents({"pricing_group_id": group_id})
    group["user_count"] = user_count
    return PricingGroup(**group)

@api_router.post("/pricing-groups", response_model=PricingGroup)
async def create_pricing_group(
    group_data: PricingGroupCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Create a new pricing group"""
    existing = await db.pricing_groups.find_one({"name": group_data.name})
    if existing:
        raise HTTPException(status_code=400, detail="Group name already exists")
    
    group = {
        "id": str(uuid.uuid4()),
        "name": group_data.name,
        "description": group_data.description,
        "connector_pricing": group_data.connector_pricing.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.pricing_groups.insert_one(group)
    group["user_count"] = 0
    return PricingGroup(**{k: v for k, v in group.items() if k != "_id"})

@api_router.patch("/pricing-groups/{group_id}", response_model=PricingGroup)
async def update_pricing_group(
    group_id: str,
    update_data: PricingGroupUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Update a pricing group"""
    existing = await db.pricing_groups.find_one({"id": group_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Pricing group not found")
    
    update_dict = {}
    
    if update_data.name:
        name_check = await db.pricing_groups.find_one({"name": update_data.name, "id": {"$ne": group_id}})
        if name_check:
            raise HTTPException(status_code=400, detail="Group name already exists")
        update_dict["name"] = update_data.name
    
    if update_data.description is not None:
        update_dict["description"] = update_data.description
    
    if update_data.connector_pricing:
        update_dict["connector_pricing"] = update_data.connector_pricing.model_dump()
    
    if update_dict:
        update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.pricing_groups.update_one({"id": group_id}, {"$set": update_dict})
        existing.update(update_dict)
    
    user_count = await db.users.count_documents({"pricing_group_id": group_id})
    existing["user_count"] = user_count
    return PricingGroup(**existing)

@api_router.delete("/pricing-groups/{group_id}")
async def delete_pricing_group(
    group_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Delete a pricing group"""
    user_count = await db.users.count_documents({"pricing_group_id": group_id})
    if user_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete group with {user_count} assigned users. Reassign users first."
        )
    
    result = await db.pricing_groups.delete_one({"id": group_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Pricing group not found")
    return {"message": "Pricing group deleted successfully"}

@api_router.get("/pricing-groups/{group_id}/users")
async def get_group_users(
    group_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Get all users in a pricing group"""
    users = await db.users.find(
        {"pricing_group_id": group_id}, 
        {"_id": 0, "password_hash": 0}
    ).to_list(500)
    return users

@api_router.post("/pricing-groups/{group_id}/users/{user_id}")
async def assign_user_to_group(
    group_id: str,
    user_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Assign a user to a pricing group"""
    group = await db.pricing_groups.find_one({"id": group_id})
    if not group:
        raise HTTPException(status_code=404, detail="Pricing group not found")
    
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.users.update_one({"id": user_id}, {"$set": {"pricing_group_id": group_id}})
    return {"message": f"User assigned to group '{group['name']}'"}

@api_router.delete("/pricing-groups/{group_id}/users/{user_id}")
async def remove_user_from_group(
    group_id: str,
    user_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Remove a user from a pricing group"""
    result = await db.users.update_one(
        {"id": user_id, "pricing_group_id": group_id},
        {"$unset": {"pricing_group_id": ""}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found in this group")
    return {"message": "User removed from group"}

# Transaction Routes
@api_router.post("/transactions", response_model=Transaction)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.USER))
):
    price_per_kwh = await get_pricing(transaction_data.account, transaction_data.connector, transaction_data.connector_type)
    cost = transaction_data.meter_value * price_per_kwh
    charging_duration = calculate_charging_duration(transaction_data.start_time, transaction_data.end_time)
    
    transaction = {
        "id": str(uuid.uuid4()),
        **transaction_data.model_dump(),
        "charging_duration": charging_duration,
        "cost": round(cost, 2),
        "payment_status": "UNPAID",
        "payment_type": None,
        "payment_date": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.transactions.insert_one(transaction)
    return Transaction(**{k: v for k, v in transaction.items() if k != "_id"})

@api_router.get("/transactions", response_model=List[Transaction])
async def get_transactions(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    station: Optional[str] = None,
    account: Optional[str] = None,
    payment_status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    query = {}
    
    if start_date:
        query["start_time"] = {"$gte": start_date}
    if end_date:
        if "start_time" in query:
            query["start_time"]["$lte"] = end_date
        else:
            query["start_time"] = {"$lte": end_date}
    if station:
        query["station"] = station
    if account:
        query["account"] = account
    if payment_status:
        query["payment_status"] = payment_status
    
    transactions = await db.transactions.find(query, {"_id": 0}).sort("start_time", -1).skip(skip).limit(limit).to_list(limit)
    return [Transaction(**t) for t in transactions]

@api_router.patch("/transactions/{transaction_id}", response_model=Transaction)
async def update_transaction(
    transaction_id: str,
    update_data: TransactionUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.USER))
):
    existing = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    # Recalculate cost if meter_value, account, or connector changed
    if "meter_value" in update_dict or "account" in update_dict or "connector" in update_dict or "connector_type" in update_dict:
        meter_value = update_dict.get("meter_value", existing["meter_value"])
        account = update_dict.get("account", existing["account"])
        connector = update_dict.get("connector", existing["connector"])
        connector_type = update_dict.get("connector_type", existing.get("connector_type"))
        
        price_per_kwh = await get_pricing(account, connector, connector_type)
        update_dict["cost"] = round(meter_value * price_per_kwh, 2)
    
    # Recalculate duration if times changed
    if "start_time" in update_dict or "end_time" in update_dict:
        start_time = update_dict.get("start_time", existing["start_time"])
        end_time = update_dict.get("end_time", existing["end_time"])
        update_dict["charging_duration"] = calculate_charging_duration(start_time, end_time)
    
    if update_dict:
        await db.transactions.update_one({"id": transaction_id}, {"$set": update_dict})
        existing.update(update_dict)
    
    return Transaction(**existing)

@api_router.delete("/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    result = await db.transactions.delete_one({"id": transaction_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted successfully"}

# Bulk Delete Transactions
class BulkDeleteRequest(BaseModel):
    ids: List[str]

@api_router.post("/transactions/bulk-delete")
async def bulk_delete_transactions(
    request: BulkDeleteRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    if not request.ids:
        raise HTTPException(status_code=400, detail="No transaction IDs provided")
    
    if len(request.ids) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 transactions can be deleted at once")
    
    result = await db.transactions.delete_many({"id": {"$in": request.ids}})
    
    return {
        "message": f"Successfully deleted {result.deleted_count} transaction(s)",
        "deleted_count": result.deleted_count
    }

# Excel Import
@api_router.post("/transactions/import", response_model=ImportResult)
async def import_transactions(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.USER))
):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) are allowed")
    
    try:
        contents = await file.read()
        df = pd.read_excel(BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {str(e)}")
    
    # Create case-insensitive column mapping
    df_columns_lower = {col.lower(): col for col in df.columns}
    required_columns_map = {
        'txid': 'TxID',
        'station': 'Station', 
        'connector': 'Connector',
        'account': 'Account',
        'start time': 'Start Time',
        'end time': 'End Time',
        'meter value(kw.h)': 'Meter value(kW.h)'
    }
    
    # Normalize column names
    column_mapping = {}
    missing_columns = []
    for required_lower, required_display in required_columns_map.items():
        found = False
        for df_col_lower, df_col_orig in df_columns_lower.items():
            if df_col_lower == required_lower:
                column_mapping[df_col_orig] = required_display
                found = True
                break
        if not found:
            missing_columns.append(required_display)
    
    # Rename columns to standard names
    if column_mapping:
        df = df.rename(columns=column_mapping)
    
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing_columns)}"
        )
    
    errors = []
    imported = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        row_num = idx + 2
        
        try:
            meter_value = float(row['Meter value(kW.h)'])
        except (ValueError, TypeError):
            errors.append(ImportValidationError(
                row=row_num,
                field="Meter value(kW.h)",
                message="Invalid number format"
            ))
            continue
        
        if meter_value == 0:
            skipped += 1
            continue
        
        if pd.isna(row['TxID']) or str(row['TxID']).strip() == '':
            errors.append(ImportValidationError(
                row=row_num,
                field="TxID",
                message="TxID is required"
            ))
            continue
        
        existing = await db.transactions.find_one({"tx_id": str(row['TxID'])})
        if existing:
            skipped += 1
            continue
        
        account = str(row['Account']) if not pd.isna(row['Account']) else ""
        connector = str(row['Connector']) if not pd.isna(row['Connector']) else ""
        connector_type = str(row.get('Connector Type', '')) if 'Connector Type' in df.columns and not pd.isna(row.get('Connector Type')) else None
        
        price_per_kwh = await get_pricing(account, connector, connector_type)
        cost = meter_value * price_per_kwh
        
        start_time = str(row['Start Time']) if not pd.isna(row['Start Time']) else ""
        end_time = str(row['End Time']) if not pd.isna(row['End Time']) else ""
        charging_duration = calculate_charging_duration(start_time, end_time)
        
        transaction = {
            "id": str(uuid.uuid4()),
            "tx_id": str(row['TxID']),
            "station": str(row['Station']),
            "connector": connector,
            "connector_type": connector_type,
            "account": account,
            "start_time": start_time,
            "end_time": end_time,
            "meter_value": meter_value,
            "charging_duration": charging_duration,
            "cost": round(cost, 2),
            "payment_status": "UNPAID",
            "payment_type": None,
            "payment_date": None,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        await db.transactions.insert_one(transaction)
        imported += 1
    
    return ImportResult(
        success=len(errors) == 0,
        imported_count=imported,
        skipped_count=skipped,
        errors=errors
    )

# Dashboard Stats
@api_router.get("/dashboard/stats", response_model=DashboardStats)
async def get_dashboard_stats(current_user: User = Depends(get_current_user)):
    total_transactions = await db.transactions.count_documents({})
    
    pipeline = [
        {"$group": {
            "_id": None,
            "total_energy": {"$sum": "$meter_value"},
            "total_revenue": {"$sum": "$cost"}
        }}
    ]
    result = await db.transactions.aggregate(pipeline).to_list(1)
    total_energy = result[0]["total_energy"] if result else 0
    total_revenue = result[0]["total_revenue"] if result else 0
    
    # Calculate paid vs unpaid revenue
    paid_pipeline = [{"$match": {"payment_status": "PAID"}}, {"$group": {"_id": None, "paid_revenue": {"$sum": "$cost"}}}]
    paid_result = await db.transactions.aggregate(paid_pipeline).to_list(1)
    paid_revenue = paid_result[0]["paid_revenue"] if paid_result else 0
    unpaid_revenue = total_revenue - paid_revenue
    
    # Payment breakdown
    payment_pipeline = [{"$match": {"payment_status": "PAID"}}, {"$group": {"_id": "$payment_type", "count": {"$sum": 1}, "amount": {"$sum": "$cost"}}}]
    payment_results = await db.transactions.aggregate(payment_pipeline).to_list(10)
    payment_breakdown = {item["_id"]: {"count": item["count"], "amount": item["amount"]} for item in payment_results if item["_id"]}
    
    stations = await db.transactions.distinct("station")
    active_stations = len(stations)
    
    accounts = await db.transactions.distinct("account")
    unique_accounts = len(accounts)
    
    recent = await db.transactions.find({}, {"_id": 0}).sort("start_time", -1).limit(5).to_list(5)
    recent_transactions = [Transaction(**t) for t in recent]
    
    return DashboardStats(
        total_transactions=total_transactions,
        total_energy=round(total_energy, 2),
        total_revenue=round(total_revenue, 2),
        paid_revenue=round(paid_revenue, 2),
        unpaid_revenue=round(unpaid_revenue, 2),
        active_stations=active_stations,
        unique_accounts=unique_accounts,
        payment_breakdown=payment_breakdown,
        recent_transactions=recent_transactions
    )

# User Management
@api_router.get("/users", response_model=List[User])
async def get_users(current_user: User = Depends(require_role(UserRole.ADMIN))):
    users = await db.users.find({}, {"_id": 0, "password_hash": 0}).to_list(100)
    return [User(**u) for u in users]

@api_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

@api_router.patch("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    if role not in [UserRole.ADMIN, UserRole.USER, UserRole.VIEWER]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    result = await db.users.update_one({"id": user_id}, {"$set": {"role": role}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Role updated successfully"}

@api_router.post("/users", response_model=User)
async def create_user(
    user_data: UserCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Create a new user (Admin only)"""
    # Check if email already exists
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    if user_data.role not in [UserRole.ADMIN, UserRole.USER, UserRole.VIEWER]:
        raise HTTPException(status_code=400, detail="Invalid role")
    
    password_hash = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    new_user = {
        "id": str(uuid.uuid4()),
        "name": user_data.name,
        "email": user_data.email,
        "password_hash": password_hash,
        "role": user_data.role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.users.insert_one(new_user)
    
    return User(**{k: v for k, v in new_user.items() if k not in ['_id', 'password_hash']})

# User Import Models
class UserImportResult(BaseModel):
    imported: int
    skipped: int
    errors: List[dict]

@api_router.post("/users/import", response_model=UserImportResult)
async def import_users(
    file: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Import users from Excel/CSV file (Admin only)
    
    Required columns: Name, Email, Role (optional, defaults to 'user')
    Optional columns: Password (if not provided, a default password will be generated)
    """
    if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
        raise HTTPException(status_code=400, detail="File must be Excel (.xlsx, .xls) or CSV (.csv)")
    
    try:
        contents = await file.read()
        if file.filename.endswith('.csv'):
            import io
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read file: {str(e)}")
    
    # Create case-insensitive column mapping
    df_columns_lower = {col.lower().strip(): col for col in df.columns}
    
    # Map columns
    name_col = None
    email_col = None
    role_col = None
    password_col = None
    group_col = None
    
    for col_lower, col_orig in df_columns_lower.items():
        if col_lower in ['name', 'nombre', 'full name', 'fullname']:
            name_col = col_orig
        elif col_lower in ['email', 'correo', 'e-mail', 'email address']:
            email_col = col_orig
        elif col_lower in ['role', 'rol', 'user role']:
            role_col = col_orig
        elif col_lower in ['password', 'contraseña', 'pass']:
            password_col = col_orig
        elif col_lower in ['group', 'grupo', 'pricing group', 'pricing_group']:
            group_col = col_orig
    
    if not name_col:
        raise HTTPException(status_code=400, detail="Missing required column: Name")
    if not email_col:
        raise HTTPException(status_code=400, detail="Missing required column: Email")
    
    # Get all pricing groups for mapping
    pricing_groups = {}
    async for group in db.pricing_groups.find({}, {"_id": 0}):
        pricing_groups[group["name"].lower()] = group["id"]
    
    imported = 0
    skipped = 0
    errors = []
    default_password = "ChangeMeNow123!"
    
    for idx, row in df.iterrows():
        row_num = idx + 2  # Excel rows start at 1, header is row 1
        
        name = str(row[name_col]).strip() if not pd.isna(row[name_col]) else ""
        email = str(row[email_col]).strip().lower() if not pd.isna(row[email_col]) else ""
        
        if not name:
            errors.append({"row": row_num, "field": "Name", "message": "Name is required"})
            continue
        
        if not email or '@' not in email:
            errors.append({"row": row_num, "field": "Email", "message": "Valid email is required"})
            continue
        
        # Check for existing user
        existing = await db.users.find_one({"email": email})
        if existing:
            skipped += 1
            continue
        
        # Get role
        role = "user"
        if role_col and not pd.isna(row.get(role_col)):
            role_value = str(row[role_col]).strip().lower()
            if role_value in ['admin', 'administrador']:
                role = "admin"
            elif role_value in ['viewer', 'visor', 'view']:
                role = "viewer"
            else:
                role = "user"
        
        # Get password
        password = default_password
        if password_col and not pd.isna(row.get(password_col)):
            password = str(row[password_col]).strip()
            if len(password) < 6:
                password = default_password
        
        # Create password hash
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Get pricing group
        pricing_group_id = None
        if group_col and not pd.isna(row.get(group_col)):
            group_name = str(row[group_col]).strip().lower()
            if group_name in pricing_groups:
                pricing_group_id = pricing_groups[group_name]
        
        new_user = {
            "id": str(uuid.uuid4()),
            "name": name,
            "email": email,
            "password_hash": password_hash,
            "role": role,
            "pricing_group_id": pricing_group_id,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        try:
            await db.users.insert_one(new_user)
            imported += 1
        except Exception as e:
            errors.append({"row": row_num, "field": "Database", "message": str(e)})
    
    return UserImportResult(imported=imported, skipped=skipped, errors=errors)

@api_router.patch("/users/{user_id}", response_model=User)
async def update_user(
    user_id: str,
    user_data: UserUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Update user details (Admin only)"""
    existing = await db.users.find_one({"id": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_dict = {}
    
    if user_data.name:
        update_dict["name"] = user_data.name
    
    if user_data.email:
        # Check if email already used by another user
        email_check = await db.users.find_one({"email": user_data.email, "id": {"$ne": user_id}})
        if email_check:
            raise HTTPException(status_code=400, detail="Email already in use")
        update_dict["email"] = user_data.email
    
    if user_data.password:
        update_dict["password_hash"] = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    if update_dict:
        await db.users.update_one({"id": user_id}, {"$set": update_dict})
    
    updated_user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    return User(**updated_user)

@api_router.get("/users/{user_id}", response_model=User)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Get a single user by ID"""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User(**user)

# RFID Card Management
@api_router.get("/rfid-cards", response_model=List[RFIDCard])
async def get_all_rfid_cards(current_user: User = Depends(require_role(UserRole.ADMIN))):
    """Get all RFID cards with user info"""
    cards = await db.rfid_cards.find({}, {"_id": 0}).to_list(500)
    
    # Enrich with user info
    for card in cards:
        user = await db.users.find_one({"id": card.get("user_id")}, {"_id": 0, "name": 1, "email": 1})
        if user:
            card["user_name"] = user.get("name", "Unknown")
            card["user_email"] = user.get("email", "")
    
    return [RFIDCard(**c) for c in cards]

@api_router.get("/rfid-cards/user/{user_id}", response_model=List[RFIDCard])
async def get_user_rfid_cards(
    user_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get RFID cards for a specific user"""
    cards = await db.rfid_cards.find({"user_id": user_id}, {"_id": 0}).to_list(50)
    
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "name": 1, "email": 1})
    for card in cards:
        if user:
            card["user_name"] = user.get("name", "Unknown")
            card["user_email"] = user.get("email", "")
    
    return [RFIDCard(**c) for c in cards]

@api_router.post("/rfid-cards", response_model=RFIDCard)
async def create_rfid_card(
    card_data: RFIDCardCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Create a new RFID card for a user"""
    # Check if card number already exists
    existing = await db.rfid_cards.find_one({"card_number": card_data.card_number})
    if existing:
        raise HTTPException(status_code=400, detail="Card number already exists")
    
    # Check if user exists
    user = await db.users.find_one({"id": card_data.user_id}, {"_id": 0, "name": 1, "email": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    card = {
        "id": str(uuid.uuid4()),
        **card_data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.rfid_cards.insert_one(card)
    
    card["user_name"] = user.get("name", "Unknown")
    card["user_email"] = user.get("email", "")
    
    return RFIDCard(**{k: v for k, v in card.items() if k != "_id"})

@api_router.patch("/rfid-cards/{card_id}", response_model=RFIDCard)
async def update_rfid_card(
    card_id: str,
    update_data: RFIDCardUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Update RFID card details"""
    existing = await db.rfid_cards.find_one({"id": card_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="RFID card not found")
    
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    # Check for duplicate card number
    if "card_number" in update_dict:
        duplicate = await db.rfid_cards.find_one({
            "card_number": update_dict["card_number"],
            "id": {"$ne": card_id}
        })
        if duplicate:
            raise HTTPException(status_code=400, detail="Card number already exists")
    
    if update_dict:
        await db.rfid_cards.update_one({"id": card_id}, {"$set": update_dict})
        existing.update(update_dict)
    
    # Get user info
    user = await db.users.find_one({"id": existing.get("user_id")}, {"_id": 0, "name": 1, "email": 1})
    if user:
        existing["user_name"] = user.get("name", "Unknown")
        existing["user_email"] = user.get("email", "")
    
    return RFIDCard(**existing)

@api_router.post("/rfid-cards/{card_id}/topup", response_model=RFIDCard)
async def topup_rfid_card(
    card_id: str,
    topup: RFIDTopUp,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Add balance to RFID card (manual top-up by admin)"""
    if topup.amount <= 0:
        raise HTTPException(status_code=400, detail="Top-up amount must be positive")
    
    existing = await db.rfid_cards.find_one({"id": card_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="RFID card not found")
    
    old_balance = existing.get("balance", 0)
    new_balance = old_balance + topup.amount
    
    await db.rfid_cards.update_one(
        {"id": card_id},
        {"$set": {"balance": new_balance}}
    )
    
    # Log history
    history_record = {
        "id": str(uuid.uuid4()),
        "card_id": card_id,
        "card_number": existing.get("card_number"),
        "type": "topup",
        "amount": topup.amount,
        "balance_before": old_balance,
        "balance_after": new_balance,
        "description": f"Manual Top-Up by {current_user.email}",
        "reference_id": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.rfid_history.insert_one(history_record)
    
    existing["balance"] = new_balance
    
    # Get user info
    user = await db.users.find_one({"id": existing.get("user_id")}, {"_id": 0, "name": 1, "email": 1})
    if user:
        existing["user_name"] = user.get("name", "Unknown")
        existing["user_email"] = user.get("email", "")
    
    return RFIDCard(**existing)

@api_router.delete("/rfid-cards/{card_id}")
async def delete_rfid_card(
    card_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Delete an RFID card"""
    result = await db.rfid_cards.delete_one({"id": card_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="RFID card not found")
    return {"message": "RFID card deleted successfully"}

# RFID Card History
@api_router.get("/rfid-cards/{card_id}/history", response_model=List[RFIDHistory])
async def get_rfid_card_history(
    card_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get transaction history for an RFID card"""
    history = await db.rfid_history.find({"card_id": card_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [RFIDHistory(**h) for h in history]

async def log_rfid_history(card_id: str, card_number: str, history_type: str, 
                          amount: float, balance_before: float, balance_after: float,
                          description: str, reference_id: str = None):
    """Helper function to log RFID card transactions"""
    history_record = {
        "id": str(uuid.uuid4()),
        "card_id": card_id,
        "card_number": card_number,
        "type": history_type,
        "amount": amount,
        "balance_before": balance_before,
        "balance_after": balance_after,
        "description": description,
        "reference_id": reference_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.rfid_history.insert_one(history_record)
    return history_record

# PayU Colombia Integration for RFID Top-Up
def generate_payu_signature(api_key: str, merchant_id: str, reference_code: str, amount: str, currency: str) -> str:
    """Generate MD5 signature for PayU WebCheckout"""
    signature_string = f"{api_key}~{merchant_id}~{reference_code}~{amount}~{currency}"
    return hashlib.md5(signature_string.encode()).hexdigest()

@api_router.post("/payu/initiate-topup")
async def initiate_payu_topup(
    topup_request: PayUTopUpRequest,
    current_user: User = Depends(get_current_user)
):
    """Initiate PayU payment for RFID card top-up"""
    # Validate RFID card exists
    card = await db.rfid_cards.find_one({"id": topup_request.rfid_card_id}, {"_id": 0})
    if not card:
        raise HTTPException(status_code=404, detail="RFID card not found")
    
    if card.get("status") != "active":
        raise HTTPException(status_code=400, detail="RFID card is not active")
    
    # Generate unique reference code
    reference_code = f"TOPUP-{uuid.uuid4().hex[:12].upper()}"
    amount_str = f"{topup_request.amount:.2f}"
    
    # Generate PayU signature
    signature = generate_payu_signature(
        PAYU_API_KEY,
        PAYU_MERCHANT_ID,
        reference_code,
        amount_str,
        "COP"
    )
    
    # Create pending payment record
    payment_record = {
        "id": str(uuid.uuid4()),
        "reference_code": reference_code,
        "rfid_card_id": topup_request.rfid_card_id,
        "card_number": card.get("card_number"),
        "user_id": card.get("user_id"),
        "amount": topup_request.amount,
        "buyer_name": topup_request.buyer_name,
        "buyer_email": topup_request.buyer_email,
        "buyer_phone": topup_request.buyer_phone,
        "status": "PENDING",
        "payu_response": {},
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.payu_payments.insert_one(payment_record)
    
    # Return PayU WebCheckout form data
    return {
        "payment_id": payment_record["id"],
        "reference_code": reference_code,
        "payu_url": PAYU_API_URL,
        "form_data": {
            "merchantId": PAYU_MERCHANT_ID,
            "accountId": PAYU_ACCOUNT_ID,
            "description": f"RFID Card Top-Up - {card.get('card_number')}",
            "referenceCode": reference_code,
            "amount": amount_str,
            "tax": "0",
            "taxReturnBase": "0",
            "currency": "COP",
            "signature": signature,
            "test": "1" if PAYU_TEST_MODE else "0",
            "buyerEmail": topup_request.buyer_email,
            "buyerFullName": topup_request.buyer_name,
            "telephone": topup_request.buyer_phone,
            "responseUrl": f"{FRONTEND_URL}/payment-response",
            "confirmationUrl": f"{os.environ.get('BACKEND_URL', 'http://localhost:8001')}/api/payu/webhook"
        }
    }

@api_router.post("/payu/webhook")
async def payu_webhook(request: Request):
    """Handle PayU payment confirmation webhook"""
    try:
        form_data = await request.form()
        webhook_data = dict(form_data)
        
        reference_code = webhook_data.get('reference_sale', '')
        state_pol = webhook_data.get('state_pol', '')
        response_code = webhook_data.get('response_code_pol', '')
        transaction_id = webhook_data.get('transaction_id', '')
        
        # Map PayU states: 4=Approved, 6=Declined, 5=Expired, 7=Pending
        status_mapping = {
            '4': 'APPROVED',
            '6': 'DECLINED',
            '5': 'EXPIRED',
            '7': 'PENDING'
        }
        payment_status = status_mapping.get(state_pol, 'UNKNOWN')
        
        # Find and update payment record
        payment = await db.payu_payments.find_one({"reference_code": reference_code})
        
        if payment:
            await db.payu_payments.update_one(
                {"reference_code": reference_code},
                {"$set": {
                    "status": payment_status,
                    "payu_response": webhook_data,
                    "payu_transaction_id": transaction_id,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            # If payment approved, top up the RFID card
            if payment_status == 'APPROVED':
                card = await db.rfid_cards.find_one({"id": payment["rfid_card_id"]})
                if card:
                    old_balance = card.get("balance", 0)
                    new_balance = old_balance + payment["amount"]
                    
                    await db.rfid_cards.update_one(
                        {"id": payment["rfid_card_id"]},
                        {"$set": {"balance": new_balance}}
                    )
                    
                    # Log history
                    await log_rfid_history(
                        card_id=payment["rfid_card_id"],
                        card_number=card.get("card_number"),
                        history_type="topup",
                        amount=payment["amount"],
                        balance_before=old_balance,
                        balance_after=new_balance,
                        description=f"PayU Online Top-Up ({reference_code})",
                        reference_id=reference_code
                    )
        
        # Log webhook for audit
        await db.payu_webhook_logs.insert_one({
            "id": str(uuid.uuid4()),
            "reference_code": reference_code,
            "webhook_data": webhook_data,
            "received_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {"status": "received"}
    except Exception as e:
        logging.error(f"PayU webhook error: {str(e)}")
        return {"status": "error", "message": str(e)}

@api_router.get("/payu/payment-status/{reference_code}")
async def get_payu_payment_status(
    reference_code: str,
    current_user: User = Depends(get_current_user)
):
    """Get payment status for a PayU transaction"""
    payment = await db.payu_payments.find_one({"reference_code": reference_code}, {"_id": 0})
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment

# Filters
@api_router.get("/filters/stations")
async def get_stations(current_user: User = Depends(get_current_user)):
    stations = await db.transactions.distinct("station")
    return sorted([s for s in stations if s])

@api_router.get("/filters/accounts")
async def get_accounts(current_user: User = Depends(get_current_user)):
    accounts = await db.transactions.distinct("account")
    return sorted([a for a in accounts if a])

# OCPP 1.6 Endpoints
@api_router.post("/ocpp/boot-notification")
async def ocpp_boot_notification(data: OCPPBootNotification):
    """OCPP 1.6 BootNotification"""
    boot_record = {
        "id": str(uuid.uuid4()),
        "vendor": data.chargePointVendor,
        "model": data.chargePointModel,
        "serial": data.chargePointSerialNumber,
        "firmware": data.firmwareVersion,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "Accepted"
    }
    await db.ocpp_boots.insert_one(boot_record)
    
    return {
        "status": "Accepted",
        "currentTime": datetime.now(timezone.utc).isoformat(),
        "interval": 300
    }

@api_router.post("/ocpp/heartbeat")
async def ocpp_heartbeat():
    """OCPP 1.6 Heartbeat"""
    return {"currentTime": datetime.now(timezone.utc).isoformat()}

@api_router.post("/ocpp/start-transaction")
async def ocpp_start_transaction(data: OCPPStartTransaction):
    """OCPP 1.6 StartTransaction"""
    transaction_id = abs(hash(data.idTag + data.timestamp)) % (10 ** 8)
    
    ocpp_transaction = {
        "transaction_id": transaction_id,
        "connector_id": data.connectorId,
        "id_tag": data.idTag,
        "meter_start": data.meterStart,
        "start_timestamp": data.timestamp,
        "status": "active"
    }
    await db.ocpp_transactions.insert_one(ocpp_transaction)
    
    return {"transactionId": transaction_id}

@api_router.post("/ocpp/stop-transaction")
async def ocpp_stop_transaction(data: OCPPStopTransaction):
    """OCPP 1.6 StopTransaction"""
    ocpp_tx = await db.ocpp_transactions.find_one({"transaction_id": data.transactionId})
    
    if ocpp_tx:
        energy_consumed = (data.meterStop - ocpp_tx["meter_start"]) / 1000.0
        
        await db.ocpp_transactions.update_one(
            {"transaction_id": data.transactionId},
            {"$set": {
                "meter_stop": data.meterStop,
                "stop_timestamp": data.timestamp,
                "energy_consumed": energy_consumed,
                "status": "completed"
            }}
        )
    
    return {"status": "Accepted"}

@api_router.get("/ocpp/status")
async def get_ocpp_status(current_user: User = Depends(get_current_user)):
    """Get OCPP connection status"""
    active_transactions = await db.ocpp_transactions.count_documents({"status": "active"})
    total_boots = await db.ocpp_boots.count_documents({})
    
    return {
        "active_transactions": active_transactions,
        "total_boots": total_boots,
        "ocpp_version": "1.6"
    }

@api_router.get("/ocpp/boots")
async def get_ocpp_boots(current_user: User = Depends(get_current_user)):
    """Get all registered charge points"""
    boots = await db.ocpp_boots.find({}, {"_id": 0}).sort("timestamp", -1).to_list(50)
    return boots

@api_router.get("/ocpp/active-transactions")
async def get_active_ocpp_transactions(current_user: User = Depends(get_current_user)):
    """Get active OCPP transactions"""
    active_txs = await db.ocpp_transactions.find({"status": "active"}, {"_id": 0}).to_list(50)
    return active_txs

# Charger Management
@api_router.get("/chargers", response_model=List[Charger])
async def get_chargers(current_user: User = Depends(get_current_user)):
    chargers = await db.chargers.find({}, {"_id": 0}).to_list(100)
    return [Charger(**c) for c in chargers]

@api_router.post("/chargers", response_model=Charger)
async def create_charger(
    charger_data: ChargerCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    charger = {
        "id": str(uuid.uuid4()),
        **charger_data.model_dump(),
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.chargers.insert_one(charger)
    return Charger(**{k: v for k, v in charger.items() if k != "_id"})

@api_router.patch("/chargers/{charger_id}", response_model=Charger)
async def update_charger(
    charger_id: str,
    update_data: ChargerUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    update_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    if update_dict:
        result = await db.chargers.update_one({"id": charger_id}, {"$set": update_dict})
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Charger not found")
    
    charger = await db.chargers.find_one({"id": charger_id}, {"_id": 0})
    return Charger(**charger)

@api_router.delete("/chargers/{charger_id}")
async def delete_charger(
    charger_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    result = await db.chargers.delete_one({"id": charger_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Charger not found")
    return {"message": "Charger deleted successfully"}

# OCPP Remote Control
@api_router.post("/ocpp/remote-start")
async def remote_start_transaction(
    request: RemoteStartRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.USER))
):
    """OCPP 1.6 RemoteStartTransaction - Linked to RFID cards"""
    # Check if id_tag is an RFID card number
    rfid_card = await db.rfid_cards.find_one({"card_number": request.id_tag}, {"_id": 0})
    
    if rfid_card:
        # Validate RFID card is active
        if rfid_card.get("status") != "active":
            raise HTTPException(status_code=400, detail="RFID card is not active")
        
        # Check minimum balance (e.g., 5000 COP)
        min_balance = 5000
        if rfid_card.get("balance", 0) < min_balance:
            raise HTTPException(status_code=400, detail=f"Insufficient balance. Minimum {min_balance} COP required")
    
    transaction_id = abs(hash(request.id_tag + datetime.now(timezone.utc).isoformat())) % (10 ** 8)
    
    ocpp_transaction = {
        "transaction_id": transaction_id,
        "charger_id": request.charger_id,
        "connector_id": request.connector_id,
        "id_tag": request.id_tag,
        "rfid_card_id": rfid_card.get("id") if rfid_card else None,
        "meter_start": 0,
        "start_timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "active",
        "remote_start": True
    }
    await db.ocpp_transactions.insert_one(ocpp_transaction)
    
    # Update charger status
    await db.chargers.update_one(
        {"id": request.charger_id},
        {"$set": {"status": "Charging"}}
    )
    
    return {
        "status": "Accepted",
        "transactionId": transaction_id,
        "rfid_linked": rfid_card is not None
    }

@api_router.post("/ocpp/remote-stop")
async def remote_stop_transaction(
    request: RemoteStopRequest,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.USER))
):
    """OCPP 1.6 RemoteStopTransaction - Auto deduct from RFID card"""
    ocpp_tx = await db.ocpp_transactions.find_one({"transaction_id": request.transaction_id})
    
    if not ocpp_tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Calculate energy consumed (simulated: random between 1-50 kWh for demo)
    import random
    energy_consumed = round(random.uniform(1, 50), 2)
    
    # Get charger connector type for pricing
    charger = await db.chargers.find_one({"id": ocpp_tx.get("charger_id")}, {"_id": 0})
    connector_type = charger.get("connector_types", ["CCS2"])[0] if charger else "CCS2"
    price_per_kwh = CONNECTOR_TYPE_PRICING.get(connector_type, 2000.0)
    cost = round(energy_consumed * price_per_kwh, 0)
    
    stop_timestamp = datetime.now(timezone.utc).isoformat()
    
    # Auto deduct from RFID card if linked
    rfid_deducted = False
    rfid_card = None
    if ocpp_tx.get("rfid_card_id"):
        rfid_card = await db.rfid_cards.find_one({"id": ocpp_tx["rfid_card_id"]}, {"_id": 0})
        if rfid_card:
            old_balance = rfid_card.get("balance", 0)
            new_balance = max(0, old_balance - cost)
            
            await db.rfid_cards.update_one(
                {"id": rfid_card["id"]},
                {"$set": {"balance": new_balance}}
            )
            
            # Log RFID history
            await log_rfid_history(
                card_id=rfid_card["id"],
                card_number=rfid_card.get("card_number"),
                history_type="charge",
                amount=-cost,
                balance_before=old_balance,
                balance_after=new_balance,
                description=f"Charging session #{request.transaction_id} - {energy_consumed} kWh",
                reference_id=str(request.transaction_id)
            )
            rfid_deducted = True
            
            # Check if balance fell below threshold and send notification
            threshold = rfid_card.get("low_balance_threshold", 10000)
            if new_balance < threshold and old_balance >= threshold:
                # Get user info for email
                user = await db.users.find_one({"id": rfid_card.get("user_id")}, {"_id": 0})
                if user and user.get("email"):
                    # Update card with new balance for email
                    rfid_card["balance"] = new_balance
                    await send_low_balance_email(rfid_card, user["email"], user.get("name", "User"))
    
    await db.ocpp_transactions.update_one(
        {"transaction_id": request.transaction_id},
        {"$set": {
            "status": "completed",
            "stop_timestamp": stop_timestamp,
            "energy_consumed": energy_consumed,
            "cost": cost,
            "connector_type": connector_type,
            "rfid_deducted": rfid_deducted
        }}
    )
    
    # Update charger status
    if "charger_id" in ocpp_tx:
        await db.chargers.update_one(
            {"id": ocpp_tx["charger_id"]},
            {"$set": {"status": "Available"}}
        )
    
    # Trigger invoice webhook if configured
    await trigger_invoice_webhook(ocpp_tx, energy_consumed, cost, connector_type, stop_timestamp, rfid_card)
    
    return {
        "status": "Accepted",
        "energy_consumed": energy_consumed,
        "cost": cost,
        "rfid_deducted": rfid_deducted,
        "new_balance": rfid_card.get("balance", 0) - cost if rfid_card else None
    }

# Invoice Webhook API for 3rd Party Integration
async def trigger_invoice_webhook(ocpp_tx: dict, energy: float, cost: float, 
                                 connector_type: str, stop_time: str, rfid_card: dict = None):
    """Send transaction data to configured webhook endpoint"""
    webhook_config = await db.invoice_webhook_config.find_one({}, {"_id": 0})
    
    if not webhook_config or not webhook_config.get("enabled"):
        return
    
    webhook_url = webhook_config.get("webhook_url")
    if not webhook_url:
        return
    
    # Get user info if RFID card linked
    user_email = None
    if rfid_card:
        user = await db.users.find_one({"id": rfid_card.get("user_id")}, {"_id": 0, "email": 1})
        user_email = user.get("email") if user else None
    
    payload = {
        "event_type": "transaction_completed",
        "transaction_id": str(ocpp_tx.get("transaction_id")),
        "tx_id": f"OCPP-{ocpp_tx.get('transaction_id')}",
        "account": rfid_card.get("card_number") if rfid_card else ocpp_tx.get("id_tag"),
        "station": ocpp_tx.get("charger_id", "Unknown"),
        "connector": str(ocpp_tx.get("connector_id", 1)),
        "connector_type": connector_type,
        "start_time": ocpp_tx.get("start_timestamp"),
        "end_time": stop_time,
        "charging_duration": None,  # Could calculate from timestamps
        "meter_value": energy,
        "cost": cost,
        "payment_status": "PAID" if rfid_card else "UNPAID",
        "payment_type": "RFID" if rfid_card else None,
        "payment_date": stop_time if rfid_card else None,
        "rfid_card_number": rfid_card.get("card_number") if rfid_card else None,
        "user_email": user_email,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        headers = {"Content-Type": "application/json"}
        if webhook_config.get("api_key"):
            headers["X-API-Key"] = webhook_config["api_key"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, headers=headers, timeout=10.0)
            
            # Log webhook delivery
            await db.invoice_webhook_logs.insert_one({
                "id": str(uuid.uuid4()),
                "transaction_id": str(ocpp_tx.get("transaction_id")),
                "webhook_url": webhook_url,
                "payload": payload,
                "response_status": response.status_code,
                "response_body": response.text[:500],
                "created_at": datetime.now(timezone.utc).isoformat()
            })
    except Exception as e:
        logging.error(f"Invoice webhook error: {str(e)}")
        await db.invoice_webhook_logs.insert_one({
            "id": str(uuid.uuid4()),
            "transaction_id": str(ocpp_tx.get("transaction_id")),
            "webhook_url": webhook_url,
            "payload": payload,
            "error": str(e),
            "created_at": datetime.now(timezone.utc).isoformat()
        })

@api_router.get("/invoice-webhook/config")
async def get_invoice_webhook_config(current_user: User = Depends(require_role(UserRole.ADMIN))):
    """Get current invoice webhook configuration"""
    config = await db.invoice_webhook_config.find_one({}, {"_id": 0})
    return config or {"webhook_url": "", "api_key": "", "enabled": False}

@api_router.post("/invoice-webhook/config")
async def set_invoice_webhook_config(
    config: InvoiceWebhookConfig,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Configure invoice webhook for 3rd party integration"""
    existing = await db.invoice_webhook_config.find_one({})
    
    config_data = {
        "webhook_url": config.webhook_url,
        "api_key": config.api_key,
        "enabled": config.enabled,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user.email
    }
    
    if existing:
        await db.invoice_webhook_config.update_one({}, {"$set": config_data})
        config_data["id"] = existing.get("id", str(uuid.uuid4()))
        config_data["created_at"] = existing.get("created_at")
    else:
        config_data["id"] = str(uuid.uuid4())
        config_data["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.invoice_webhook_config.insert_one(config_data)
    
    # Return without _id
    return {k: v for k, v in config_data.items() if k != "_id"}

@api_router.get("/invoice-webhook/logs")
async def get_invoice_webhook_logs(
    limit: int = Query(default=50, le=100),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Get invoice webhook delivery logs"""
    logs = await db.invoice_webhook_logs.find({}, {"_id": 0}).sort("created_at", -1).to_list(limit)
    return logs

@api_router.post("/invoice-webhook/test")
async def test_invoice_webhook(current_user: User = Depends(require_role(UserRole.ADMIN))):
    """Send a test webhook to the configured endpoint"""
    config = await db.invoice_webhook_config.find_one({}, {"_id": 0})
    
    if not config or not config.get("webhook_url"):
        raise HTTPException(status_code=400, detail="No webhook URL configured")
    
    test_payload = {
        "event_type": "test",
        "message": "This is a test webhook from EV Charging System",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        headers = {"Content-Type": "application/json"}
        if config.get("api_key"):
            headers["X-API-Key"] = config["api_key"]
        
        async with httpx.AsyncClient() as client:
            response = await client.post(config["webhook_url"], json=test_payload, headers=headers, timeout=10.0)
            
            return {
                "success": response.status_code < 400,
                "status_code": response.status_code,
                "response": response.text[:500]
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Webhook test failed: {str(e)}")

# Settings API
@api_router.get("/settings/payu")
async def get_payu_settings(current_user: User = Depends(require_role(UserRole.ADMIN))):
    """Get PayU configuration (masked API key)"""
    settings = await db.settings.find_one({"type": "payu"}, {"_id": 0})
    if settings:
        # Mask API key for security
        if settings.get("api_key"):
            settings["api_key"] = settings["api_key"][:4] + "****" + settings["api_key"][-4:]
    return settings or {"type": "payu", "api_key": "", "api_login": "", "merchant_id": "", "account_id": "", "test_mode": True}

@api_router.post("/settings/payu")
async def save_payu_settings(
    settings: PayUSettings,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Save PayU configuration"""
    existing = await db.settings.find_one({"type": "payu"})
    
    settings_data = {
        "type": "payu",
        **settings.model_dump(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user.email
    }
    
    if existing:
        await db.settings.update_one({"type": "payu"}, {"$set": settings_data})
    else:
        settings_data["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.settings.insert_one(settings_data)
    
    return {"message": "PayU settings saved successfully"}

@api_router.get("/settings/sendgrid")
async def get_sendgrid_settings(current_user: User = Depends(require_role(UserRole.ADMIN))):
    """Get SendGrid configuration (masked API key)"""
    settings = await db.settings.find_one({"type": "sendgrid"}, {"_id": 0})
    if settings:
        if settings.get("api_key"):
            settings["api_key"] = settings["api_key"][:4] + "****" + settings["api_key"][-4:]
    return settings or {"type": "sendgrid", "api_key": "", "sender_email": "", "sender_name": "EV Charging System", "enabled": False}

@api_router.post("/settings/sendgrid")
async def save_sendgrid_settings(
    settings: SendGridSettings,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Save SendGrid configuration"""
    existing = await db.settings.find_one({"type": "sendgrid"})
    
    settings_data = {
        "type": "sendgrid",
        **settings.model_dump(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "updated_by": current_user.email
    }
    
    if existing:
        await db.settings.update_one({"type": "sendgrid"}, {"$set": settings_data})
    else:
        settings_data["created_at"] = datetime.now(timezone.utc).isoformat()
        await db.settings.insert_one(settings_data)
    
    return {"message": "SendGrid settings saved successfully"}

@api_router.post("/settings/sendgrid/test")
async def test_sendgrid_email(
    test_email: str = Query(..., description="Email address to send test to"),
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    """Send a test email via SendGrid"""
    settings = await db.settings.find_one({"type": "sendgrid"}, {"_id": 0})
    
    if not settings or not settings.get("api_key"):
        raise HTTPException(status_code=400, detail="SendGrid not configured")
    
    try:
        sg = SendGridAPIClient(settings["api_key"])
        
        message = Mail(
            from_email=(settings.get("sender_email"), settings.get("sender_name", "EV Charging System")),
            to_emails=test_email,
            subject="Test Email - EV Charging System",
            html_content="""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Test Email</h2>
                <p>This is a test email from your EV Charging System.</p>
                <p>If you received this, SendGrid is configured correctly!</p>
            </body>
            </html>
            """
        )
        
        response = sg.send(message)
        
        return {
            "success": response.status_code == 202,
            "status_code": response.status_code,
            "message": "Test email sent successfully" if response.status_code == 202 else "Failed to send"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send test email: {str(e)}")

# Invoice Generation
@api_router.get("/transactions/{transaction_id}/invoice")
async def generate_invoice(
    transaction_id: str,
    current_user: User = Depends(get_current_user)
):
    """Generate PDF invoice for a paid transaction"""
    transaction = await db.transactions.find_one({"id": transaction_id}, {"_id": 0})
    
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    if transaction.get("payment_status") != "PAID":
        raise HTTPException(status_code=400, detail="Transaction is not paid")
    
    # Create PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    
    # Title
    title = Paragraph("<b>SMART CHARGE - INVOICE</b>", styles['Title'])
    elements.append(title)
    elements.append(Spacer(1, 0.3*inch))
    
    # Invoice details
    invoice_data = [
        ['Invoice #:', transaction['tx_id']],
        ['Date:', transaction.get('payment_date', 'N/A')],
        ['Account:', transaction['account']],
        ['', ''],
        ['Station:', transaction['station']],
        ['Connector:', transaction['connector']],
        ['Connector Type:', transaction.get('connector_type', 'N/A')],
        ['', ''],
        ['Start Time:', transaction['start_time']],
        ['End Time:', transaction['end_time']],
        ['Duration:', transaction.get('charging_duration', 'N/A')],
        ['', ''],
        ['Energy Consumed:', f"{transaction['meter_value']:.2f} kWh"],
        ['', ''],
        ['<b>Total Amount:</b>', f"<b>${transaction['cost']:,.0f} COP</b>"],
        ['Payment Method:', transaction.get('payment_type', 'N/A')],
        ['Payment Status:', 'PAID'],
    ]
    
    table = Table(invoice_data, colWidths=[3*inch, 3*inch])
    table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('FONTNAME', (0, 14), (-1, 14), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 14), (-1, 14), 14),
        ('TEXTCOLOR', (0, 14), (-1, 14), colors.HexColor('#EA580C')),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 0.5*inch))
    
    # Footer
    footer = Paragraph("<i>Thank you for using Smart Charge!</i>", styles['Normal'])
    elements.append(footer)
    
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=invoice_{transaction['tx_id']}.pdf"}
    )

# Advanced Reporting
@api_router.post("/reports/generate", response_model=ReportData)
async def generate_report(
    filters: ReportFilter,
    current_user: User = Depends(get_current_user)
):
    """Generate comprehensive report with filtering"""
    query = {}
    
    if filters.start_date:
        query["start_time"] = {"$gte": filters.start_date}
    if filters.end_date:
        if "start_time" in query:
            query["start_time"]["$lte"] = filters.end_date
        else:
            query["start_time"] = {"$lte": filters.end_date}
    if filters.account:
        query["account"] = filters.account
    if filters.connector_type:
        query["connector_type"] = filters.connector_type
    if filters.payment_type:
        query["payment_type"] = filters.payment_type
    if filters.payment_status:
        query["payment_status"] = filters.payment_status
    
    # Get transactions
    transactions = await db.transactions.find(query, {"_id": 0}).to_list(1000)
    
    # Summary
    total_transactions = len(transactions)
    total_energy = sum(t["meter_value"] for t in transactions)
    total_revenue = sum(t["cost"] for t in transactions)
    paid_count = len([t for t in transactions if t.get("payment_status") == "PAID"])
    paid_revenue = sum(t["cost"] for t in transactions if t.get("payment_status") == "PAID")
    
    summary = {
        "total_transactions": total_transactions,
        "total_energy": round(total_energy, 2),
        "total_revenue": round(total_revenue, 2),
        "paid_transactions": paid_count,
        "paid_revenue": round(paid_revenue, 2),
        "unpaid_revenue": round(total_revenue - paid_revenue, 2)
    }
    
    # By Account
    by_account = {}
    for tx in transactions:
        acc = tx["account"]
        if acc not in by_account:
            by_account[acc] = {"account": acc, "transactions": 0, "energy": 0, "revenue": 0}
        by_account[acc]["transactions"] += 1
        by_account[acc]["energy"] += tx["meter_value"]
        by_account[acc]["revenue"] += tx["cost"]
    
    by_account_list = [
        {**v, "energy": round(v["energy"], 2), "revenue": round(v["revenue"], 2)}
        for v in sorted(by_account.values(), key=lambda x: x["revenue"], reverse=True)
    ]
    
    # By Connector Type
    by_connector = {}
    for tx in transactions:
        conn_type = tx.get("connector_type", "Unknown")
        if conn_type not in by_connector:
            by_connector[conn_type] = {"connector_type": conn_type, "transactions": 0, "energy": 0, "revenue": 0}
        by_connector[conn_type]["transactions"] += 1
        by_connector[conn_type]["energy"] += tx["meter_value"]
        by_connector[conn_type]["revenue"] += tx["cost"]
    
    by_connector_list = [
        {**v, "energy": round(v["energy"], 2), "revenue": round(v["revenue"], 2)}
        for v in sorted(by_connector.values(), key=lambda x: x["revenue"], reverse=True)
    ]
    
    # By Payment Type
    by_payment = {}
    for tx in transactions:
        if tx.get("payment_status") == "PAID":
            payment_type = tx.get("payment_type", "Unknown")
            if payment_type not in by_payment:
                by_payment[payment_type] = {"payment_type": payment_type, "transactions": 0, "revenue": 0}
            by_payment[payment_type]["transactions"] += 1
            by_payment[payment_type]["revenue"] += tx["cost"]
    
    by_payment_list = [
        {**v, "revenue": round(v["revenue"], 2)}
        for v in sorted(by_payment.values(), key=lambda x: x["revenue"], reverse=True)
    ]
    
    return ReportData(
        summary=summary,
        by_account=by_account_list,
        by_connector=by_connector_list,
        by_payment_type=by_payment_list,
        transactions=[Transaction(**t) for t in transactions[:100]]
    )


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()