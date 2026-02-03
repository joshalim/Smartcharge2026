@echo off
REM EV Charging Backend Start Script
REM This script properly activates the virtual environment before starting uvicorn

cd /d C:\Apps\Smartcharge2026\backend
call venv\Scripts\activate.bat
python -m uvicorn server:app --host 0.0.0.0 --port 8001
