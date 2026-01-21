from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import bcrypt
import jwt
import pandas as pd
import openpyxl
from io import BytesIO

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

security = HTTPBearer()

# Create the main app
app = FastAPI()
api_router = APIRouter(prefix="/api")

# Models
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

class Transaction(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    tx_id: str
    station: str
    connector: str
    account: str
    start_time: str
    end_time: str
    meter_value: float
    cost: float
    created_at: str

class TransactionCreate(BaseModel):
    tx_id: str
    station: str
    connector: str
    account: str
    start_time: str
    end_time: str
    meter_value: float

class TransactionFilter(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    station: Optional[str] = None
    account: Optional[str] = None

class DashboardStats(BaseModel):
    total_transactions: int
    total_energy: float
    total_revenue: float
    active_stations: int
    unique_accounts: int
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

# Helper Functions
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

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

async def get_pricing(account: str, connector: str) -> float:
    """Get price per kWh for account/connector combination"""
    pricing = await db.pricing.find_one({"account": account, "connector": connector}, {"_id": 0})
    if pricing:
        return pricing['price_per_kwh']
    # Default pricing if not found
    default_pricing = await db.pricing.find_one({"account": account, "connector": "default"}, {"_id": 0})
    if default_pricing:
        return default_pricing['price_per_kwh']
    return 500.0  # Default COP per kWh

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
    # Check if rule exists
    existing = await db.pricing.find_one({
        "account": pricing_data.account,
        "connector": pricing_data.connector
    })
    
    if existing:
        # Update existing
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

# Transaction Routes
@api_router.post("/transactions", response_model=Transaction)
async def create_transaction(
    transaction_data: TransactionCreate,
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.USER))
):
    # Calculate cost
    price_per_kwh = await get_pricing(transaction_data.account, transaction_data.connector)
    cost = transaction_data.meter_value * price_per_kwh
    
    transaction = {
        "id": str(uuid.uuid4()),
        **transaction_data.model_dump(),
        "cost": round(cost, 2),
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
    
    transactions = await db.transactions.find(query, {"_id": 0}).sort("start_time", -1).skip(skip).limit(limit).to_list(limit)
    return [Transaction(**t) for t in transactions]

@api_router.delete("/transactions/{transaction_id}")
async def delete_transaction(
    transaction_id: str,
    current_user: User = Depends(require_role(UserRole.ADMIN))
):
    result = await db.transactions.delete_one({"id": transaction_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return {"message": "Transaction deleted successfully"}

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
    
    # Validate required columns
    required_columns = ['TxID', 'Station', 'Connector', 'Account', 'Start time', 'End Time', 'Meter value(kW.h)']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail=f"Missing required columns: {', '.join(missing_columns)}. Expected columns: {', '.join(required_columns)}"
        )
    
    errors = []
    imported = 0
    skipped = 0
    
    for idx, row in df.iterrows():
        row_num = idx + 2
        
        # Validate meter value
        try:
            meter_value = float(row['Meter value(kW.h)'])
        except (ValueError, TypeError):
            errors.append(ImportValidationError(
                row=row_num,
                field="Meter value(kW.h)",
                message="Invalid number format"
            ))
            continue
        
        # Skip 0 values
        if meter_value == 0:
            skipped += 1
            continue
        
        # Validate required fields
        if pd.isna(row['TxID']) or str(row['TxID']).strip() == '':
            errors.append(ImportValidationError(
                row=row_num,
                field="TxID",
                message="TxID is required"
            ))
            continue
        
        if pd.isna(row['Station']) or str(row['Station']).strip() == '':
            errors.append(ImportValidationError(
                row=row_num,
                field="Station",
                message="Station is required"
            ))
            continue
        
        # Check if transaction already exists
        existing = await db.transactions.find_one({"tx_id": str(row['TxID'])})
        if existing:
            skipped += 1
            continue
        
        # Get pricing and calculate cost
        account = str(row['Account']) if not pd.isna(row['Account']) else ""
        connector = str(row['Connector']) if not pd.isna(row['Connector']) else ""
        price_per_kwh = await get_pricing(account, connector)
        cost = meter_value * price_per_kwh
        
        # Create transaction
        transaction = {
            "id": str(uuid.uuid4()),
            "tx_id": str(row['TxID']),
            "station": str(row['Station']),
            "connector": connector,
            "account": account,
            "start_time": str(row['Start time']) if not pd.isna(row['Start time']) else "",
            "end_time": str(row['End Time']) if not pd.isna(row['End Time']) else "",
            "meter_value": meter_value,
            "cost": round(cost, 2),
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
    
    # Calculate total energy and revenue
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
    
    # Count unique stations
    stations = await db.transactions.distinct("station")
    active_stations = len(stations)
    
    # Count unique accounts
    accounts = await db.transactions.distinct("account")
    unique_accounts = len(accounts)
    
    # Get recent transactions
    recent = await db.transactions.find({}, {"_id": 0}).sort("start_time", -1).limit(5).to_list(5)
    recent_transactions = [Transaction(**t) for t in recent]
    
    return DashboardStats(
        total_transactions=total_transactions,
        total_energy=round(total_energy, 2),
        total_revenue=round(total_revenue, 2),
        active_stations=active_stations,
        unique_accounts=unique_accounts,
        recent_transactions=recent_transactions
    )

# User Management (Admin only)
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

# Get unique stations and accounts for filters
@api_router.get("/filters/stations")
async def get_stations(current_user: User = Depends(get_current_user)):
    stations = await db.transactions.distinct("station")
    return sorted([s for s in stations if s])

@api_router.get("/filters/accounts")
async def get_accounts(current_user: User = Depends(get_current_user)):
    accounts = await db.transactions.distinct("account")
    return sorted([a for a in accounts if a])

# Include router
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