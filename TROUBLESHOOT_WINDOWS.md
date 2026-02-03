# Troubleshooting Windows Service Issues

## Error: "A service specific error occurred: 3"

This error means the service failed to start. Follow these steps to diagnose:

---

## Step 1: Test Backend Manually

Open Command Prompt as Administrator and run:

```cmd
cd C:\Apps\Smartcharge2026\backend
.\venv\Scripts\activate
python -m uvicorn server:app --host 0.0.0.0 --port 8001
```

**If you see errors**, fix them first before proceeding.

---

## Step 2: Check NSSM Service Configuration

```cmd
C:\nssm\win64\nssm.exe edit EVChargingBackend
```

Verify these settings:
- **Path:** `C:\Apps\Smartcharge2026\backend\venv\Scripts\python.exe`
- **Startup directory:** `C:\Apps\Smartcharge2026\backend`
- **Arguments:** `-m uvicorn server:app --host 0.0.0.0 --port 8001`

---

## Step 3: Check NSSM Logs

```cmd
C:\nssm\win64\nssm.exe status EVChargingBackend
```

View Windows Event Viewer:
1. Open Event Viewer (eventvwr.msc)
2. Go to Windows Logs > Application
3. Look for errors from "nssm" or "EVChargingBackend"

---

## Step 4: Use Wrapper Script Instead

Create `C:\Apps\Smartcharge2026\backend\start-server.bat`:

```batch
@echo off
cd /d C:\Apps\Smartcharge2026\backend
call venv\Scripts\activate.bat
python -m uvicorn server:app --host 0.0.0.0 --port 8001
```

Then reconfigure NSSM:

```cmd
C:\nssm\win64\nssm.exe stop EVChargingBackend
C:\nssm\win64\nssm.exe remove EVChargingBackend confirm

C:\nssm\win64\nssm.exe install EVChargingBackend "C:\Apps\Smartcharge2026\backend\start-server.bat"
C:\nssm\win64\nssm.exe set EVChargingBackend AppDirectory "C:\Apps\Smartcharge2026\backend"
C:\nssm\win64\nssm.exe set EVChargingBackend DisplayName "EV Charging Backend"
C:\nssm\win64\nssm.exe set EVChargingBackend Start SERVICE_AUTO_START

net start EVChargingBackend
```

---

## Step 5: Check Common Issues

### Issue: Python not in venv
```cmd
C:\Apps\Smartcharge2026\backend\venv\Scripts\python.exe --version
```
Should show Python version.

### Issue: Missing dependencies
```cmd
cd C:\Apps\Smartcharge2026\backend
.\venv\Scripts\activate
pip install -r requirements.txt
```

### Issue: Wrong .env file
Check `C:\Apps\Smartcharge2026\backend\.env` exists with:
```
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/evcharging
DATABASE_TYPE=postgresql
JWT_SECRET=your-secret-key
```

### Issue: PostgreSQL not running
```cmd
sc query postgresql-x64-16
```
If not running:
```cmd
net start postgresql-x64-16
```

---

## Step 6: Run as Console App (No Service)

If services won't work, run directly in a terminal:

**PowerShell (keep open):**
```powershell
cd C:\Apps\Smartcharge2026\backend
.\venv\Scripts\Activate.ps1
python -m uvicorn server:app --host 0.0.0.0 --port 8001
```

**Or use Task Scheduler** to run the batch file at startup.
