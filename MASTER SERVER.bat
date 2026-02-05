@echo off
setlocal enabledelayedexpansion

title SmartCharge Master Server
color 0A

echo.
echo  ============================================================
echo  #                                                          #
echo  #              SMARTCHARGE MASTER SERVER                   #
echo  #                                                          #
echo  ============================================================
echo.

:: Set paths
set APP_DIR=C:\Apps\Smartcharge2026
set BACKEND_DIR=%APP_DIR%\backend
set FRONTEND_DIR=%APP_DIR%\frontend
set LOG_DIR=%APP_DIR%\logs

:: Create logs directory
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

:: Change to app directory
cd /d %APP_DIR%

echo  [STEP 1/6] Checking environment...
echo  --------------------------------------------------------

:: Check backend directory
if not exist "%BACKEND_DIR%" (
    echo  [ERROR] Backend directory not found: %BACKEND_DIR%
    goto :error
)

:: Check frontend directory  
if not exist "%FRONTEND_DIR%" (
    echo  [ERROR] Frontend directory not found: %FRONTEND_DIR%
    goto :error
)

:: Check Python venv
if not exist "%BACKEND_DIR%\venv\Scripts\python.exe" (
    echo  [ERROR] Python virtual environment not found!
    echo  Please run: cd %BACKEND_DIR% ^&^& python -m venv venv
    goto :error
)

echo  [OK] Directories verified

echo.
echo  [STEP 2/6] Setting up environment variables...
echo  --------------------------------------------------------

:: Create/update backend .env if needed
cd /d %BACKEND_DIR%

:: Check if .env exists, create if not
if not exist ".env" (
    echo  [INFO] Creating backend .env file...
    (
        echo DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/evcharging
        echo DATABASE_TYPE=postgresql
        echo JWT_SECRET=smartcharge-secret-key-2026
        echo CORS_ORIGINS=*
    ) > .env
    echo  [WARNING] Created default .env - edit DATABASE_URL with your password!
)

:: Ensure DATABASE_TYPE=postgresql is set
findstr /C:"DATABASE_TYPE=postgresql" .env >nul 2>&1
if errorlevel 1 (
    echo DATABASE_TYPE=postgresql >> .env
    echo  [OK] Added DATABASE_TYPE=postgresql
)

echo  [OK] Environment configured

echo.
echo  [STEP 3/6] Testing database connection...
echo  --------------------------------------------------------

call "%BACKEND_DIR%\venv\Scripts\activate.bat"

python -c "import asyncio, asyncpg, os; from dotenv import load_dotenv; load_dotenv(); url=os.environ.get('DATABASE_URL','').replace('postgresql+asyncpg://','postgresql://'); asyncio.run(asyncpg.connect(url,timeout=5)); print('  [OK] PostgreSQL connection successful')" 2>nul
if errorlevel 1 (
    echo  [ERROR] Cannot connect to PostgreSQL!
    echo.
    echo  Please verify:
    echo    1. PostgreSQL service is running (services.msc)
    echo    2. Database 'evcharging' exists
    echo    3. PASSWORD in DATABASE_URL is correct
    echo.
    echo  Current DATABASE_URL in .env:
    findstr "DATABASE_URL" .env
    echo.
    pause
    goto :error
)

echo.
echo  [STEP 4/6] Creating admin user...
echo  --------------------------------------------------------

python -c "import asyncio,bcrypt,asyncpg,uuid,os;from dotenv import load_dotenv;load_dotenv();url=os.environ.get('DATABASE_URL','').replace('postgresql+asyncpg://','postgresql://');exec('''
async def setup():
    conn=await asyncpg.connect(url,timeout=10)
    await conn.execute(\"\"\"CREATE TABLE IF NOT EXISTS users(id VARCHAR PRIMARY KEY,email VARCHAR UNIQUE NOT NULL,name VARCHAR NOT NULL,password_hash VARCHAR NOT NULL,role VARCHAR DEFAULT 'user',pricing_group_id VARCHAR,created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW())\"\"\")
    await conn.execute(\"\"\"CREATE TABLE IF NOT EXISTS transactions(id VARCHAR PRIMARY KEY,tx_id VARCHAR,station VARCHAR,connector VARCHAR,connector_type VARCHAR,account VARCHAR,start_time VARCHAR,end_time VARCHAR,meter_value FLOAT DEFAULT 0,charging_duration VARCHAR,cost FLOAT DEFAULT 0,payment_status VARCHAR DEFAULT 'PENDING',payment_type VARCHAR,payment_date VARCHAR,created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW())\"\"\")
    await conn.execute(\"\"\"CREATE TABLE IF NOT EXISTS chargers(id VARCHAR PRIMARY KEY,charger_id VARCHAR UNIQUE NOT NULL,name VARCHAR NOT NULL,location VARCHAR,status VARCHAR DEFAULT 'Available',connectors JSONB DEFAULT '[]',last_heartbeat TIMESTAMP WITH TIME ZONE,created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW())\"\"\")
    await conn.execute(\"\"\"CREATE TABLE IF NOT EXISTS pricing_rules(id VARCHAR PRIMARY KEY,account VARCHAR,connector VARCHAR,connector_type VARCHAR,price_per_kwh FLOAT NOT NULL,created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW())\"\"\")
    await conn.execute(\"\"\"CREATE TABLE IF NOT EXISTS pricing_groups(id VARCHAR PRIMARY KEY,name VARCHAR UNIQUE NOT NULL,description TEXT,connector_pricing JSONB DEFAULT '{}',created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),updated_at TIMESTAMP WITH TIME ZONE)\"\"\")
    await conn.execute(\"\"\"CREATE TABLE IF NOT EXISTS rfid_cards(id VARCHAR PRIMARY KEY,card_number VARCHAR UNIQUE NOT NULL,user_id VARCHAR NOT NULL,balance FLOAT DEFAULT 0,status VARCHAR DEFAULT 'active',low_balance_threshold FLOAT DEFAULT 10000,created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW())\"\"\")
    await conn.execute(\"\"\"CREATE TABLE IF NOT EXISTS rfid_history(id VARCHAR PRIMARY KEY,card_id VARCHAR NOT NULL,timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),type VARCHAR,amount FLOAT,description TEXT,balance_before FLOAT,balance_after FLOAT)\"\"\")
    await conn.execute(\"\"\"CREATE TABLE IF NOT EXISTS app_config(id VARCHAR PRIMARY KEY,config_type VARCHAR UNIQUE NOT NULL,config_data JSONB DEFAULT '{}',updated_at TIMESTAMP WITH TIME ZONE)\"\"\")
    pwd=bcrypt.hashpw(b'admin123',bcrypt.gensalt()).decode()
    admin=await conn.fetchrow('SELECT * FROM users WHERE email=$1','admin@evcharge.com')
    if admin:
        await conn.execute('UPDATE users SET password_hash=$1 WHERE email=$2',pwd,'admin@evcharge.com')
        print('  [OK] Admin password reset to: admin123')
    else:
        await conn.execute('INSERT INTO users(id,email,name,password_hash,role)VALUES($1,$2,$3,$4,$5)',str(uuid.uuid4()),'admin@evcharge.com','Admin User',pwd,'admin')
        print('  [OK] Admin user created')
    await conn.close()
asyncio.run(setup())
''')"

if errorlevel 1 (
    echo  [WARNING] Could not setup admin user automatically
)

echo.
echo  [STEP 5/6] Starting Backend Server...
echo  --------------------------------------------------------
echo  Server: server.py (PostgreSQL mode)
echo  Port:   8001
echo.

:: Start backend in a new window
start "SmartCharge Backend" cmd /k "cd /d %BACKEND_DIR% && call venv\Scripts\activate.bat && set DATABASE_TYPE=postgresql && python -m uvicorn server:app --host 0.0.0.0 --port 8001"

:: Wait for backend to start
echo  Waiting for backend to start...
timeout /t 5 /nobreak >nul

:: Verify backend is running
curl -s http://localhost:8001/api/health >nul 2>&1
if errorlevel 1 (
    echo  [WARNING] Backend may not have started correctly
    echo  Check the Backend window for errors
) else (
    echo  [OK] Backend is running on port 8001
)

echo.
echo  [STEP 6/6] Starting Frontend Server...
echo  --------------------------------------------------------
echo  Port: 3000
echo.

:: Check if serve is installed
where serve >nul 2>&1
if errorlevel 1 (
    echo  [INFO] Installing 'serve' package...
    call npm install -g serve
)

:: Check if frontend build exists
if not exist "%FRONTEND_DIR%\build" (
    echo  [WARNING] Frontend build not found!
    echo  Building frontend...
    cd /d %FRONTEND_DIR%
    call yarn build
)

:: Start frontend in a new window
start "SmartCharge Frontend" cmd /k "cd /d %FRONTEND_DIR% && npx serve -s build -l 3000"

:: Wait for frontend
timeout /t 3 /nobreak >nul

echo  [OK] Frontend is running on port 3000

echo.
echo  ============================================================
echo  #                                                          #
echo  #              SMARTCHARGE SERVER STARTED                  #
echo  #                                                          #
echo  ============================================================
echo.
echo    Backend:  http://localhost:8001
echo    Frontend: http://localhost:3000
echo.
echo    Login Credentials:
echo    ------------------
echo    Email:    admin@evcharge.com
echo    Password: admin123
echo.
echo  ============================================================
echo.
echo  Two server windows should now be open:
echo    - "SmartCharge Backend"  (Python/Uvicorn)
echo    - "SmartCharge Frontend" (Node/Serve)
echo.
echo  To stop servers, close those windows or press Ctrl+C in them.
echo.
echo  Press any key to open the application in your browser...
pause >nul

:: Open browser
start http://localhost:3000

goto :end

:error
echo.
echo  ============================================================
echo  [ERROR] Server startup failed! See messages above.
echo  ============================================================
pause
exit /b 1

:end
echo.
echo  Master Server script completed.
echo  Keep this window open to monitor status.
echo.
pause
