"""
Diagnose Login Issues
Run this script to check database and test login

Usage:
    cd C:\Apps\Smartcharge2026\backend
    .\venv\Scripts\activate
    python diagnose_login.py
"""

import asyncio
import bcrypt
import uuid
import requests
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get('DATABASE_URL', '')
DATABASE_TYPE = os.environ.get('DATABASE_TYPE', 'postgresql')

print("="*60)
print("SMARTCHARGE LOGIN DIAGNOSTICS")
print("="*60)

print(f"\n[1] Environment Check:")
print(f"    DATABASE_TYPE: {DATABASE_TYPE}")
print(f"    DATABASE_URL: {DATABASE_URL[:50]}..." if len(DATABASE_URL) > 50 else f"    DATABASE_URL: {DATABASE_URL}")

async def check_postgresql():
    try:
        import asyncpg
        PG_URL = DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://')
        
        print(f"\n[2] PostgreSQL Connection:")
        conn = await asyncpg.connect(PG_URL)
        print(f"    ✓ Connected successfully!")
        
        # Check if users table exists
        table_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'users'
            );
        """)
        print(f"    ✓ Users table exists: {table_exists}")
        
        if not table_exists:
            print("    ✗ ERROR: Users table does not exist!")
            print("    → Run: python create_admin.py")
            await conn.close()
            return False
        
        # Check for admin user
        print(f"\n[3] Admin User Check:")
        admin = await conn.fetchrow(
            "SELECT id, email, name, role, password_hash FROM users WHERE email = $1",
            "admin@evcharge.com"
        )
        
        if admin:
            print(f"    ✓ Admin user found!")
            print(f"      - ID: {admin['id']}")
            print(f"      - Email: {admin['email']}")
            print(f"      - Name: {admin['name']}")
            print(f"      - Role: {admin['role']}")
            print(f"      - Password hash exists: {bool(admin['password_hash'])}")
            
            # Test password
            print(f"\n[4] Password Verification:")
            test_password = "admin123"
            stored_hash = admin['password_hash']
            
            try:
                is_valid = bcrypt.checkpw(
                    test_password.encode('utf-8'),
                    stored_hash.encode('utf-8')
                )
                if is_valid:
                    print(f"    ✓ Password 'admin123' is CORRECT")
                else:
                    print(f"    ✗ Password 'admin123' is INCORRECT")
                    print(f"    → Will reset password now...")
                    
                    new_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    await conn.execute(
                        "UPDATE users SET password_hash = $1 WHERE email = $2",
                        new_hash, "admin@evcharge.com"
                    )
                    print(f"    ✓ Password reset to 'admin123'")
            except Exception as e:
                print(f"    ✗ Password check error: {e}")
                print(f"    → Resetting password...")
                new_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                await conn.execute(
                    "UPDATE users SET password_hash = $1 WHERE email = $2",
                    new_hash, "admin@evcharge.com"
                )
                print(f"    ✓ Password reset to 'admin123'")
        else:
            print(f"    ✗ Admin user NOT FOUND!")
            print(f"    → Creating admin user now...")
            
            password_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            await conn.execute("""
                INSERT INTO users (id, email, name, password_hash, role, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, 
                str(uuid.uuid4()),
                "admin@evcharge.com",
                "Admin User",
                password_hash,
                "admin",
                datetime.now(timezone.utc)
            )
            print(f"    ✓ Admin user created!")
        
        await conn.close()
        return True
        
    except ImportError:
        print("    ✗ asyncpg not installed. Run: pip install asyncpg")
        return False
    except Exception as e:
        print(f"    ✗ Database error: {e}")
        return False

def test_api_login():
    print(f"\n[5] API Login Test:")
    try:
        response = requests.post(
            "http://localhost:8001/api/auth/login",
            json={"email": "admin@evcharge.com", "password": "admin123"},
            timeout=10
        )
        
        print(f"    Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"    ✓ LOGIN SUCCESSFUL!")
            print(f"    Token: {data.get('access_token', '')[:50]}...")
            return True
        else:
            print(f"    ✗ LOGIN FAILED!")
            print(f"    Response: {response.text[:200]}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"    ✗ Cannot connect to backend at http://localhost:8001")
        print(f"    → Make sure backend is running")
        return False
    except Exception as e:
        print(f"    ✗ API error: {e}")
        return False

async def main():
    db_ok = await check_postgresql()
    
    if db_ok:
        test_api_login()
    
    print("\n" + "="*60)
    print("DIAGNOSIS COMPLETE")
    print("="*60)
    print("\nIf login still fails, check:")
    print("1. Backend is running (python -m uvicorn server:app --port 8001)")
    print("2. No firewall blocking port 8001")
    print("3. Browser console for JavaScript errors")
    print("4. Backend logs for Python errors")

if __name__ == "__main__":
    asyncio.run(main())
