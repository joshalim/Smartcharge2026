@echo off
REM EV Charging Frontend Start Script
REM Serves the built React app on port 3000

cd /d C:\Apps\Smartcharge2026\frontend

REM Try serve first, fall back to http-server
where serve >nul 2>&1
if %errorlevel% equ 0 (
    serve -s build -l 3000
) else (
    REM Install and use http-server as fallback
    npm install -g http-server
    http-server build -p 3000 -c-1
)
