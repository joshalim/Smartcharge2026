@echo off
REM Diagnose Login Issues
REM Run this to check database and test login

cd /d C:\Apps\Smartcharge2026\backend
call venv\Scripts\activate.bat
pip install requests -q
python diagnose_login.py
pause
