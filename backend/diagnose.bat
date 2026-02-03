@echo off
echo ============================================
echo SmartCharge Full Diagnostic Tool
echo ============================================
echo.

cd /d C:\Apps\Smartcharge2026\backend
call venv\Scripts\activate.bat

echo Running diagnostic...
echo.
python diagnose_full.py

echo.
pause
