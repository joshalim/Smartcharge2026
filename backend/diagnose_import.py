"""
Diagnostic script to find where server.py hangs during import
"""
import os
import sys

# Set DATABASE_TYPE before any imports
os.environ['DATABASE_TYPE'] = 'postgresql'

print("Step 1: Basic imports...")
from fastapi import FastAPI
print("  FastAPI OK")

from dotenv import load_dotenv
print("  dotenv OK")

print("\nStep 2: Loading .env...")
from pathlib import Path
load_dotenv(Path(__file__).parent / '.env')
print("  .env loaded")

print(f"\nStep 3: DATABASE_TYPE = {os.environ.get('DATABASE_TYPE', 'NOT SET')}")

print("\nStep 4: Importing database.py...")
try:
    from database import init_db, async_session
    print("  database.py OK")
except Exception as e:
    print(f"  database.py FAILED: {e}")
    sys.exit(1)

print("\nStep 5: Importing db_adapter.py...")
try:
    from db_adapter import db
    print("  db_adapter.py OK")
except Exception as e:
    print(f"  db_adapter.py FAILED: {e}")
    sys.exit(1)

print("\nStep 6: Other imports...")
import bcrypt
print("  bcrypt OK")
import jwt
print("  jwt OK")
import uuid
print("  uuid OK")

print("\nStep 7: Creating FastAPI app...")
app = FastAPI(title="Test")
print("  App created OK")

print("\n" + "="*50)
print("ALL IMPORTS SUCCESSFUL!")
print("="*50)
print("\nThe issue is likely in the lifespan/startup code.")
print("Try running: python -m uvicorn diagnose_import:app --host 0.0.0.0 --port 8001")
