@echo off
echo ============================================
echo SmartCharge Frontend Rebuild Tool
echo ============================================
echo.

cd /d C:\Apps\Smartcharge2026\frontend

echo [1] Checking frontend .env configuration...
echo.
type .env
echo.
echo.

echo [2] The REACT_APP_BACKEND_URL should be:
echo     For local: http://localhost:8001
echo     For IIS proxy: (leave empty or use domain)
echo.

set /p choice="Do you want to update .env to http://localhost:8001? (Y/N): "
if /i "%choice%"=="Y" (
    echo REACT_APP_BACKEND_URL=http://localhost:8001 > .env
    echo Updated .env file!
)

echo.
echo [3] Installing dependencies...
call yarn install

echo.
echo [4] Building frontend...
call yarn build

echo.
echo ============================================
echo Frontend rebuild complete!
echo ============================================
echo.
echo If using Windows Services, restart the frontend:
echo   net stop EVChargingFrontend
echo   net start EVChargingFrontend
echo.
pause
