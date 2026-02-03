@echo off
echo ============================================
echo   SmartCharge Service Installation
echo ============================================
echo.

:: Check for admin rights
net session >nul 2>&1
if errorlevel 1 (
    echo [ERROR] This script requires Administrator privileges.
    echo Please right-click and select "Run as administrator"
    pause
    exit /b 1
)

:: Check if NSSM exists
if not exist "C:\nssm\win64\nssm.exe" (
    echo [ERROR] NSSM not found at C:\nssm\win64\nssm.exe
    echo Please download NSSM from https://nssm.cc/download
    echo and extract to C:\nssm\
    pause
    exit /b 1
)

echo [1/4] Stopping existing services...
net stop EVChargingBackend 2>nul
net stop EVChargingFrontend 2>nul

echo.
echo [2/4] Removing old services...
C:\nssm\win64\nssm.exe remove EVChargingBackend confirm 2>nul
C:\nssm\win64\nssm.exe remove EVChargingFrontend confirm 2>nul

echo.
echo [3/4] Installing Backend Service...
C:\nssm\win64\nssm.exe install EVChargingBackend "C:\Apps\Smartcharge2026\backend\service-backend.bat"
C:\nssm\win64\nssm.exe set EVChargingBackend AppDirectory "C:\Apps\Smartcharge2026\backend"
C:\nssm\win64\nssm.exe set EVChargingBackend DisplayName "SmartCharge EV Backend"
C:\nssm\win64\nssm.exe set EVChargingBackend Description "SmartCharge EV Charging Management System - Backend API"
C:\nssm\win64\nssm.exe set EVChargingBackend Start SERVICE_AUTO_START
C:\nssm\win64\nssm.exe set EVChargingBackend AppStdout "C:\Apps\Smartcharge2026\logs\backend.log"
C:\nssm\win64\nssm.exe set EVChargingBackend AppStderr "C:\Apps\Smartcharge2026\logs\backend-error.log"

:: Create logs directory
if not exist "C:\Apps\Smartcharge2026\logs" mkdir "C:\Apps\Smartcharge2026\logs"

echo.
echo [4/4] Installing Frontend Service...
C:\nssm\win64\nssm.exe install EVChargingFrontend "C:\Program Files\nodejs\npx.cmd"
C:\nssm\win64\nssm.exe set EVChargingFrontend AppParameters "serve -s build -l 3000"
C:\nssm\win64\nssm.exe set EVChargingFrontend AppDirectory "C:\Apps\Smartcharge2026\frontend"
C:\nssm\win64\nssm.exe set EVChargingFrontend DisplayName "SmartCharge EV Frontend"
C:\nssm\win64\nssm.exe set EVChargingFrontend Description "SmartCharge EV Charging Management System - Frontend"
C:\nssm\win64\nssm.exe set EVChargingFrontend Start SERVICE_AUTO_START
C:\nssm\win64\nssm.exe set EVChargingFrontend AppStdout "C:\Apps\Smartcharge2026\logs\frontend.log"
C:\nssm\win64\nssm.exe set EVChargingFrontend AppStderr "C:\Apps\Smartcharge2026\logs\frontend-error.log"

echo.
echo ============================================
echo   Starting Services...
echo ============================================
net start EVChargingBackend
net start EVChargingFrontend

echo.
echo ============================================
echo   Installation Complete!
echo ============================================
echo.
echo Services installed and started:
echo   - EVChargingBackend  (port 8001)
echo   - EVChargingFrontend (port 3000)
echo.
echo Log files: C:\Apps\Smartcharge2026\logs\
echo.
echo To check status:  sc query EVChargingBackend
echo To stop service:  net stop EVChargingBackend
echo To start service: net start EVChargingBackend
echo.
pause
