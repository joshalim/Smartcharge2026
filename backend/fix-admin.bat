@echo off
echo ============================================
echo   SmartCharge - Fix Admin Login
echo ============================================
echo.

cd /d C:\Apps\Smartcharge2026\backend
call venv\Scripts\activate.bat

echo Creating/resetting admin user...
echo.

python -c "import asyncio; import bcrypt; import asyncpg; import uuid; from dotenv import load_dotenv; import os; load_dotenv(); url=os.environ.get('DATABASE_URL','').replace('postgresql+asyncpg://','postgresql://'); exec('''
async def fix_admin():
    try:
        conn = await asyncpg.connect(url, timeout=10)
        print(\"Connected to database.\")
        
        # Check if users table exists
        table = await conn.fetchval(\"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')\")
        if not table:
            print(\"Creating users table...\")
            await conn.execute(\"\"\"
                CREATE TABLE IF NOT EXISTS users (
                    id VARCHAR PRIMARY KEY,
                    email VARCHAR UNIQUE NOT NULL,
                    name VARCHAR NOT NULL,
                    password_hash VARCHAR NOT NULL,
                    role VARCHAR DEFAULT 'user',
                    pricing_group_id VARCHAR,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            \"\"\")
        
        # Create or reset admin
        pwd = bcrypt.hashpw(b\"admin123\", bcrypt.gensalt()).decode()
        admin = await conn.fetchrow(\"SELECT * FROM users WHERE email = $1\", \"admin@evcharge.com\")
        
        if admin:
            await conn.execute(\"UPDATE users SET password_hash = $1 WHERE email = $2\", pwd, \"admin@evcharge.com\")
            print(\"Admin password RESET to: admin123\")
        else:
            await conn.execute(\"INSERT INTO users (id, email, name, password_hash, role) VALUES ($1, $2, $3, $4, $5)\", 
                str(uuid.uuid4()), \"admin@evcharge.com\", \"Admin User\", pwd, \"admin\")
            print(\"Admin user CREATED.\")
        
        await conn.close()
        print(\"\")
        print(\"============================================\")
        print(\"  Login Credentials:\")
        print(\"  Email:    admin@evcharge.com\")
        print(\"  Password: admin123\")
        print(\"============================================\")
    except Exception as e:
        print(f\"ERROR: {e}\")
        print(\"\")
        print(\"Check that:\")
        print(\"  1. PostgreSQL is running\")
        print(\"  2. DATABASE_URL in .env is correct\")
        print(\"  3. Database 'evcharging' exists\")

asyncio.run(fix_admin())
''')"

echo.
pause
