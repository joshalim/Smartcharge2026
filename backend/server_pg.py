"""
SmartCharge EV Charging Management System - PostgreSQL Server
This is a PostgreSQL-only version that eliminates MongoDB dependencies.
"""
from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, status, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
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
from contextlib import asynccontextmanager

# Load environment variables FIRST
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Starting SmartCharge Server (PostgreSQL)...")

# Import PostgreSQL database adapter
from database import init_db
from db_adapter import db

logger.info("Database modules imported successfully")

# JWT Configuration
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

# Lifespan for database initialization
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    await init_db()
    logger.info("Database initialized")
    
    # Create default admin user if not exists
    admin = await db.users.find_one({"email": "admin@evcharge.com"})
    if not admin:
        password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        await db.users.insert_one({
            "id": str(uuid.uuid4()),
            "email": "admin@evcharge.com",
            "name": "Admin User",
            "password_hash": password_hash,
            "role": "admin"
        })
        logger.info("Default admin user created")
    yield
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)
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

# ==================== Pydantic Models ====================

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
    created_at: Optional[str] = None

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
    connector_pricing: Optional[dict] = None

class PricingGroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    connector_pricing: Optional[dict] = None

class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    tx_id: Optional[str] = None
    station: Optional[str] = None
    connector: Optional[str] = None
    connector_type: Optional[str] = None
    account: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    meter_value: Optional[float] = 0
    charging_duration: Optional[str] = None
    cost: Optional[float] = 0
    payment_status: str = "PENDING"
    payment_type: Optional[str] = None
    payment_date: Optional[str] = None

class Charger(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    charger_id: str
    name: str
    location: Optional[str] = None
    status: str = "Available"
    connectors: List[str] = []
    last_heartbeat: Optional[str] = None

class ChargerCreate(BaseModel):
    charger_id: str
    name: str
    location: Optional[str] = None
    connectors: List[str] = []

class RFIDCard(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    card_number: str
    user_id: str
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    balance: float = 0
    status: str = "active"
    low_balance_threshold: float = 10000

class RFIDCardCreate(BaseModel):
    card_number: str
    user_id: str
    balance: float = 0
    low_balance_threshold: float = 10000

class TopUpRequest(BaseModel):
    amount: float
    description: Optional[str] = None

class AppConfigUpdate(BaseModel):
    config_type: str
    config_data: dict

# ==================== Helper Functions ====================

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        user = await db.users.find_one({"id": user_id})
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def require_admin(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def calculate_price(account: str, connector_type: str, kwh: float) -> float:
    base_price = CONNECTOR_TYPE_PRICING.get(connector_type, 2000.0)
    if account in SPECIAL_ACCOUNTS:
        return 0
    return kwh * base_price

# ==================== Auth Endpoints ====================

@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    existing = await db.users.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    password_hash = bcrypt.hashpw(user_data.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    user = {
        "id": str(uuid.uuid4()),
        "email": user_data.email,
        "name": user_data.name,
        "password_hash": password_hash,
        "role": user_data.role,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.users.insert_one(user)
    return {"message": "User registered successfully"}

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    user = await db.users.find_one({"email": credentials.email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not bcrypt.checkpw(credentials.password.encode('utf-8'), user["password_hash"].encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user["id"]})
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=User(
            id=user["id"],
            email=user["email"],
            name=user["name"],
            role=user["role"],
            pricing_group_id=user.get("pricing_group_id"),
            created_at=str(user.get("created_at")) if user.get("created_at") else None
        )
    )

@api_router.get("/auth/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    return User(
        id=current_user["id"],
        email=current_user["email"],
        name=current_user["name"],
        role=current_user["role"],
        pricing_group_id=current_user.get("pricing_group_id"),
        created_at=str(current_user.get("created_at")) if current_user.get("created_at") else None
    )

# ==================== Health Check ====================

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "database": "postgresql", "timestamp": datetime.now(timezone.utc).isoformat()}

# ==================== Users Endpoints ====================

@api_router.get("/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    users = await db.users.find({})
    return [User(
        id=u["id"],
        email=u["email"],
        name=u["name"],
        role=u["role"],
        pricing_group_id=u.get("pricing_group_id"),
        created_at=str(u.get("created_at")) if u.get("created_at") else None
    ) for u in users]

@api_router.get("/users/{user_id}")
async def get_user(user_id: str, current_user: dict = Depends(get_current_user)):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return User(
        id=user["id"],
        email=user["email"],
        name=user["name"],
        role=user["role"],
        pricing_group_id=user.get("pricing_group_id"),
        created_at=str(user.get("created_at")) if user.get("created_at") else None
    )

@api_router.put("/users/{user_id}")
async def update_user(user_id: str, user_data: dict, current_user: dict = Depends(require_admin)):
    user = await db.users.find_one({"id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = {}
    if "name" in user_data:
        update_data["name"] = user_data["name"]
    if "email" in user_data:
        update_data["email"] = user_data["email"]
    if "role" in user_data:
        update_data["role"] = user_data["role"]
    if "pricing_group_id" in user_data:
        update_data["pricing_group_id"] = user_data["pricing_group_id"]
    if "password" in user_data and user_data["password"]:
        update_data["password_hash"] = bcrypt.hashpw(user_data["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    if update_data:
        await db.users.update_one({"id": user_id}, {"$set": update_data})
    
    updated_user = await db.users.find_one({"id": user_id})
    return User(
        id=updated_user["id"],
        email=updated_user["email"],
        name=updated_user["name"],
        role=updated_user["role"],
        pricing_group_id=updated_user.get("pricing_group_id"),
        created_at=str(updated_user.get("created_at")) if updated_user.get("created_at") else None
    )

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(require_admin)):
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}

@api_router.post("/users/import")
async def import_users(file: UploadFile = File(...), current_user: dict = Depends(require_admin)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    contents = await file.read()
    df = pd.read_excel(BytesIO(contents))
    
    required_columns = ['email', 'name']
    for col in required_columns:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Missing required column: {col}")
    
    imported = 0
    skipped = 0
    errors = []
    
    for _, row in df.iterrows():
        try:
            email = str(row['email']).strip()
            name = str(row['name']).strip()
            role = str(row.get('role', 'user')).strip().lower()
            password = str(row.get('password', 'password123')).strip()
            
            if role not in ['admin', 'user', 'viewer']:
                role = 'user'
            
            existing = await db.users.find_one({"email": email})
            if existing:
                skipped += 1
                continue
            
            password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            user = {
                "id": str(uuid.uuid4()),
                "email": email,
                "name": name,
                "password_hash": password_hash,
                "role": role,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            await db.users.insert_one(user)
            imported += 1
        except Exception as e:
            errors.append(f"Row error: {str(e)}")
    
    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:10]
    }

# ==================== Transactions Endpoints ====================

@api_router.get("/transactions")
async def get_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = Depends(get_current_user)
):
    transactions = await db.transactions.find({}, skip=skip, limit=limit, sort=[("start_time", -1)])
    return [Transaction(**t) for t in transactions]

@api_router.get("/transactions/{tx_id}")
async def get_transaction(tx_id: str, current_user: dict = Depends(get_current_user)):
    tx = await db.transactions.find_one({"id": tx_id})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return Transaction(**tx)

@api_router.post("/transactions/import")
async def import_transactions(file: UploadFile = File(...), current_user: dict = Depends(require_admin)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    contents = await file.read()
    df = pd.read_excel(BytesIO(contents))
    
    imported = 0
    errors = []
    
    for _, row in df.iterrows():
        try:
            tx = {
                "id": str(uuid.uuid4()),
                "tx_id": str(row.get('Transaction Id', row.get('tx_id', ''))),
                "station": str(row.get('Station', row.get('station', ''))),
                "connector": str(row.get('Connector', row.get('connector', ''))),
                "connector_type": str(row.get('Connector Type', row.get('connector_type', ''))),
                "account": str(row.get('Account', row.get('account', ''))),
                "start_time": str(row.get('Start Time', row.get('start_time', ''))),
                "end_time": str(row.get('End Time', row.get('end_time', ''))),
                "meter_value": float(row.get('Meter Value (kWh)', row.get('meter_value', 0)) or 0),
                "charging_duration": str(row.get('Charging Duration', row.get('charging_duration', ''))),
                "payment_status": "PENDING",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Calculate cost
            tx["cost"] = calculate_price(tx["account"], tx["connector_type"], tx["meter_value"])
            
            await db.transactions.insert_one(tx)
            imported += 1
        except Exception as e:
            errors.append(str(e))
    
    return {"imported": imported, "errors": errors[:10]}

@api_router.post("/transactions/bulk-delete")
async def bulk_delete_transactions(data: dict, current_user: dict = Depends(require_admin)):
    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="No IDs provided")
    
    deleted = 0
    for tx_id in ids:
        result = await db.transactions.delete_one({"id": tx_id})
        deleted += result.deleted_count
    
    return {"deleted": deleted}

@api_router.put("/transactions/{tx_id}/payment")
async def update_payment_status(tx_id: str, data: dict, current_user: dict = Depends(require_admin)):
    tx = await db.transactions.find_one({"id": tx_id})
    if not tx:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    update = {
        "payment_status": data.get("payment_status", "PAID"),
        "payment_type": data.get("payment_type"),
        "payment_date": datetime.now(timezone.utc).isoformat()
    }
    
    await db.transactions.update_one({"id": tx_id}, {"$set": update})
    return {"message": "Payment updated"}

# ==================== Chargers Endpoints ====================

@api_router.get("/chargers")
async def get_chargers(current_user: dict = Depends(get_current_user)):
    chargers = await db.chargers.find({})
    return [Charger(**c) for c in chargers]

@api_router.post("/chargers")
async def create_charger(charger: ChargerCreate, current_user: dict = Depends(require_admin)):
    existing = await db.chargers.find_one({"charger_id": charger.charger_id})
    if existing:
        raise HTTPException(status_code=400, detail="Charger ID already exists")
    
    new_charger = {
        "id": str(uuid.uuid4()),
        "charger_id": charger.charger_id,
        "name": charger.name,
        "location": charger.location,
        "status": "Available",
        "connectors": charger.connectors,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.chargers.insert_one(new_charger)
    return Charger(**new_charger)

@api_router.put("/chargers/{charger_id}")
async def update_charger(charger_id: str, data: dict, current_user: dict = Depends(require_admin)):
    charger = await db.chargers.find_one({"id": charger_id})
    if not charger:
        raise HTTPException(status_code=404, detail="Charger not found")
    
    update_data = {}
    for field in ["name", "location", "status", "connectors"]:
        if field in data:
            update_data[field] = data[field]
    
    if update_data:
        await db.chargers.update_one({"id": charger_id}, {"$set": update_data})
    
    updated = await db.chargers.find_one({"id": charger_id})
    return Charger(**updated)

@api_router.delete("/chargers/{charger_id}")
async def delete_charger(charger_id: str, current_user: dict = Depends(require_admin)):
    result = await db.chargers.delete_one({"id": charger_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Charger not found")
    return {"message": "Charger deleted"}

# ==================== Pricing Groups Endpoints ====================

@api_router.get("/pricing-groups")
async def get_pricing_groups(current_user: dict = Depends(get_current_user)):
    groups = await db.pricing_groups.find({})
    result = []
    for g in groups:
        user_count = await db.users.count_documents({"pricing_group_id": g["id"]})
        result.append(PricingGroup(
            id=g["id"],
            name=g["name"],
            description=g.get("description"),
            connector_pricing=g.get("connector_pricing", CONNECTOR_TYPE_PRICING),
            user_count=user_count,
            created_at=str(g.get("created_at", "")),
            updated_at=str(g.get("updated_at", "")) if g.get("updated_at") else None
        ))
    return result

@api_router.post("/pricing-groups")
async def create_pricing_group(group: PricingGroupCreate, current_user: dict = Depends(require_admin)):
    existing = await db.pricing_groups.find_one({"name": group.name})
    if existing:
        raise HTTPException(status_code=400, detail="Group name already exists")
    
    new_group = {
        "id": str(uuid.uuid4()),
        "name": group.name,
        "description": group.description,
        "connector_pricing": group.connector_pricing or CONNECTOR_TYPE_PRICING,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.pricing_groups.insert_one(new_group)
    return PricingGroup(**new_group, user_count=0)

@api_router.put("/pricing-groups/{group_id}")
async def update_pricing_group(group_id: str, data: PricingGroupUpdate, current_user: dict = Depends(require_admin)):
    group = await db.pricing_groups.find_one({"id": group_id})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    update_data = {"updated_at": datetime.now(timezone.utc).isoformat()}
    if data.name is not None:
        update_data["name"] = data.name
    if data.description is not None:
        update_data["description"] = data.description
    if data.connector_pricing is not None:
        update_data["connector_pricing"] = data.connector_pricing
    
    await db.pricing_groups.update_one({"id": group_id}, {"$set": update_data})
    updated = await db.pricing_groups.find_one({"id": group_id})
    user_count = await db.users.count_documents({"pricing_group_id": group_id})
    return PricingGroup(**updated, user_count=user_count)

@api_router.delete("/pricing-groups/{group_id}")
async def delete_pricing_group(group_id: str, current_user: dict = Depends(require_admin)):
    # Remove group assignment from users
    await db.users.update_many({"pricing_group_id": group_id}, {"$set": {"pricing_group_id": None}})
    
    result = await db.pricing_groups.delete_one({"id": group_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"message": "Group deleted"}

@api_router.post("/pricing-groups/{group_id}/users")
async def assign_users_to_group(group_id: str, data: dict, current_user: dict = Depends(require_admin)):
    group = await db.pricing_groups.find_one({"id": group_id})
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    
    user_ids = data.get("user_ids", [])
    for user_id in user_ids:
        await db.users.update_one({"id": user_id}, {"$set": {"pricing_group_id": group_id}})
    
    return {"message": f"Assigned {len(user_ids)} users to group"}

@api_router.delete("/pricing-groups/{group_id}/users/{user_id}")
async def remove_user_from_group(group_id: str, user_id: str, current_user: dict = Depends(require_admin)):
    await db.users.update_one({"id": user_id, "pricing_group_id": group_id}, {"$set": {"pricing_group_id": None}})
    return {"message": "User removed from group"}

# ==================== RFID Cards Endpoints ====================

@api_router.get("/rfid-cards")
async def get_rfid_cards(current_user: dict = Depends(get_current_user)):
    cards = await db.rfid_cards.find({})
    result = []
    for card in cards:
        user = await db.users.find_one({"id": card["user_id"]})
        result.append(RFIDCard(
            id=card["id"],
            card_number=card["card_number"],
            user_id=card["user_id"],
            user_name=user["name"] if user else None,
            user_email=user["email"] if user else None,
            balance=card.get("balance", 0),
            status=card.get("status", "active"),
            low_balance_threshold=card.get("low_balance_threshold", 10000)
        ))
    return result

@api_router.post("/rfid-cards")
async def create_rfid_card(card: RFIDCardCreate, current_user: dict = Depends(require_admin)):
    existing = await db.rfid_cards.find_one({"card_number": card.card_number})
    if existing:
        raise HTTPException(status_code=400, detail="Card number already exists")
    
    user = await db.users.find_one({"id": card.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    new_card = {
        "id": str(uuid.uuid4()),
        "card_number": card.card_number,
        "user_id": card.user_id,
        "balance": card.balance,
        "status": "active",
        "low_balance_threshold": card.low_balance_threshold,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.rfid_cards.insert_one(new_card)
    return RFIDCard(**new_card, user_name=user["name"], user_email=user["email"])

@api_router.post("/rfid-cards/{card_id}/topup")
async def topup_rfid_card(card_id: str, topup: TopUpRequest, current_user: dict = Depends(require_admin)):
    card = await db.rfid_cards.find_one({"id": card_id})
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    
    old_balance = card.get("balance", 0)
    new_balance = old_balance + topup.amount
    
    await db.rfid_cards.update_one({"id": card_id}, {"$set": {"balance": new_balance}})
    
    # Record history
    history = {
        "id": str(uuid.uuid4()),
        "card_id": card_id,
        "type": "topup",
        "amount": topup.amount,
        "description": topup.description or "Manual top-up",
        "balance_before": old_balance,
        "balance_after": new_balance,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    await db.rfid_history.insert_one(history)
    
    return {"balance": new_balance, "message": "Top-up successful"}

@api_router.get("/rfid-cards/{card_id}/history")
async def get_rfid_history(card_id: str, current_user: dict = Depends(get_current_user)):
    history = await db.rfid_history.find({"card_id": card_id}, sort=[("timestamp", -1)])
    return history

@api_router.delete("/rfid-cards/{card_id}")
async def delete_rfid_card(card_id: str, current_user: dict = Depends(require_admin)):
    result = await db.rfid_cards.delete_one({"id": card_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Card not found")
    await db.rfid_history.delete_many({"card_id": card_id})
    return {"message": "Card deleted"}

# ==================== Settings/Config Endpoints ====================

@api_router.get("/settings")
async def get_settings(current_user: dict = Depends(require_admin)):
    configs = await db.app_config.find({})
    result = {}
    for config in configs:
        result[config["config_type"]] = config.get("config_data", {})
    return result

@api_router.put("/settings")
async def update_settings(config: AppConfigUpdate, current_user: dict = Depends(require_admin)):
    await db.app_config.update_one(
        {"config_type": config.config_type},
        {"$set": {"config_data": config.config_data, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True
    )
    return {"message": "Settings updated"}

# ==================== Dashboard/Stats Endpoints ====================

@api_router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    total_transactions = await db.transactions.count_documents({})
    total_energy = 0
    total_revenue = 0
    paid_revenue = 0
    unpaid_revenue = 0
    
    transactions = await db.transactions.find({})
    for tx in transactions:
        total_energy += tx.get("meter_value", 0) or 0
        cost = tx.get("cost", 0) or 0
        total_revenue += cost
        if tx.get("payment_status") == "PAID":
            paid_revenue += cost
        else:
            unpaid_revenue += cost
    
    active_chargers = await db.chargers.count_documents({"status": {"$ne": "Offline"}})
    unique_accounts = len(set([tx.get("account", "") for tx in await db.transactions.find({})]))
    
    return {
        "total_transactions": total_transactions,
        "total_energy": round(total_energy, 2),
        "total_revenue": round(total_revenue, 2),
        "paid_revenue": round(paid_revenue, 2),
        "unpaid_revenue": round(unpaid_revenue, 2),
        "active_chargers": active_chargers,
        "unique_accounts": unique_accounts
    }

# ==================== Reports Endpoints ====================

@api_router.get("/reports/transactions")
async def export_transactions_report(
    format: str = Query("json", enum=["json", "pdf"]),
    current_user: dict = Depends(get_current_user)
):
    transactions = await db.transactions.find({}, sort=[("start_time", -1)])
    
    if format == "json":
        return [Transaction(**tx) for tx in transactions]
    
    # Generate PDF
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    styles = getSampleStyleSheet()
    elements.append(Paragraph("Transactions Report", styles['Title']))
    elements.append(Spacer(1, 20))
    
    data = [["ID", "Account", "Station", "kWh", "Cost", "Status"]]
    for tx in transactions[:100]:  # Limit to 100 for PDF
        data.append([
            tx.get("tx_id", "")[:10],
            tx.get("account", "")[:15],
            tx.get("station", "")[:15],
            f"{tx.get('meter_value', 0):.2f}",
            f"${tx.get('cost', 0):,.0f}",
            tx.get("payment_status", "")
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=transactions_report.pdf"}
    )

# ==================== Include Router & CORS ====================

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("SmartCharge Server ready!")
