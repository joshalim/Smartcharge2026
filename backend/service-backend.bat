@echo off
:: SmartCharge Backend Service Wrapper
:: This script is designed to be run by NSSM as a Windows Service

cd /d C:\Apps\Smartcharge2026\backend
call venv\Scripts\activate.bat

:: Ensure DATABASE_TYPE is set
set DATABASE_TYPE=postgresql

:: Start the server (use server.py, NOT server_simple.py)
python -m uvicorn server:app --host 0.0.0.0 --port 8001
