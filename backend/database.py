"""
PostgreSQL Database Configuration and Models
"""
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, String, Float, Boolean, DateTime, Text, JSON, ForeignKey, Integer
from sqlalchemy.sql import func
from dotenv import load_dotenv
from pathlib import Path
import uuid

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql+asyncpg://postgres:postgres@localhost:5432/evcharging')

# Create async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Create async session factory
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Base class for models
class Base(DeclarativeBase):
    pass

def generate_uuid():
    return str(uuid.uuid4())

# ============== Models ==============

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, default="user")  # admin, user, viewer
    pricing_group_id = Column(String, ForeignKey("pricing_groups.id", ondelete="SET NULL"), nullable=True)
    # RFID fields - each user has one RFID card
    rfid_card_number = Column(String, unique=True, nullable=True, index=True)
    rfid_balance = Column(Float, default=0.0)
    rfid_status = Column(String, default="active")  # active, inactive, blocked
    # Vehicle registration (PLACA) - optional
    placa = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    tx_id = Column(String, index=True)
    station = Column(String, index=True)
    connector = Column(String)
    connector_type = Column(String)
    account = Column(String, index=True)
    start_time = Column(String)
    end_time = Column(String)
    meter_value = Column(Float, default=0)
    charging_duration = Column(String)
    cost = Column(Float, default=0)
    payment_status = Column(String, default="PENDING")  # PENDING, PAID
    payment_type = Column(String)
    payment_date = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Charger(Base):
    __tablename__ = "chargers"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    charger_id = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    location = Column(String)
    status = Column(String, default="Available")  # Available, Charging, Offline, Faulted
    connectors = Column(JSON, default=list)  # List of connector types
    last_heartbeat = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PricingRule(Base):
    __tablename__ = "pricing_rules"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    account = Column(String, index=True)
    connector = Column(String)
    connector_type = Column(String)
    price_per_kwh = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class PricingGroup(Base):
    __tablename__ = "pricing_groups"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, unique=True, nullable=False)
    description = Column(Text)
    connector_pricing = Column(JSON, default=dict)  # {"CCS2": 2500, "CHADEMO": 2000, "J1772": 1500}
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class RFIDCard(Base):
    __tablename__ = "rfid_cards"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    card_number = Column(String, unique=True, nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    balance = Column(Float, default=0)
    status = Column(String, default="active")  # active, inactive, blocked
    is_active = Column(Boolean, default=True)
    low_balance_threshold = Column(Float, default=10000)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class RFIDHistory(Base):
    __tablename__ = "rfid_history"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    card_id = Column(String, ForeignKey("rfid_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_type = Column(String)  # TOPUP, CHARGE, REFUND
    amount = Column(Float)
    balance_before = Column(Float)
    balance_after = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class OCPPSession(Base):
    __tablename__ = "ocpp_sessions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    charger_id = Column(String, ForeignKey("chargers.id"), nullable=False)
    connector_id = Column(Integer)
    rfid_card_id = Column(String, ForeignKey("rfid_cards.id"))
    transaction_id = Column(String)
    status = Column(String, default="Started")  # Started, Stopped
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True))
    meter_start = Column(Float, default=0)
    meter_stop = Column(Float)


class AppConfig(Base):
    __tablename__ = "app_config"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    config_type = Column(String, unique=True, nullable=False)  # payu, sendgrid, invoice_webhook
    config_data = Column(JSON, default=dict)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Settings(Base):
    """Settings table for PayU, SendGrid, etc."""
    __tablename__ = "settings"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    type = Column(String, unique=True, nullable=False)  # payu, sendgrid
    api_key = Column(String)
    api_login = Column(String)
    merchant_id = Column(String)
    account_id = Column(String)
    test_mode = Column(Boolean, default=True)
    sender_email = Column(String)
    sender_name = Column(String)
    enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PayUPayment(Base):
    """PayU payment records"""
    __tablename__ = "payu_payments"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    reference_code = Column(String, unique=True, nullable=False, index=True)
    rfid_card_id = Column(String)
    card_number = Column(String)
    user_id = Column(String)
    amount = Column(Float)
    buyer_name = Column(String)
    buyer_email = Column(String)
    buyer_phone = Column(String)
    status = Column(String, default="PENDING")
    payu_response = Column(JSON, default=dict)
    payu_transaction_id = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PayUWebhookLog(Base):
    """PayU webhook logs"""
    __tablename__ = "payu_webhook_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    reference_code = Column(String, index=True)
    webhook_data = Column(JSON, default=dict)
    received_at = Column(DateTime(timezone=True), server_default=func.now())


class OCPPBoot(Base):
    """OCPP boot notification records"""
    __tablename__ = "ocpp_boots"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    vendor = Column(String)
    model = Column(String)
    serial = Column(String)
    firmware = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String, default="Accepted")


class OCPPTransaction(Base):
    """OCPP transaction records"""
    __tablename__ = "ocpp_transactions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    transaction_id = Column(Integer, index=True)
    charger_id = Column(String, index=True)
    connector_id = Column(Integer)
    id_tag = Column(String)
    meter_start = Column(Integer)
    meter_stop = Column(Integer)
    start_timestamp = Column(String)
    stop_timestamp = Column(String)
    status = Column(String, default="active")  # active, completed
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class InvoiceWebhookConfig(Base):
    """Invoice webhook configuration"""
    __tablename__ = "invoice_webhook_config"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    webhook_url = Column(String)
    api_key = Column(String)
    enabled = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class InvoiceWebhookLog(Base):
    """Invoice webhook delivery logs"""
    __tablename__ = "invoice_webhook_logs"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    transaction_id = Column(String, index=True)
    status = Column(String)  # success, failed
    response_code = Column(Integer)
    response_body = Column(Text)
    error = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ============== Database Functions ==============

async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Get database session"""
    async with async_session() as session:
        yield session
