@echo off
REM Create Default Admin User
REM Run this if you can't login with default credentials

cd /d C:\Apps\Smartcharge2026\backend
call venv\Scripts\activate.bat
python create_admin.py
pause
