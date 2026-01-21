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

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

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

async def get_pricing(account: str, connector: str, connector_type: Optional[str] = None) -> float:
    """Get price per kWh based on account and connector"""
    # Check if account is in special group
    if account in SPECIAL_ACCOUNTS:
        # Use connector type pricing
        if connector_type and connector_type in CONNECTOR_TYPE_PRICING:
            return CONNECTOR_TYPE_PRICING[connector_type]
        # Fallback to default if connector type not specified
        return 500.0
    
    # For other accounts, use custom pricing from database
    pricing = await db.pricing.find_one({"account": account, "connector": connector}, {"_id": 0})
    if pricing:
        return pricing['price_per_kwh']
    
    # Check for default pricing
    default_pricing = await db.pricing.find_one({"account": account, "connector": "default"}, {"_id": 0})
    if default_pricing:
        return default_pricing['price_per_kwh']
    
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
    
    required_columns = ['TxID', 'Station', 'Connector', 'Account', 'Start time', 'End Time', 'Meter value(kW.h)']
    missing_columns = [col for col in required_columns if col not in df.columns]
    
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
        
        start_time = str(row['Start time']) if not pd.isna(row['Start time']) else ""
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