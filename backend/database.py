"""Database configuration and connection"""
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Configuration
SECRET_KEY = os.environ.get('JWT_SECRET', 'your-secret-key-change-in-production')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

# PayU Colombia Configuration
PAYU_API_KEY = os.environ.get('PAYU_API_KEY', '4Vj8eK4rloUd272L48hsrarnUA')
PAYU_API_LOGIN = os.environ.get('PAYU_API_LOGIN', 'pRRXKOl8ikMmt9u')
PAYU_MERCHANT_ID = os.environ.get('PAYU_MERCHANT_ID', '508029')
PAYU_ACCOUNT_ID = os.environ.get('PAYU_ACCOUNT_ID', '512321')
PAYU_TEST_MODE = os.environ.get('PAYU_TEST_MODE', 'true').lower() == 'true'
PAYU_API_URL = 'https://sandbox.checkout.payulatam.com/ppp-web-gateway-payu/' if PAYU_TEST_MODE else 'https://checkout.payulatam.com/ppp-web-gateway-payu/'
FRONTEND_URL = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Default pricing
CONNECTOR_TYPE_PRICING = {
    "CCS2": 2500.0,
    "CHADEMO": 2000.0,
    "J1772": 1500.0
}

# Special accounts (legacy - now using pricing groups)
SPECIAL_ACCOUNTS = ["PORTERIA", "Jorge Iluminacion", "John Iluminacion"]
