@echo off
echo ============================================
echo SmartCharge Backend Startup (PostgreSQL)
echo ============================================

cd /d C:\Apps\Smartcharge2026\backend
call venv\Scripts\activate.bat

echo Starting backend server...
python -m uvicorn server_pg:app --host 0.0.0.0 --port 8001

pause
