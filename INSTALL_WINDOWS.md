# EV Charging Management System - Windows Server 2016 Installation Guide

Complete guide for deploying the SmartCharge EV Charging Management System on Windows Server 2016.

---

## Quick Start (After Installation)

Double-click **`MASTER SERVER.bat`** in `C:\Apps\Smartcharge2026\` to start both servers.

**Login Credentials:**
- Email: `admin@evcharge.com`
- Password: `admin123`

---

## Prerequisites

- Windows Server 2016 (64-bit)
- Administrator access
- Internet connection
- At least 4GB RAM, 20GB disk space

## Required Software

| Software   | Version | Download Link |
|------------|---------|---------------|
| Node.js    | v20+    | https://nodejs.org/ |
| Python     | v3.11+  | https://www.python.org/downloads/ |
| PostgreSQL | v15+    | https://www.enterprisedb.com/downloads/postgres-postgresql-downloads |
| Git        | Latest  | https://git-scm.com/download/win |

> **Note:** Python 3.14 has compatibility issues with some packages. Python 3.11 or 3.12 is recommended.

---

## Step 1: Install Git

1. Download Git from https://git-scm.com/download/win
2. Run the installer with default options
3. Verify installation:
```cmd
git --version
```

---

## Step 2: Install Node.js

1. Download Node.js LTS from https://nodejs.org/
2. Run the installer with default options
3. Verify installation:
```cmd
node --version
npm --version
```

4. Install Yarn globally:
```cmd
npm install -g yarn serve
```

---

## Step 3: Install Python

1. Download Python from https://www.python.org/downloads/
2. Run the installer:
   - **CHECK** "Add Python to PATH"
   - Click "Customize installation"
   - Check all Optional Features
   - Check "Install for all users"
3. Verify installation:
```cmd
python --version
pip --version
```

---

## Step 4: Install PostgreSQL

1. Download PostgreSQL from https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2. Run the installer:
   - Set a password for `postgres` user (remember this!)
   - Port: `5432` (default)
3. Add PostgreSQL to PATH:
   - Open System Properties > Environment Variables
   - Edit `Path` variable
   - Add: `C:\Program Files\PostgreSQL\16\bin` (adjust version number)
4. Verify:
```cmd
psql --version
```

### Create Database

Open Command Prompt as Administrator:
```cmd
psql -U postgres
```
Enter password, then run:
```sql
CREATE DATABASE evcharging;
\q
```

---

## Step 5: Clone Repository

```cmd
cd C:\
mkdir Apps
cd Apps
git clone https://github.com/YOUR_USERNAME/Smartcharge2026.git
cd Smartcharge2026
```

---

## Step 6: Setup Backend

```cmd
cd C:\Apps\Smartcharge2026\backend
python -m venv venv
venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
pip install email-validator
```

### Configure Environment

Create file `C:\Apps\Smartcharge2026\backend\.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/evcharging
JWT_SECRET=your-super-secure-jwt-secret-change-this
CORS_ORIGINS=*
```

**Replace `YOUR_PASSWORD` with your PostgreSQL password.**

### Create Admin User

```cmd
python create_admin.py
```

---

## Step 7: Setup Frontend

```cmd
cd C:\Apps\Smartcharge2026\frontend
yarn install
```

### Configure Environment

Create file `C:\Apps\Smartcharge2026\frontend\.env`:
```env
REACT_APP_BACKEND_URL=http://YOUR_SERVER_IP:8001
```

**Replace `YOUR_SERVER_IP` with:**
- `localhost` for local access only
- Your server's IP address (e.g., `192.168.1.100`) for network access

### Build Frontend

```cmd
yarn build
```

---

## Step 8: Test Installation

### Start Backend (Terminal 1)
```cmd
cd C:\Apps\Smartcharge2026\backend
venv\Scripts\activate
python -m uvicorn server:app --host 0.0.0.0 --port 8001
```

### Start Frontend (Terminal 2)
```cmd
cd C:\Apps\Smartcharge2026\frontend
npx serve -s build -l 3000
```

### Verify
- Backend: http://localhost:8001/api/health
- Frontend: http://localhost:3000

### Login
- Email: `admin@evcharge.com`
- Password: `admin123`

---

## Step 9: Easy Startup with MASTER SERVER.bat

Once testing is complete, use the master script for easy startup:

```cmd
cd C:\Apps\Smartcharge2026
"MASTER SERVER.bat"
```

This script will:
1. Check and install missing dependencies
2. Setup database and admin user
3. Start backend server (port 8001)
4. Start frontend server (port 3000)
5. Open browser automatically

---

## Step 10: Configure Windows Firewall

Open PowerShell as Administrator:
```powershell
New-NetFirewallRule -DisplayName "SmartCharge Backend" -Direction Inbound -Port 8001 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "SmartCharge Frontend" -Direction Inbound -Port 3000 -Protocol TCP -Action Allow
```

---

## Step 11: Install as Windows Services (Optional)

For automatic startup on boot, install as Windows Services using NSSM:

1. Download NSSM from https://nssm.cc/download
2. Extract to `C:\nssm`
3. Run as Administrator:

```cmd
cd C:\Apps\Smartcharge2026
install-services.bat
```

Or manually:
```cmd
C:\nssm\win64\nssm.exe install EVChargingBackend "C:\Apps\Smartcharge2026\backend\service-backend.bat"
C:\nssm\win64\nssm.exe install EVChargingFrontend "C:\Program Files\nodejs\npx.cmd"
C:\nssm\win64\nssm.exe set EVChargingFrontend AppParameters "serve -s build -l 3000"
C:\nssm\win64\nssm.exe set EVChargingFrontend AppDirectory "C:\Apps\Smartcharge2026\frontend"

net start EVChargingBackend
net start EVChargingFrontend
```

---

## Updating the Application

### Quick Update
```cmd
cd C:\Apps\Smartcharge2026
git pull origin main
cd backend
venv\Scripts\activate
pip install -r requirements.txt
cd ..\frontend
yarn install
yarn build
```

Then restart using `MASTER SERVER.bat` or restart services:
```cmd
net stop EVChargingBackend
net stop EVChargingFrontend
net start EVChargingBackend
net start EVChargingFrontend
```

### After Update - If Login Fails

Run the admin setup again:
```cmd
cd C:\Apps\Smartcharge2026\backend
venv\Scripts\activate
python create_admin.py
```

---

## Troubleshooting

### Cannot Login After Update
```cmd
cd C:\Apps\Smartcharge2026\backend
venv\Scripts\activate
python create_admin.py
```

### Backend Won't Start
Check for missing packages:
```cmd
cd C:\Apps\Smartcharge2026\backend
venv\Scripts\activate
pip install email-validator pandas
```

### Frontend Shows Blank Page
Rebuild the frontend:
```cmd
cd C:\Apps\Smartcharge2026\frontend
yarn build
```

### Cannot Access From Other Computers
1. Check `frontend\.env` has the server IP (not localhost)
2. Rebuild frontend: `yarn build`
3. Check Windows Firewall rules

### Database Connection Error
Verify PostgreSQL is running:
```cmd
psql -U postgres -d evcharging -c "SELECT 1;"
```

### Check Service Status
```cmd
sc query EVChargingBackend
sc query EVChargingFrontend
```

### View Backend Logs
Check the SMARTCHARGE BACKEND window for error messages.

### Port Already in Use
```cmd
netstat -ano | findstr :8001
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

---

## Backup Database

```cmd
pg_dump -U postgres evcharging > C:\Backups\evcharging_backup.sql
```

## Restore Database

```cmd
psql -U postgres evcharging < C:\Backups\evcharging_backup.sql
```

---

## Security Checklist

- [ ] Change default admin password after first login
- [ ] Use strong JWT_SECRET in backend\.env
- [ ] Configure HTTPS via IIS reverse proxy for production
- [ ] Restrict database to localhost only
- [ ] Enable Windows Firewall with specific port rules
- [ ] Setup regular database backups

---

## Updating the Application

When you receive updated code files, follow these steps:

### Step 1: Stop Services
```cmd
REM If using MASTER SERVER.bat, close both command windows
REM If using Windows Services:
sc stop EVChargingBackend
sc stop EVChargingFrontend
```

### Step 2: Backup Database (Recommended)
```cmd
pg_dump -U postgres evcharging > C:\Backups\evcharging_%date:~-4,4%%date:~-10,2%%date:~-7,2%.sql
```

### Step 3: Update Backend Files
Copy these files from the updated source to `C:\Apps\Smartcharge2026\backend\`:
- `server.py`
- `database.py`
- `db_adapter.py`

### Step 4: Install New Dependencies (If Required)
```cmd
cd C:\Apps\Smartcharge2026\backend
venv\Scripts\activate
pip install -r requirements.txt
```

### Step 5: Rebuild Frontend (If Frontend Files Changed)
```cmd
cd C:\Apps\Smartcharge2026\frontend
yarn install
yarn build
```

### Step 6: Reset Admin User (If Login Fails)
```cmd
cd C:\Apps\Smartcharge2026\backend
venv\Scripts\activate
python create_admin.py
```

### Step 7: Start Services
```cmd
REM Use MASTER SERVER.bat
C:\Apps\Smartcharge2026\MASTER SERVER.bat
```

---

## Feb 2026 Update - Critical Fix

**Issue:** Login fails, charger creation returns 422 error, transaction import fails.

**Fix:** Updated `database.py` and `db_adapter.py` to include missing database models.

**Files to update:**
1. `backend/database.py` - Added new models: Settings, PayUPayment, PayUWebhookLog, OCPPBoot, OCPPTransaction, InvoiceWebhookConfig, InvoiceWebhookLog
2. `backend/db_adapter.py` - Added MODEL_MAP entries for all collections including 'pricing' alias

**After updating, run:**
```cmd
cd C:\Apps\Smartcharge2026\backend
venv\Scripts\activate
python create_admin.py
```

---

## File Structure

```
C:\Apps\Smartcharge2026\
├── MASTER SERVER.bat      <- Double-click to start everything
├── install-services.bat   <- Install as Windows Services
├── backend\
│   ├── .env               <- Database config (edit this!)
│   ├── venv\              <- Python virtual environment
│   ├── server.py          <- Main backend server
│   ├── create_admin.py    <- Creates admin user
│   ├── start-backend.bat  <- Manual backend start
│   └── service-backend.bat <- For Windows Service
├── frontend\
│   ├── .env               <- Backend URL config (edit this!)
│   ├── build\             <- Production build (yarn build)
│   └── src\               <- Source code
└── logs\                  <- Application logs
```

---

## Default Credentials

| Role  | Email                | Password |
|-------|----------------------|----------|
| Admin | admin@evcharge.com   | admin123 |

**⚠️ Change the admin password immediately after first login!**

---

## Support

For issues: Check the SMARTCHARGE BACKEND window for error messages, then refer to the Troubleshooting section above.
