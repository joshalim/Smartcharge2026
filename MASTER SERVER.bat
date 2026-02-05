@echo off
title SmartCharge Master Server
cd /d C:\Apps\Smartcharge2026

echo.
echo ========================================
echo   SMARTCHARGE MASTER SERVER
echo ========================================
echo.

:: Step 1: Activate virtual environment
echo [1/5] Activating virtual environment...
cd /d C:\Apps\Smartcharge2026\backend
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo       OK

:: Step 2: Install missing dependencies
echo.
echo [2/5] Checking dependencies...
pip show email-validator >nul 2>&1
if errorlevel 1 (
    echo       Installing email-validator...
    pip install email-validator
)
pip show pandas >nul 2>&1
if errorlevel 1 (
    echo       Installing pandas...
    pip install pandas
)
echo       OK

:: Step 3: Setup database and admin user
echo.
echo [3/5] Setting up database and admin user...
python create_admin.py
if errorlevel 1 (
    echo [WARNING] Admin setup had issues - continuing anyway
)

:: Step 4: Start Backend
echo.
echo [4/5] Starting Backend Server (port 8001)...
set DATABASE_TYPE=postgresql
start "SMARTCHARGE BACKEND" cmd /k "cd /d C:\Apps\Smartcharge2026\backend && call venv\Scripts\activate.bat && set DATABASE_TYPE=postgresql && python -m uvicorn server:app --host 0.0.0.0 --port 8001"

echo       Waiting for backend to start...
timeout /t 8 /nobreak >nul
echo       OK

:: Step 5: Start Frontend
echo.
echo [5/5] Starting Frontend Server (port 3000)...
start "SMARTCHARGE FRONTEND" cmd /k "cd /d C:\Apps\Smartcharge2026\frontend && npx serve -s build -l 3000"

timeout /t 3 /nobreak >nul
echo       OK

echo.
echo ========================================
echo   SMARTCHARGE SERVERS STARTED
echo ========================================
echo.
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:3000
echo.
echo   Login Credentials:
echo   ------------------
echo   Email:    admin@evcharge.com
echo   Password: admin123
echo.
echo ========================================
echo.
echo   Two windows should now be open:
echo   - SMARTCHARGE BACKEND
echo   - SMARTCHARGE FRONTEND
echo.
echo   Keep those windows open to run the app.
echo.
echo ========================================
echo.
echo Press any key to open browser...
pause >nul

start http://localhost:3000

echo.
echo You can close this window now.
pause
