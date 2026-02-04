@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   SmartCharge Backend Startup Script
echo ============================================
echo.

:: Set working directory
cd /d C:\Apps\Smartcharge2026\backend

:: Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then: venv\Scripts\activate ^&^& pip install -r requirements.txt
    pause
    exit /b 1
)

:: Activate virtual environment
echo [1/5] Activating virtual environment...
call venv\Scripts\activate.bat

:: Check if .env file exists
if not exist ".env" (
    echo [ERROR] .env file not found!
    echo Creating default .env file...
    (
        echo DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/evcharging
        echo DATABASE_TYPE=postgresql
        echo JWT_SECRET=your-secret-key-change-in-production
        echo CORS_ORIGINS=*
    ) > .env
    echo [WARNING] Please edit .env with your PostgreSQL password!
    pause
)

:: Check if DATABASE_TYPE is set to postgresql
findstr /C:"DATABASE_TYPE=postgresql" .env >nul 2>&1
if errorlevel 1 (
    echo [WARNING] DATABASE_TYPE=postgresql not found in .env
    echo Adding DATABASE_TYPE=postgresql to .env...
    echo DATABASE_TYPE=postgresql >> .env
    echo [OK] DATABASE_TYPE added
)

echo [2/5] Environment configuration:
echo      - Database: PostgreSQL
echo      - Server: server.py (full version)
echo.

:: Check if PostgreSQL is accessible
echo [3/5] Testing database connection...
python -c "import asyncio; import asyncpg; from dotenv import load_dotenv; import os; load_dotenv(); url=os.environ.get('DATABASE_URL','').replace('postgresql+asyncpg://','postgresql://'); asyncio.run(asyncpg.connect(url, timeout=5))" 2>nul
if errorlevel 1 (
    echo [WARNING] Could not connect to PostgreSQL database.
    echo Please check:
    echo   1. PostgreSQL service is running
    echo   2. DATABASE_URL in .env is correct
    echo   3. Database 'evcharging' exists
    echo.
    echo Continuing anyway...
) else (
    echo [OK] Database connection successful
)

echo.
echo [4/5] Creating/verifying admin user...
python -c "import asyncio; import bcrypt; import asyncpg; import uuid; from dotenv import load_dotenv; import os; load_dotenv(); url=os.environ.get('DATABASE_URL','').replace('postgresql+asyncpg://','postgresql://'); exec('''
async def setup():
    conn = await asyncpg.connect(url, timeout=5)
    admin = await conn.fetchrow(\"SELECT * FROM users WHERE email = $1\", \"admin@evcharge.com\")
    if not admin:
        pwd = bcrypt.hashpw(b\"admin123\", bcrypt.gensalt()).decode()
        await conn.execute(\"INSERT INTO users (id, email, name, password_hash, role) VALUES ($1, $2, $3, $4, $5)\", str(uuid.uuid4()), \"admin@evcharge.com\", \"Admin User\", pwd, \"admin\")
        print(\"[OK] Admin user created: admin@evcharge.com / admin123\")
    else:
        print(\"[OK] Admin user exists: \" + admin[\"email\"])
    await conn.close()
asyncio.run(setup())
''')" 2>nul
if errorlevel 1 (
    echo [WARNING] Could not verify admin user - will be created on server start
)

echo.
echo [5/5] Starting backend server...
echo ============================================
echo   Server: server.py
echo   Host:   0.0.0.0
echo   Port:   8001
echo ============================================
echo.
echo   Admin Login: admin@evcharge.com / admin123
echo.
echo Press Ctrl+C to stop the server
echo.

:: Start the FULL server (server.py), NOT server_simple.py
python -m uvicorn server:app --host 0.0.0.0 --port 8001

:: If we get here, server stopped
echo.
echo Server stopped.
pause
