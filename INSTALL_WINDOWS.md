# EV Charging Management System - Windows Server 2016 Installation Guide

Complete guide for deploying the Smart Charge EV Charging Management System on Windows Server 2016.

## Prerequisites

- Windows Server 2016 (64-bit)
- Administrator access
- Internet connection
- At least 4GB RAM, 20GB disk space

## Required Software Versions

| Software | Version | Download Link |
|----------|---------|---------------|
| Node.js | v25.5.0 | https://nodejs.org/dist/v25.5.0/node-v25.5.0-x64.msi |
| NPM | v11.8.0 | (included with Node.js) |
| Python | v3.14 | https://www.python.org/downloads/release/python-3140/ |
| PostgreSQL | v16 | https://www.enterprisedb.com/downloads/postgres-postgresql-downloads |
| Git | Latest | https://git-scm.com/download/win |

---

## Step 1: Install Git

1. Download Git from https://git-scm.com/download/win
2. Run the installer with default options
3. Verify installation:
```cmd
git --version
```

---

## Step 2: Install Node.js v25.5.0

1. Download Node.js v25.5.0 from https://nodejs.org/dist/v25.5.0/node-v25.5.0-x64.msi
2. Run the installer:
   - Accept the license agreement
   - Use default installation path: `C:\Program Files\nodejs`
   - Ensure "Add to PATH" is checked
3. Restart Command Prompt and verify:
```cmd
node --version
npm --version
```
Expected output: `v25.5.0` and `v11.8.0`

4. Install Yarn globally:
```cmd
npm install -g yarn
yarn --version
```

---

## Step 3: Install Python v3.14

1. Download Python 3.14 from https://www.python.org/downloads/release/python-3140/
2. Run the installer:
   - **CHECK** "Add Python 3.14 to PATH"
   - Click "Customize installation"
   - Check all Optional Features
   - Check "Install for all users"
   - Install to: `C:\Python314`
3. Verify installation:
```cmd
python --version
pip --version
```
Expected output: `Python 3.14.x`

---

## Step 4: Install PostgreSQL v16

1. Download PostgreSQL 16 from https://www.enterprisedb.com/downloads/postgres-postgresql-downloads
2. Run the installer:
   - Installation Directory: `C:\Program Files\PostgreSQL\16`
   - Data Directory: `C:\Program Files\PostgreSQL\16\data`
   - Password: Set a strong password for `postgres` user (remember this!)
   - Port: `5432` (default)
   - Locale: Default
3. **DO NOT** launch Stack Builder when prompted
4. Add PostgreSQL to PATH:
   - Open System Properties > Environment Variables
   - Edit `Path` variable
   - Add: `C:\Program Files\PostgreSQL\16\bin`
5. Verify installation:
```cmd
psql --version
```

### Create Database

Open Command Prompt as Administrator:
```cmd
psql -U postgres
```
Enter the password you set during installation, then run:
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

### Create Virtual Environment
```cmd
cd backend
python -m venv venv
venv\Scripts\activate
```

### Install Dependencies
```cmd
pip install --upgrade pip
pip install -r requirements.txt
```

### Configure Environment
Create file `backend\.env`:
```env
DATABASE_URL=postgresql+asyncpg://postgres:YOUR_PASSWORD@localhost:5432/evcharging
DATABASE_TYPE=postgresql
JWT_SECRET=your-super-secure-jwt-secret-change-this-in-production
CORS_ORIGINS=*
```

**Important:** Replace `YOUR_PASSWORD` with your PostgreSQL password.

### Generate Secure JWT Secret
```cmd
python -c "import secrets; print(secrets.token_hex(32))"
```
Copy the output and replace `your-super-secure-jwt-secret-change-this-in-production` in `.env`

---

## Step 7: Setup Frontend

```cmd
cd ..\frontend
yarn install
```

### Configure Environment
Create file `frontend\.env`:
```env
REACT_APP_BACKEND_URL=http://localhost:8001
```

For production with a domain:
```env
REACT_APP_BACKEND_URL=https://your-domain.com
```

### Build Production Bundle
```cmd
yarn build
```

---

## Step 8: Install Windows Services

### Option A: Using NSSM (Recommended)

1. Download NSSM from https://nssm.cc/download
2. Extract to `C:\nssm`
3. Add to PATH or use full path

#### Install Backend Service
```cmd
C:\nssm\win64\nssm.exe install EVChargingBackend
```
In the GUI:
- **Path:** `C:\Apps\Smartcharge2026\backend\venv\Scripts\python.exe`
- **Startup directory:** `C:\Apps\Smartcharge2026\backend`
- **Arguments:** `-m uvicorn server:app --host 0.0.0.0 --port 8001`

Click "Install service"

#### Install Frontend Service (using serve)
First, install serve globally:
```cmd
npm install -g serve
```

```cmd
C:\nssm\win64\nssm.exe install EVChargingFrontend
```
In the GUI:
- **Path:** `C:\Program Files\nodejs\serve.cmd`
- **Startup directory:** `C:\Apps\Smartcharge2026\frontend`
- **Arguments:** `-s build -l 3000`

Click "Install service"

#### Start Services
```cmd
net start EVChargingBackend
net start EVChargingFrontend
```

### Option B: Using PowerShell Scripts

Create `C:\Apps\Smartcharge2026\start-backend.ps1`:
```powershell
Set-Location "C:\Apps\Smartcharge2026\backend"
& ".\venv\Scripts\activate.ps1"
python -m uvicorn server:app --host 0.0.0.0 --port 8001
```

Create `C:\Apps\Smartcharge2026\start-frontend.ps1`:
```powershell
Set-Location "C:\Apps\Smartcharge2026\frontend"
npx serve -s build -l 3000
```

---

## Step 9: Configure Windows Firewall

Open PowerShell as Administrator:
```powershell
# Allow Backend (port 8001)
New-NetFirewallRule -DisplayName "EV Charging Backend" -Direction Inbound -Port 8001 -Protocol TCP -Action Allow

# Allow Frontend (port 3000)
New-NetFirewallRule -DisplayName "EV Charging Frontend" -Direction Inbound -Port 3000 -Protocol TCP -Action Allow

# Allow PostgreSQL (port 5432) - only if remote access needed
New-NetFirewallRule -DisplayName "PostgreSQL" -Direction Inbound -Port 5432 -Protocol TCP -Action Allow
```

---

## Step 10: Setup IIS as Reverse Proxy (Optional but Recommended)

### Install IIS
1. Open Server Manager
2. Add Roles and Features
3. Select "Web Server (IIS)"
4. Include "Application Development" features

### Install URL Rewrite and ARR
1. Download URL Rewrite: https://www.iis.net/downloads/microsoft/url-rewrite
2. Download ARR: https://www.iis.net/downloads/microsoft/application-request-routing

### Configure Reverse Proxy
Create `C:\inetpub\wwwroot\web.config`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <system.webServer>
        <rewrite>
            <rules>
                <rule name="API Proxy" stopProcessing="true">
                    <match url="^api/(.*)" />
                    <action type="Rewrite" url="http://localhost:8001/api/{R:1}" />
                </rule>
                <rule name="Frontend Proxy" stopProcessing="true">
                    <match url="(.*)" />
                    <action type="Rewrite" url="http://localhost:3000/{R:1}" />
                </rule>
            </rules>
        </rewrite>
    </system.webServer>
</configuration>
```

---

## Step 11: Verify Installation

### Test Backend
```cmd
curl http://localhost:8001/api/health
```

### Test Frontend
Open browser: http://localhost:3000

### Default Login
- **Email:** admin@evcharge.com
- **Password:** admin123

**⚠️ IMPORTANT: Change the admin password immediately after first login!**

---

## Troubleshooting

### Backend won't start
```cmd
cd C:\Apps\Smartcharge2026\backend
venv\Scripts\activate
python -c "import asyncpg; print('asyncpg OK')"
python -c "from sqlalchemy import create_engine; print('SQLAlchemy OK')"
```

### Database connection issues
```cmd
psql -U postgres -d evcharging -c "SELECT 1;"
```

### Check service status
```cmd
sc query EVChargingBackend
sc query EVChargingFrontend
```

### View logs (if using NSSM)
```cmd
C:\nssm\win64\nssm.exe status EVChargingBackend
```

### Port already in use
```cmd
netstat -ano | findstr :8001
netstat -ano | findstr :3000
taskkill /PID <PID> /F
```

---

## Updating the Application

```cmd
cd C:\Apps\Smartcharge2026

:: Stop services
net stop EVChargingBackend
net stop EVChargingFrontend

:: Pull latest changes
git pull origin main

:: Update backend
cd backend
venv\Scripts\activate
pip install -r requirements.txt
deactivate

:: Update frontend
cd ..\frontend
yarn install
yarn build

:: Start services
net start EVChargingBackend
net start EVChargingFrontend
```

---

## Backup Database

### Manual Backup
```cmd
pg_dump -U postgres evcharging > C:\Backups\evcharging_backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%.sql
```

### Scheduled Backup (Task Scheduler)
Create `C:\Scripts\backup-db.bat`:
```batch
@echo off
set BACKUP_DIR=C:\Backups
set PGPASSWORD=YOUR_PASSWORD
pg_dump -U postgres evcharging > %BACKUP_DIR%\evcharging_%date:~-4,4%%date:~-10,2%%date:~-7,2%.sql
```

Schedule this script to run daily via Task Scheduler.

---

## Security Recommendations

1. **Change Default Password:** Update admin password immediately
2. **Use HTTPS:** Configure SSL certificate in IIS
3. **Restrict Database Access:** Only allow localhost connections
4. **Regular Updates:** Keep Windows, Node.js, and Python updated
5. **Backup Strategy:** Implement daily database backups
6. **Firewall:** Only open necessary ports

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/YOUR_USERNAME/Smartcharge2026/issues
