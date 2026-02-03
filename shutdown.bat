@echo off
REM ============================================
REM Smartcharge2026 - Shutdown Script
REM Stops both backend and frontend servers
REM ============================================

echo Stopping Smartcharge2026 servers...
echo.

REM Kill Python/Uvicorn processes on port 8001
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8001 ^| findstr LISTENING') do (
    echo Stopping Backend (PID: %%a)...
    taskkill /PID %%a /F >nul 2>&1
)

REM Kill Node/Serve processes on port 3000
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :3000 ^| findstr LISTENING') do (
    echo Stopping Frontend (PID: %%a)...
    taskkill /PID %%a /F >nul 2>&1
)

echo.
echo Servers stopped.
pause
