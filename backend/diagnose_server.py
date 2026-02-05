"""
Step-by-step test of server.py imports
"""
import os
os.environ['DATABASE_TYPE'] = 'postgresql'

print("Testing server.py line by line...")
print()

print("1. FastAPI imports...")
from fastapi import FastAPI, APIRouter, HTTPException, Depends, UploadFile, File, status, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
print("   OK")

print("2. Starlette/CORS...")
from starlette.middleware.cors import CORSMiddleware
print("   OK")

print("3. Standard library...")
from dotenv import load_dotenv
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional, Dict
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from io import BytesIO
import logging
import hashlib
import uuid
print("   OK")

print("4. Loading .env...")
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')
print("   OK")

print("5. Checking DATABASE_TYPE...")
DATABASE_TYPE = os.environ.get('DATABASE_TYPE', 'mongodb')
print(f"   DATABASE_TYPE = {DATABASE_TYPE}")

print("6. Database imports (PostgreSQL path)...")
if DATABASE_TYPE == 'postgresql':
    from database import init_db
    from db_adapter import db
    print("   PostgreSQL imports OK")
else:
    print("   WARNING: Would use MongoDB path!")

print("7. Other libraries...")
import bcrypt
import jwt
print("   OK")

print("8. pandas...")
import pandas as pd
print("   OK")

print("9. openpyxl...")
import openpyxl
print("   OK")

print("10. reportlab...")
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import inch
print("    OK")

print("11. FastAPI responses...")
from fastapi.responses import StreamingResponse
print("    OK")

print("12. httpx...")
import httpx
print("    OK")

print()
print("="*50)
print("ALL MODULE-LEVEL IMPORTS SUCCESSFUL!")
print("="*50)
print()
print("Now testing FastAPI app creation with lifespan...")

security = HTTPBearer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("   Lifespan startup...")
    yield
    print("   Lifespan shutdown...")

app = FastAPI(lifespan=lifespan, title="Test Server")
api_router = APIRouter(prefix="/api")

@api_router.get("/health")
async def health():
    return {"status": "ok"}

app.include_router(api_router)

print("   App created!")
print()
print("="*50)
print("SUCCESS! Try running:")
print("python -m uvicorn diagnose_server:app --host 0.0.0.0 --port 8001")
print("="*50)
