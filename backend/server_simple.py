"""
Simple Backend Server for Smartcharge2026
This is a standalone server that works without complex imports
"""
print("Loading server modules...")

from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import bcrypt
import jwt
import asyncpg
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from dotenv import load_dotenv

print("Modules loaded successfully!")

# Load environment
load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/evcharging')
# Convert async URL to sync for asyncpg
PG_URL = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
JWT_SECRET = os.environ.get('JWT_SECRET', 'your-secret-key')
ALGORITHM = "HS256"

print(f"Database URL: {PG_URL[:50]}...")

# Database connection pool
db_pool = None

async def get_db_pool():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(PG_URL, min_size=1, max_size=10)
    return db_pool

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up...")
    # Initialize database pool
    pool = await get_db_pool()
    
    # Create tables if not exist
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR PRIMARY KEY,
                email VARCHAR UNIQUE NOT NULL,
                name VARCHAR NOT NULL,
                password_hash VARCHAR NOT NULL,
                role VARCHAR DEFAULT 'user',
                pricing_group_id VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id VARCHAR PRIMARY KEY,
                tx_id VARCHAR,
                station VARCHAR,
                connector VARCHAR,
                connector_type VARCHAR,
                account VARCHAR,
                start_time VARCHAR,
                end_time VARCHAR,
                meter_value FLOAT DEFAULT 0,
                charging_duration VARCHAR,
                cost FLOAT DEFAULT 0,
                payment_status VARCHAR DEFAULT 'PENDING',
                payment_type VARCHAR,
                payment_date VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chargers (
                id VARCHAR PRIMARY KEY,
                charger_id VARCHAR UNIQUE NOT NULL,
                name VARCHAR NOT NULL,
                location VARCHAR,
                status VARCHAR DEFAULT 'Available',
                connectors JSONB DEFAULT '[]',
                last_heartbeat TIMESTAMP WITH TIME ZONE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS pricing_groups (
                id VARCHAR PRIMARY KEY,
                name VARCHAR UNIQUE NOT NULL,
                description TEXT,
                connector_pricing JSONB DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE
            )
        """)
        
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS rfid_cards (
                id VARCHAR PRIMARY KEY,
                card_number VARCHAR UNIQUE NOT NULL,
                user_id VARCHAR NOT NULL,
                balance FLOAT DEFAULT 0,
                status VARCHAR DEFAULT 'active',
                low_balance_threshold FLOAT DEFAULT 10000,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            )
        """)
        
        # Check for admin user
        admin = await conn.fetchrow("SELECT * FROM users WHERE email = $1", "admin@evcharge.com")
        if not admin:
            password_hash = bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode()
            await conn.execute(
                "INSERT INTO users (id, email, name, password_hash, role) VALUES ($1, $2, $3, $4, $5)",
                str(uuid.uuid4()), "admin@evcharge.com", "Admin User", password_hash, "admin"
            )
            print("Default admin user created!")
    
    print("Application startup complete!")
    yield
    
    # Shutdown
    if db_pool:
        await db_pool.close()
    print("Shutdown complete!")

# Create FastAPI app
app = FastAPI(title="Smartcharge2026 API", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Router
api = APIRouter(prefix="/api")
security = HTTPBearer(auto_error=False)

# Models
class LoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    pricing_group_id: Optional[str] = None
    created_at: Optional[str] = None

class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

# Helper functions
def create_token(user_id: str, email: str, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=1)
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expire
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Routes
@api.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@api.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow(
            "SELECT * FROM users WHERE email = $1",
            request.email.lower()
        )
        
        if not user:
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        if not bcrypt.checkpw(request.password.encode(), user['password_hash'].encode()):
            raise HTTPException(status_code=401, detail="Invalid email or password")
        
        token = create_token(user['id'], user['email'], user['role'])
        
        return LoginResponse(
            access_token=token,
            user=UserResponse(
                id=user['id'],
                email=user['email'],
                name=user['name'],
                role=user['role'],
                pricing_group_id=user.get('pricing_group_id'),
                created_at=user['created_at'].isoformat() if user.get('created_at') else None
            )
        )

@api.get("/auth/me", response_model=UserResponse)
async def get_me(current_user: dict = Depends(get_current_user)):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        user = await conn.fetchrow("SELECT * FROM users WHERE id = $1", current_user['sub'])
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return UserResponse(
            id=user['id'],
            email=user['email'],
            name=user['name'],
            role=user['role'],
            pricing_group_id=user.get('pricing_group_id'),
            created_at=user['created_at'].isoformat() if user.get('created_at') else None
        )

@api.get("/users")
async def get_users(current_user: dict = Depends(get_current_user)):
    if current_user['role'] != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id, email, name, role, pricing_group_id, created_at FROM users")
        return [dict(row) for row in rows]

@api.get("/transactions")
async def get_transactions(current_user: dict = Depends(get_current_user)):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM transactions ORDER BY created_at DESC LIMIT 100")
        return [dict(row) for row in rows]

@api.get("/chargers")
async def get_chargers(current_user: dict = Depends(get_current_user)):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM chargers")
        return [dict(row) for row in rows]

@api.get("/pricing-groups")
async def get_pricing_groups(current_user: dict = Depends(get_current_user)):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM pricing_groups")
        return [dict(row) for row in rows]

@api.get("/rfid-cards")
async def get_rfid_cards(current_user: dict = Depends(get_current_user)):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT * FROM rfid_cards")
        return [dict(row) for row in rows]

@api.get("/dashboard/stats")
async def get_dashboard_stats(current_user: dict = Depends(get_current_user)):
    pool = await get_db_pool()
    async with pool.acquire() as conn:
        total_transactions = await conn.fetchval("SELECT COUNT(*) FROM transactions")
        total_revenue = await conn.fetchval("SELECT COALESCE(SUM(cost), 0) FROM transactions WHERE payment_status = 'PAID'")
        total_energy = await conn.fetchval("SELECT COALESCE(SUM(meter_value), 0) FROM transactions")
        total_chargers = await conn.fetchval("SELECT COUNT(*) FROM chargers")
        
        return {
            "total_transactions": total_transactions or 0,
            "total_revenue": float(total_revenue or 0),
            "total_energy": float(total_energy or 0),
            "total_chargers": total_chargers or 0,
            "currency": "COP"
        }

# Include router
app.include_router(api)

print("Server configured and ready!")

if __name__ == "__main__":
    import uvicorn
    print("Starting Uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
