@echo off
REM EV Charging Frontend Start Script
REM Serves the built React app on port 3000

cd /d C:\Apps\Smartcharge2026\frontend
npx serve -s build -l 3000
