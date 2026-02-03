@echo off
REM Start Simple Backend Server
REM Use this if the main server has issues

cd /d C:\Apps\Smartcharge2026\backend
call venv\Scripts\activate.bat
echo Starting simple backend server...
python server_simple.py
pause
