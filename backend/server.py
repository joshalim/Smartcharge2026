"""
SmartCharge EV Charging Management System - Modular Server
"""
import os
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import bcrypt
import uuid

from database import engine, Base, async_session, User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# OCPP WebSocket server task
ocpp_server_task = None


# Startup/Shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    global ocpp_server_task
    
    logger.info("Starting SmartCharge server...")
    
    # Initialize database
    logger.info("Initializing PostgreSQL database...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ PostgreSQL initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise
    
    # Create admin user if not exists
    logger.info("Checking for admin user...")
    try:
        async with async_session() as session:
            from sqlalchemy import select
            result = await session.execute(
                select(User).where(User.email == "admin@evcharge.com")
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                password_hash = bcrypt.hashpw(
                    "admin123".encode('utf-8'), 
                    bcrypt.gensalt()
                ).decode('utf-8')
                
                admin = User(
                    id=str(uuid.uuid4()),
                    email="admin@evcharge.com",
                    name="Administrator",
                    password_hash=password_hash,
                    role="admin"
                )
                session.add(admin)
                await session.commit()
                logger.info("✓ Admin user created: admin@evcharge.com / admin123")
            else:
                logger.info(f"✓ Admin user exists: {admin.email}")
    except Exception as e:
        logger.error(f"Admin user check failed: {e}")
    
    # Start OCPP WebSocket server
    logger.info("Starting OCPP 1.6 WebSocket server...")
    try:
        from services.ocpp_server import start_ocpp_server
        ocpp_server = await start_ocpp_server(host="0.0.0.0", port=9000)
        logger.info("✓ OCPP WebSocket server running on ws://0.0.0.0:9000")
    except Exception as e:
        logger.error(f"Failed to start OCPP server: {e}")
    
    logger.info("✓ Server startup complete")
    yield
    
    # Shutdown
    logger.info("Server shutting down...")
    if ocpp_server_task:
        ocpp_server_task.cancel()


# Create FastAPI app
app = FastAPI(
    title="SmartCharge API",
    description="EV Charging Transaction Management System",
    version="2.0.0",
    lifespan=lifespan
)

# CORS - Allow all origins for file uploads
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Must be False when allow_origins is "*"
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Import and register routes
from routes.auth import router as auth_router
from routes.users import router as users_router
from routes.chargers import router as chargers_router
from routes.transactions import router as transactions_router
from routes.pricing import router as pricing_router
from routes.rfid import router as rfid_router
from routes.dashboard import router as dashboard_router
from routes.settings import router as settings_router
from routes.ocpp import router as ocpp_router
from routes.export import router as export_router
from routes.email import router as email_router
from routes.reports import router as reports_router
from routes.public_charge import router as public_charge_router
from routes.expenses import router as expenses_router

# Register all routers under /api prefix
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(chargers_router, prefix="/api")
app.include_router(transactions_router, prefix="/api")
app.include_router(pricing_router, prefix="/api")
app.include_router(rfid_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(settings_router, prefix="/api")
app.include_router(ocpp_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(email_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(public_charge_router, prefix="/api")
app.include_router(expenses_router, prefix="/api")


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "2.0.0"
    }


# Simple test endpoint for file upload debugging
@app.post("/api/test-upload")
async def test_upload(file: UploadFile = File(...)):
    """Test file upload without authentication"""
    from fastapi import UploadFile, File
    contents = await file.read()
    return {
        "filename": file.filename,
        "size": len(contents),
        "content_type": file.content_type
    }


# Filter endpoints (moved from dashboard for backwards compatibility)
@app.get("/api/filters/stations")
async def get_stations():
    """Get unique stations (backwards compatibility)"""
    from routes.dashboard import get_stations as dashboard_get_stations
    from routes.auth import get_current_user, security
    # This is a public endpoint for filters
    from sqlalchemy import select
    from database import Transaction
    
    async with async_session() as session:
        result = await session.execute(
            select(Transaction.station).distinct()
        )
        stations = [row[0] for row in result.fetchall() if row[0]]
        return sorted(stations)


@app.get("/api/filters/accounts")
async def get_accounts():
    """Get unique accounts (backwards compatibility)"""
    from sqlalchemy import select
    from database import Transaction
    
    async with async_session() as session:
        result = await session.execute(
            select(Transaction.account).distinct()
        )
        accounts = [row[0] for row in result.fetchall() if row[0]]
        return sorted(accounts)


# Admin setup endpoint for manual admin creation/reset
@app.post("/api/setup/admin")
async def setup_admin():
    """Create or reset admin user"""
    async with async_session() as session:
        from sqlalchemy import select
        result = await session.execute(
            select(User).where(User.email == "admin@evcharge.com")
        )
        admin = result.scalar_one_or_none()
        
        password_hash = bcrypt.hashpw(
            "admin123".encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')
        
        if admin:
            admin.password_hash = password_hash
            admin.name = "Administrator"
            admin.role = "admin"
            await session.commit()
            return {"message": "Admin password reset to: admin123"}
        else:
            admin = User(
                id=str(uuid.uuid4()),
                email="admin@evcharge.com",
                name="Administrator",
                password_hash=password_hash,
                role="admin"
            )
            session.add(admin)
            await session.commit()
            return {"message": "Admin user created: admin@evcharge.com / admin123"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
