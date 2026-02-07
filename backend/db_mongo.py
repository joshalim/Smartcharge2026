"""
MongoDB Database Configuration for EV Charging System
"""
import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import ASCENDING, DESCENDING
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB configuration
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'evcharging')

# Create client
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Collections
users_collection = db['users']
transactions_collection = db['transactions']
chargers_collection = db['chargers']
pricing_rules_collection = db['pricing_rules']
pricing_groups_collection = db['pricing_groups']
rfid_cards_collection = db['rfid_cards']
rfid_history_collection = db['rfid_history']
settings_collection = db['settings']
email_templates_collection = db['email_templates']
ocpp_boots_collection = db['ocpp_boots']
ocpp_transactions_collection = db['ocpp_transactions']
ocpp_sessions_collection = db['ocpp_sessions']
payu_payments_collection = db['payu_payments']
payu_webhook_logs_collection = db['payu_webhook_logs']
invoice_webhook_config_collection = db['invoice_webhook_config']
invoice_webhook_logs_collection = db['invoice_webhook_logs']


async def init_db():
    """Initialize database indexes"""
    # Users
    await users_collection.create_index('email', unique=True)
    
    # Transactions
    await transactions_collection.create_index('tx_id')
    await transactions_collection.create_index('station')
    await transactions_collection.create_index('account')
    await transactions_collection.create_index([('start_time', DESCENDING)])
    
    # Chargers
    await chargers_collection.create_index('charger_id', unique=True)
    
    # Pricing
    await pricing_rules_collection.create_index('account')
    await pricing_groups_collection.create_index('name', unique=True)
    
    # RFID
    await rfid_cards_collection.create_index('card_number', unique=True)
    await rfid_cards_collection.create_index('user_id')
    await rfid_history_collection.create_index('card_id')
    
    # Settings
    await settings_collection.create_index('type', unique=True)
    
    # Email templates
    await email_templates_collection.create_index('name', unique=True)
    
    # OCPP
    await ocpp_transactions_collection.create_index('transaction_id')
    await ocpp_transactions_collection.create_index('charger_id')
    
    # PayU
    await payu_payments_collection.create_index('reference_code', unique=True)
    await payu_webhook_logs_collection.create_index('reference_code')
    
    print("✓ MongoDB indexes initialized")


async def close_db():
    """Close database connection"""
    client.close()
