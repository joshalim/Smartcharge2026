@echo off
REM ============================================
REM EV Charging Management System
REM Windows Server 2016 Installation Script
REM ============================================

setlocal enabledelayedexpansion

echo.
echo ============================================
echo    EV Charging Management System Installer
echo    Windows Server 2016
echo ============================================
echo.

REM Check for Administrator privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: This script must be run as Administrator
    echo Right-click and select "Run as administrator"
    pause
    exit /b 1
)

REM Configuration
set APP_DIR=C:\Apps\ev-charging-management
set PYTHON_PATH=C:\Python314
set NODE_PATH=C:\Program Files\nodejs
set PG_PATH=C:\Program Files\PostgreSQL\16
set NSSM_PATH=C:\nssm\win64

echo [1/8] Checking prerequisites...

REM Check Node.js
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js not found. Please install Node.js v25.5.0 first.
    echo Download from: https://nodejs.org/dist/v25.5.0/node-v25.5.0-x64.msi
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('node --version') do set NODE_VER=%%i
echo    Node.js: %NODE_VER%

REM Check Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found. Please install Python v3.14 first.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version') do set PYTHON_VER=%%i
echo    Python: %PYTHON_VER%

REM Check PostgreSQL
where psql >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: PostgreSQL not found. Please install PostgreSQL v16 first.
    echo Download from: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('psql --version') do set PG_VER=%%i
echo    PostgreSQL: %PG_VER%

REM Check Git
where git >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Git not found. Please install Git first.
    echo Download from: https://git-scm.com/download/win
    pause
    exit /b 1
)
echo    Git: Found

echo.
echo [2/8] Setting up directories...
if not exist "C:\Apps" mkdir C:\Apps
cd C:\Apps

echo.
echo [3/8] Getting PostgreSQL password...
set /p PG_PASSWORD="Enter PostgreSQL 'postgres' user password: "

echo.
echo [4/8] Creating database...
set PGPASSWORD=%PG_PASSWORD%
psql -U postgres -c "CREATE DATABASE evcharging;" 2>nul
if %errorlevel% neq 0 (
    echo    Database may already exist, continuing...
)
echo    Database 'evcharging' ready

echo.
echo [5/8] Setting up backend...
cd %APP_DIR%\backend

REM Create virtual environment
if not exist "venv" (
    python -m venv venv
)
call venv\Scripts\activate.bat

REM Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

REM Generate JWT secret
for /f "tokens=*" %%i in ('python -c "import secrets; print(secrets.token_hex(32))"') do set JWT_SECRET=%%i

REM Create .env file
(
echo DATABASE_URL=postgresql+asyncpg://postgres:%PG_PASSWORD%@localhost:5432/evcharging
echo DATABASE_TYPE=postgresql
echo JWT_SECRET=%JWT_SECRET%
echo CORS_ORIGINS=*
) > .env

call deactivate
echo    Backend configured

echo.
echo [6/8] Setting up frontend...
cd %APP_DIR%\frontend

REM Install dependencies
call yarn install

REM Create .env file
(
echo REACT_APP_BACKEND_URL=http://localhost:8001
) > .env

REM Build production bundle
call yarn build
echo    Frontend built

echo.
echo [7/8] Installing Windows services...

REM Check if NSSM exists
if not exist "%NSSM_PATH%\nssm.exe" (
    echo    NSSM not found at %NSSM_PATH%
    echo    Please download NSSM from https://nssm.cc/download
    echo    Extract to C:\nssm
    echo.
    echo    Skipping service installation...
    goto :skip_services
)

REM Install serve globally for frontend
call npm install -g serve

REM Remove existing services if they exist
%NSSM_PATH%\nssm.exe stop EVChargingBackend >nul 2>&1
%NSSM_PATH%\nssm.exe remove EVChargingBackend confirm >nul 2>&1
%NSSM_PATH%\nssm.exe stop EVChargingFrontend >nul 2>&1
%NSSM_PATH%\nssm.exe remove EVChargingFrontend confirm >nul 2>&1

REM Install Backend Service
%NSSM_PATH%\nssm.exe install EVChargingBackend "%APP_DIR%\backend\venv\Scripts\python.exe"
%NSSM_PATH%\nssm.exe set EVChargingBackend AppDirectory "%APP_DIR%\backend"
%NSSM_PATH%\nssm.exe set EVChargingBackend AppParameters "-m uvicorn server:app --host 0.0.0.0 --port 8001"
%NSSM_PATH%\nssm.exe set EVChargingBackend DisplayName "EV Charging Backend"
%NSSM_PATH%\nssm.exe set EVChargingBackend Start SERVICE_AUTO_START
echo    Backend service installed

REM Install Frontend Service
for /f "tokens=*" %%i in ('where serve') do set SERVE_PATH=%%i
%NSSM_PATH%\nssm.exe install EVChargingFrontend "%SERVE_PATH%"
%NSSM_PATH%\nssm.exe set EVChargingFrontend AppDirectory "%APP_DIR%\frontend"
%NSSM_PATH%\nssm.exe set EVChargingFrontend AppParameters "-s build -l 3000"
%NSSM_PATH%\nssm.exe set EVChargingFrontend DisplayName "EV Charging Frontend"
%NSSM_PATH%\nssm.exe set EVChargingFrontend Start SERVICE_AUTO_START
echo    Frontend service installed

REM Start services
net start EVChargingBackend
net start EVChargingFrontend
echo    Services started

:skip_services

echo.
echo [8/8] Configuring firewall...
netsh advfirewall firewall add rule name="EV Charging Backend" dir=in action=allow protocol=tcp localport=8001 >nul 2>&1
netsh advfirewall firewall add rule name="EV Charging Frontend" dir=in action=allow protocol=tcp localport=3000 >nul 2>&1
echo    Firewall rules added

echo.
echo ============================================
echo    Installation Complete!
echo ============================================
echo.
echo Access the application at:
echo    http://localhost:3000
echo.
echo Default Login:
echo    Email: admin@evcharge.com
echo    Password: admin123
echo.
echo IMPORTANT: Change the admin password immediately!
echo.
echo Service Management:
echo    Start:   net start EVChargingBackend / EVChargingFrontend
echo    Stop:    net stop EVChargingBackend / EVChargingFrontend
echo    Status:  sc query EVChargingBackend / EVChargingFrontend
echo.
pause
