"""
FULL DIAGNOSTIC SCRIPT for SmartCharge EV Charging System
Run this script to diagnose ALL issues with the application

Usage:
    cd C:\Apps\Smartcharge2026\backend
    .\venv\Scripts\activate
    python diagnose_full.py
"""

import os
import sys
import asyncio
from pathlib import Path

print("=" * 70)
print("SMARTCHARGE FULL SYSTEM DIAGNOSTIC")
print("=" * 70)

# Step 1: Check Python Environment
print("\n[1] PYTHON ENVIRONMENT")
print(f"    Python Version: {sys.version}")
print(f"    Python Path: {sys.executable}")
print(f"    Working Directory: {os.getcwd()}")

# Step 2: Check .env file
print("\n[2] ENVIRONMENT FILE CHECK")
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    print(f"    ✓ .env file found at: {env_path}")
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    has_database_url = False
    has_database_type = False
    has_jwt_secret = False
    
    for line in lines:
        line = line.strip()
        if line.startswith('#') or not line:
            continue
        if 'DATABASE_URL' in line and not 'DATABASE_TYPE' in line:
            has_database_url = True
            # Mask password
            if '@' in line:
                parts = line.split('@')
                masked = parts[0].rsplit(':', 1)[0] + ':****@' + parts[1]
                print(f"    DATABASE_URL: {masked}")
            else:
                print(f"    DATABASE_URL: {line}")
        if 'DATABASE_TYPE' in line:
            has_database_type = True
            print(f"    {line}")
        if 'JWT_SECRET' in line:
            has_jwt_secret = True
            print(f"    JWT_SECRET: ****")
    
    if not has_database_type:
        print("    ✗ WARNING: DATABASE_TYPE not set!")
        print("    → Add this line to your .env file:")
        print("      DATABASE_TYPE=postgresql")
    
    if not has_database_url:
        print("    ✗ WARNING: DATABASE_URL not set!")
    
    if not has_jwt_secret:
        print("    ⚠ WARNING: JWT_SECRET not set (using default)")
else:
    print(f"    ✗ ERROR: .env file NOT FOUND at {env_path}")
    print("    → Create backend\\.env with:")
    print("      DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/evcharging")
    print("      DATABASE_TYPE=postgresql")
    print("      JWT_SECRET=your-secret-key")
    sys.exit(1)

# Load environment
from dotenv import load_dotenv
load_dotenv(env_path)

DATABASE_URL = os.environ.get('DATABASE_URL', '')
DATABASE_TYPE = os.environ.get('DATABASE_TYPE', 'mongodb')

print(f"\n[3] DATABASE CONFIGURATION")
print(f"    DATABASE_TYPE: {DATABASE_TYPE}")

if DATABASE_TYPE != 'postgresql':
    print("    ✗ CRITICAL: DATABASE_TYPE should be 'postgresql'")
    print("    → Edit your .env file and add: DATABASE_TYPE=postgresql")
    print("    → Then restart the backend service")

# Step 3: Check Required Packages
print("\n[4] PYTHON PACKAGES")
packages_ok = True

try:
    import bcrypt
    print(f"    ✓ bcrypt: OK")
except ImportError:
    print(f"    ✗ bcrypt: MISSING - run: pip install bcrypt")
    packages_ok = False

try:
    import jwt
    print(f"    ✓ pyjwt: OK")
except ImportError:
    print(f"    ✗ pyjwt: MISSING - run: pip install pyjwt")
    packages_ok = False

try:
    import asyncpg
    print(f"    ✓ asyncpg: OK")
except ImportError:
    print(f"    ✗ asyncpg: MISSING - run: pip install asyncpg")
    packages_ok = False

try:
    from sqlalchemy.ext.asyncio import create_async_engine
    print(f"    ✓ sqlalchemy: OK")
except ImportError:
    print(f"    ✗ sqlalchemy: MISSING - run: pip install sqlalchemy[asyncio]")
    packages_ok = False

try:
    from fastapi import FastAPI
    print(f"    ✓ fastapi: OK")
except ImportError:
    print(f"    ✗ fastapi: MISSING - run: pip install fastapi")
    packages_ok = False

if not packages_ok:
    print("\n    → Run: pip install -r requirements.txt")

# Step 4: Test Database Connection
print("\n[5] DATABASE CONNECTION TEST")

async def test_database():
    try:
        import asyncpg
        
        # Convert SQLAlchemy URL to asyncpg format
        pg_url = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
        
        print(f"    Connecting to PostgreSQL...")
        conn = await asyncpg.connect(pg_url, timeout=10)
        print(f"    ✓ Connected successfully!")
        
        # Check tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        table_names = [t['table_name'] for t in tables]
        print(f"    Tables found: {len(table_names)}")
        
        required_tables = ['users', 'transactions', 'chargers', 'pricing_groups', 'rfid_cards']
        for table in required_tables:
            if table in table_names:
                print(f"      ✓ {table}")
            else:
                print(f"      ✗ {table} - MISSING")
        
        # Check admin user
        print(f"\n[6] ADMIN USER CHECK")
        admin = await conn.fetchrow(
            "SELECT id, email, name, role, password_hash FROM users WHERE email = $1",
            "admin@evcharge.com"
        )
        
        if admin:
            print(f"    ✓ Admin user found!")
            print(f"      Email: {admin['email']}")
            print(f"      Name: {admin['name']}")
            print(f"      Role: {admin['role']}")
            
            # Verify password
            print(f"\n[7] PASSWORD VERIFICATION")
            try:
                is_valid = bcrypt.checkpw(
                    "admin123".encode('utf-8'),
                    admin['password_hash'].encode('utf-8')
                )
                if is_valid:
                    print(f"    ✓ Password 'admin123' is CORRECT")
                else:
                    print(f"    ✗ Password 'admin123' is INCORRECT")
                    await reset_password(conn)
            except Exception as e:
                print(f"    ✗ Password check error: {e}")
                await reset_password(conn)
        else:
            print(f"    ✗ Admin user NOT FOUND")
            print(f"    → Creating admin user...")
            await create_admin_user(conn)
        
        await conn.close()
        return True
        
    except asyncpg.exceptions.InvalidPasswordError:
        print(f"    ✗ ERROR: Invalid database password!")
        print(f"    → Check DATABASE_URL in your .env file")
        return False
    except asyncpg.exceptions.InvalidCatalogNameError:
        print(f"    ✗ ERROR: Database 'evcharging' does not exist!")
        print(f"    → Run in psql: CREATE DATABASE evcharging;")
        return False
    except asyncpg.exceptions.ConnectionRefusedError:
        print(f"    ✗ ERROR: Cannot connect to PostgreSQL!")
        print(f"    → Is PostgreSQL service running?")
        print(f"    → Check: services.msc -> postgresql-x64-16")
        return False
    except Exception as e:
        print(f"    ✗ ERROR: {type(e).__name__}: {e}")
        return False

async def reset_password(conn):
    print(f"    → Resetting password to 'admin123'...")
    new_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    await conn.execute(
        "UPDATE users SET password_hash = $1 WHERE email = $2",
        new_hash, "admin@evcharge.com"
    )
    print(f"    ✓ Password reset successfully!")

async def create_admin_user(conn):
    import uuid
    password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # First check if table exists
    table_exists = await conn.fetchval("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'users'
        );
    """)
    
    if not table_exists:
        print(f"    → Creating users table first...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR PRIMARY KEY,
                email VARCHAR UNIQUE NOT NULL,
                name VARCHAR NOT NULL,
                password_hash VARCHAR NOT NULL,
                role VARCHAR DEFAULT 'user',
                pricing_group_id VARCHAR,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
        """)
    
    await conn.execute("""
        INSERT INTO users (id, email, name, password_hash, role)
        VALUES ($1, $2, $3, $4, $5)
        ON CONFLICT (email) DO UPDATE SET password_hash = EXCLUDED.password_hash
    """, 
        str(uuid.uuid4()),
        "admin@evcharge.com",
        "Admin User",
        password_hash,
        "admin"
    )
    print(f"    ✓ Admin user created!")

# Step 5: Test API (if backend is running)
def test_api():
    print(f"\n[8] API CONNECTION TEST")
    try:
        import requests
        
        # Test health endpoint
        try:
            response = requests.get("http://localhost:8001/api/health", timeout=5)
            if response.status_code == 200:
                print(f"    ✓ Backend is running on port 8001")
            else:
                print(f"    ⚠ Backend returned: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print(f"    ⚠ Backend not running on localhost:8001")
            print(f"    → This is OK if you're just testing database")
            return False
        
        # Test login
        print(f"\n[9] LOGIN API TEST")
        response = requests.post(
            "http://localhost:8001/api/auth/login",
            json={"email": "admin@evcharge.com", "password": "admin123"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"    ✓ LOGIN SUCCESSFUL!")
            print(f"    Token: {data.get('access_token', '')[:50]}...")
            return True
        else:
            print(f"    ✗ LOGIN FAILED! Status: {response.status_code}")
            print(f"    Response: {response.text[:200]}")
            return False
            
    except ImportError:
        print(f"    ⚠ 'requests' package not installed")
        print(f"    → pip install requests")
        return False
    except Exception as e:
        print(f"    ✗ API Error: {e}")
        return False

# Run all checks
async def main():
    db_ok = await test_database()
    
    if db_ok:
        test_api()
    
    print("\n" + "=" * 70)
    print("DIAGNOSTIC COMPLETE")
    print("=" * 70)
    
    print("\n📋 QUICK FIX CHECKLIST:")
    print("   1. Ensure .env has: DATABASE_TYPE=postgresql")
    print("   2. Ensure PostgreSQL service is running")
    print("   3. Run: python create_admin.py")
    print("   4. Restart backend: net stop EVChargingBackend && net start EVChargingBackend")
    print("   5. Try login at: http://localhost:3000")
    print("\n📧 Default Credentials:")
    print("   Email: admin@evcharge.com")
    print("   Password: admin123")

if __name__ == "__main__":
    asyncio.run(main())
