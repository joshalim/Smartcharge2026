@echo off
REM ============================================
REM Smartcharge2026 - Startup Script
REM Run this at Windows startup to start both services
REM ============================================

echo Starting Smartcharge2026 EV Charging System...
echo.

REM Start Backend in a new window
echo Starting Backend Server...
start "Smartcharge Backend" cmd /k "cd /d C:\Apps\Smartcharge2026\backend && call venv\Scripts\activate.bat && python -m uvicorn server:app --host 0.0.0.0 --port 8001"

REM Wait a few seconds for backend to initialize
timeout /t 5 /nobreak >nul

REM Start Frontend in a new window
echo Starting Frontend Server...
start "Smartcharge Frontend" cmd /k "cd /d C:\Apps\Smartcharge2026\frontend && npx serve -s build -l 3000"

echo.
echo ============================================
echo Smartcharge2026 is starting...
echo.
echo Backend:  http://localhost:8001
echo Frontend: http://localhost:3000
echo.
echo Login: admin@evcharge.com / admin123
echo ============================================
echo.
echo You can close this window. The servers will
echo continue running in their own windows.
echo.
pause
