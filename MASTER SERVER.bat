@echo off
title SmartCharge Master Server
cd /d C:\Apps\Smartcharge2026

echo.
echo ========================================
echo   SMARTCHARGE MASTER SERVER
echo ========================================
echo.

:: Step 1: Setup Admin User
echo [1/3] Setting up database and admin user...
cd /d C:\Apps\Smartcharge2026\backend
call venv\Scripts\activate.bat

python create_admin.py
if errorlevel 1 (
    echo [ERROR] Failed to create admin user
    echo.
    pause
)

echo.
echo [2/3] Starting Backend Server...
echo.

:: Start backend - keep window open with /k
start "BACKEND" cmd /k "cd /d C:\Apps\Smartcharge2026\backend && call venv\Scripts\activate.bat && set DATABASE_TYPE=postgresql && python -m uvicorn server:app --host 0.0.0.0 --port 8001"

echo Waiting 10 seconds for backend to start...
timeout /t 10 /nobreak

echo.
echo [3/3] Starting Frontend Server...
echo.

:: Start frontend - keep window open with /k
start "FRONTEND" cmd /k "cd /d C:\Apps\Smartcharge2026\frontend && npx serve -s build -l 3000"

echo Waiting 5 seconds for frontend to start...
timeout /t 5 /nobreak

echo.
echo ========================================
echo   SERVERS STARTED
echo ========================================
echo.
echo   Backend:  http://localhost:8001
echo   Frontend: http://localhost:3000
echo.
echo   Login: admin@evcharge.com / admin123
echo.
echo ========================================
echo.

:: Open browser
start http://localhost:3000

echo Press any key to exit this window...
echo (Keep the BACKEND and FRONTEND windows open)
pause >nul
