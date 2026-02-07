"""
MongoDB Database Configuration and Models
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
from pathlib import Path
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'evcharging')

# Global client
client = None
db = None

async def init_db():
    """Initialize MongoDB connection"""
    global client, db
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]
    
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.users.create_index("rfid_card_number", unique=True, sparse=True)
    await db.chargers.create_index("charger_id", unique=True)
    await db.transactions.create_index("tx_id")
    await db.payu_payments.create_index("reference_code", unique=True)
    
    return db

async def get_db():
    """Get database instance"""
    global db
    if db is None:
        await init_db()
    return db

@asynccontextmanager
async def get_session():
    """Context manager for database session compatibility"""
    database = await get_db()
    yield database

# Alias for compatibility
async_session = get_session

def generate_uuid():
    return str(uuid.uuid4())

# ============== Model Classes (for type hints and serialization) ==============

class User:
    """User model"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id') or kwargs.get('_id') or generate_uuid()
        self.email = kwargs.get('email', '')
        self.name = kwargs.get('name', '')
        self.password_hash = kwargs.get('password_hash', '')
        self.role = kwargs.get('role', 'user')
        self.pricing_group_id = kwargs.get('pricing_group_id')
        self.rfid_card_number = kwargs.get('rfid_card_number')
        self.rfid_balance = kwargs.get('rfid_balance', 0.0)
        self.rfid_status = kwargs.get('rfid_status', 'active')
        self.placa = kwargs.get('placa')
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'password_hash': self.password_hash,
            'role': self.role,
            'pricing_group_id': self.pricing_group_id,
            'rfid_card_number': self.rfid_card_number,
            'rfid_balance': self.rfid_balance,
            'rfid_status': self.rfid_status,
            'placa': self.placa,
            'created_at': self.created_at
        }

class Transaction:
    """Transaction model"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id') or kwargs.get('_id') or generate_uuid()
        self.tx_id = kwargs.get('tx_id', '')
        self.station = kwargs.get('station', '')
        self.connector = kwargs.get('connector', '')
        self.connector_type = kwargs.get('connector_type', '')
        self.account = kwargs.get('account', '')
        self.start_time = kwargs.get('start_time', '')
        self.end_time = kwargs.get('end_time', '')
        self.meter_value = kwargs.get('meter_value', 0)
        self.charging_duration = kwargs.get('charging_duration', '')
        self.cost = kwargs.get('cost', 0)
        self.payment_status = kwargs.get('payment_status', 'PENDING')
        self.payment_type = kwargs.get('payment_type', '')
        self.payment_date = kwargs.get('payment_date', '')
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'tx_id': self.tx_id,
            'station': self.station,
            'connector': self.connector,
            'connector_type': self.connector_type,
            'account': self.account,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'meter_value': self.meter_value,
            'charging_duration': self.charging_duration,
            'cost': self.cost,
            'payment_status': self.payment_status,
            'payment_type': self.payment_type,
            'payment_date': self.payment_date,
            'created_at': self.created_at
        }

class Charger:
    """Charger model"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id') or kwargs.get('_id') or generate_uuid()
        self.charger_id = kwargs.get('charger_id', '')
        self.name = kwargs.get('name', '')
        self.location = kwargs.get('location', '')
        self.status = kwargs.get('status', 'Available')
        self.connectors = kwargs.get('connectors', [])
        self.last_heartbeat = kwargs.get('last_heartbeat')
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'charger_id': self.charger_id,
            'name': self.name,
            'location': self.location,
            'status': self.status,
            'connectors': self.connectors,
            'last_heartbeat': self.last_heartbeat,
            'created_at': self.created_at
        }

class Settings:
    """Settings model"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id') or kwargs.get('_id') or generate_uuid()
        self.type = kwargs.get('type', '')
        self.api_key = kwargs.get('api_key')
        self.api_login = kwargs.get('api_login')
        self.merchant_id = kwargs.get('merchant_id')
        self.account_id = kwargs.get('account_id')
        self.test_mode = kwargs.get('test_mode', True)
        self.sender_email = kwargs.get('sender_email')
        self.sender_name = kwargs.get('sender_name')
        self.enabled = kwargs.get('enabled', True)
        self.updated_at = kwargs.get('updated_at')
    
    def to_dict(self):
        return {
            'id': self.id,
            'type': self.type,
            'api_key': self.api_key,
            'api_login': self.api_login,
            'merchant_id': self.merchant_id,
            'account_id': self.account_id,
            'test_mode': self.test_mode,
            'sender_email': self.sender_email,
            'sender_name': self.sender_name,
            'enabled': self.enabled,
            'updated_at': self.updated_at
        }

class PayUPayment:
    """PayU payment record"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id') or kwargs.get('_id') or generate_uuid()
        self.reference_code = kwargs.get('reference_code', '')
        self.rfid_card_id = kwargs.get('rfid_card_id')
        self.card_number = kwargs.get('card_number')
        self.user_id = kwargs.get('user_id')
        self.amount = kwargs.get('amount', 0)
        self.buyer_name = kwargs.get('buyer_name')
        self.buyer_email = kwargs.get('buyer_email')
        self.buyer_phone = kwargs.get('buyer_phone')
        self.status = kwargs.get('status', 'PENDING')
        self.payu_response = kwargs.get('payu_response', {})
        self.payu_transaction_id = kwargs.get('payu_transaction_id')
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        self.updated_at = kwargs.get('updated_at')
    
    def to_dict(self):
        return {
            'id': self.id,
            'reference_code': self.reference_code,
            'rfid_card_id': self.rfid_card_id,
            'card_number': self.card_number,
            'user_id': self.user_id,
            'amount': self.amount,
            'buyer_name': self.buyer_name,
            'buyer_email': self.buyer_email,
            'buyer_phone': self.buyer_phone,
            'status': self.status,
            'payu_response': self.payu_response,
            'payu_transaction_id': self.payu_transaction_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class PayUWebhookLog:
    """PayU webhook log"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id') or kwargs.get('_id') or generate_uuid()
        self.reference_code = kwargs.get('reference_code')
        self.webhook_data = kwargs.get('webhook_data', {})
        self.received_at = kwargs.get('received_at', datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'reference_code': self.reference_code,
            'webhook_data': self.webhook_data,
            'received_at': self.received_at
        }

class PricingRule:
    """Pricing rule model"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id') or kwargs.get('_id') or generate_uuid()
        self.account = kwargs.get('account', '')
        self.connector = kwargs.get('connector', '')
        self.connector_type = kwargs.get('connector_type', '')
        self.price_per_kwh = kwargs.get('price_per_kwh', 0)
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'account': self.account,
            'connector': self.connector,
            'connector_type': self.connector_type,
            'price_per_kwh': self.price_per_kwh,
            'created_at': self.created_at
        }

class PricingGroup:
    """Pricing group model"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id') or kwargs.get('_id') or generate_uuid()
        self.name = kwargs.get('name', '')
        self.description = kwargs.get('description', '')
        self.connector_pricing = kwargs.get('connector_pricing', {})
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
        self.updated_at = kwargs.get('updated_at')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'connector_pricing': self.connector_pricing,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }

class RFIDCard:
    """RFID card model"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id') or kwargs.get('_id') or generate_uuid()
        self.card_number = kwargs.get('card_number', '')
        self.user_id = kwargs.get('user_id')
        self.balance = kwargs.get('balance', 0)
        self.status = kwargs.get('status', 'active')
        self.is_active = kwargs.get('is_active', True)
        self.low_balance_threshold = kwargs.get('low_balance_threshold', 10000)
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'card_number': self.card_number,
            'user_id': self.user_id,
            'balance': self.balance,
            'status': self.status,
            'is_active': self.is_active,
            'low_balance_threshold': self.low_balance_threshold,
            'created_at': self.created_at
        }

class RFIDHistory:
    """RFID history model"""
    def __init__(self, **kwargs):
        self.id = kwargs.get('id') or kwargs.get('_id') or generate_uuid()
        self.card_id = kwargs.get('card_id', '')
        self.transaction_type = kwargs.get('transaction_type', '')
        self.amount = kwargs.get('amount', 0)
        self.balance_before = kwargs.get('balance_before', 0)
        self.balance_after = kwargs.get('balance_after', 0)
        self.notes = kwargs.get('notes', '')
        self.created_at = kwargs.get('created_at', datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'card_id': self.card_id,
            'transaction_type': self.transaction_type,
            'amount': self.amount,
            'balance_before': self.balance_before,
            'balance_after': self.balance_after,
            'notes': self.notes,
            'created_at': self.created_at
        }

# Placeholder for SQLAlchemy compatibility
engine = None
Base = None
