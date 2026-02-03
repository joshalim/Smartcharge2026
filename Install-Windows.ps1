# ============================================
# EV Charging Management System
# Windows Server 2016 Installation Script
# PowerShell Version
# ============================================

#Requires -RunAsAdministrator

param(
    [string]$AppDir = "C:\Apps\Smartcharge2026",
    [string]$PostgresPassword = "",
    [switch]$SkipServices
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n[$script:StepNum/8] $Message" -ForegroundColor Cyan
    $script:StepNum++
}

function Write-Success {
    param([string]$Message)
    Write-Host "    [OK] $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "    [ERROR] $Message" -ForegroundColor Red
}

$script:StepNum = 1

Write-Host "`n============================================" -ForegroundColor Yellow
Write-Host "   EV Charging Management System Installer" -ForegroundColor Yellow
Write-Host "   Windows Server 2016" -ForegroundColor Yellow
Write-Host "============================================`n" -ForegroundColor Yellow

# Step 1: Check prerequisites
Write-Step "Checking prerequisites..."

# Check Node.js
try {
    $nodeVersion = node --version
    Write-Success "Node.js: $nodeVersion"
} catch {
    Write-Error "Node.js not found. Please install Node.js v25.5.0"
    Write-Host "Download from: https://nodejs.org/dist/v25.5.0/node-v25.5.0-x64.msi"
    exit 1
}

# Check Python
try {
    $pythonVersion = python --version
    Write-Success "Python: $pythonVersion"
} catch {
    Write-Error "Python not found. Please install Python v3.14"
    Write-Host "Download from: https://www.python.org/downloads/"
    exit 1
}

# Check PostgreSQL
try {
    $pgVersion = psql --version
    Write-Success "PostgreSQL: $pgVersion"
} catch {
    Write-Error "PostgreSQL not found. Please install PostgreSQL v16"
    Write-Host "Download from: https://www.enterprisedb.com/downloads/postgres-postgresql-downloads"
    exit 1
}

# Check Git
try {
    $gitVersion = git --version
    Write-Success "Git: Found"
} catch {
    Write-Error "Git not found. Please install Git"
    Write-Host "Download from: https://git-scm.com/download/win"
    exit 1
}

# Step 2: Get PostgreSQL password
Write-Step "Getting PostgreSQL password..."
if ([string]::IsNullOrEmpty($PostgresPassword)) {
    $securePassword = Read-Host "Enter PostgreSQL 'postgres' user password" -AsSecureString
    $PostgresPassword = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword))
}

# Step 3: Create database
Write-Step "Creating database..."
$env:PGPASSWORD = $PostgresPassword
try {
    psql -U postgres -c "CREATE DATABASE evcharging;" 2>$null
    Write-Success "Database 'evcharging' created"
} catch {
    Write-Host "    Database may already exist, continuing..." -ForegroundColor Yellow
}

# Step 4: Setup backend
Write-Step "Setting up backend..."
Set-Location "$AppDir\backend"

# Create virtual environment
if (-not (Test-Path "venv")) {
    python -m venv venv
}
& ".\venv\Scripts\Activate.ps1"

# Install dependencies
pip install --upgrade pip | Out-Null
pip install -r requirements.txt | Out-Null

# Generate JWT secret
$jwtSecret = python -c "import secrets; print(secrets.token_hex(32))"

# Create .env file
@"
DATABASE_URL=postgresql+asyncpg://postgres:$PostgresPassword@localhost:5432/evcharging
DATABASE_TYPE=postgresql
JWT_SECRET=$jwtSecret
CORS_ORIGINS=*
"@ | Out-File -FilePath ".env" -Encoding UTF8

deactivate
Write-Success "Backend configured"

# Step 5: Setup frontend
Write-Step "Setting up frontend..."
Set-Location "$AppDir\frontend"

# Install dependencies
yarn install | Out-Null

# Create .env file
@"
REACT_APP_BACKEND_URL=http://localhost:8001
"@ | Out-File -FilePath ".env" -Encoding UTF8

# Build production bundle
yarn build | Out-Null
Write-Success "Frontend built"

# Step 6: Install services
Write-Step "Installing Windows services..."

if (-not $SkipServices) {
    $nssmPath = "C:\nssm\win64\nssm.exe"
    
    if (Test-Path $nssmPath) {
        # Install serve globally
        npm install -g serve | Out-Null
        
        # Remove existing services
        & $nssmPath stop EVChargingBackend 2>$null
        & $nssmPath remove EVChargingBackend confirm 2>$null
        & $nssmPath stop EVChargingFrontend 2>$null
        & $nssmPath remove EVChargingFrontend confirm 2>$null
        
        # Install Backend Service
        & $nssmPath install EVChargingBackend "$AppDir\backend\venv\Scripts\python.exe"
        & $nssmPath set EVChargingBackend AppDirectory "$AppDir\backend"
        & $nssmPath set EVChargingBackend AppParameters "-m uvicorn server:app --host 0.0.0.0 --port 8001"
        & $nssmPath set EVChargingBackend DisplayName "EV Charging Backend"
        & $nssmPath set EVChargingBackend Start SERVICE_AUTO_START
        Write-Success "Backend service installed"
        
        # Install Frontend Service
        $servePath = (Get-Command serve).Source
        & $nssmPath install EVChargingFrontend $servePath
        & $nssmPath set EVChargingFrontend AppDirectory "$AppDir\frontend"
        & $nssmPath set EVChargingFrontend AppParameters "-s build -l 3000"
        & $nssmPath set EVChargingFrontend DisplayName "EV Charging Frontend"
        & $nssmPath set EVChargingFrontend Start SERVICE_AUTO_START
        Write-Success "Frontend service installed"
        
        # Start services
        Start-Service EVChargingBackend
        Start-Service EVChargingFrontend
        Write-Success "Services started"
    } else {
        Write-Host "    NSSM not found. Download from https://nssm.cc/download" -ForegroundColor Yellow
        Write-Host "    Extract to C:\nssm and re-run script" -ForegroundColor Yellow
    }
} else {
    Write-Host "    Skipping service installation (manual mode)" -ForegroundColor Yellow
}

# Step 7: Configure firewall
Write-Step "Configuring firewall..."
New-NetFirewallRule -DisplayName "EV Charging Backend" -Direction Inbound -Port 8001 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue | Out-Null
New-NetFirewallRule -DisplayName "EV Charging Frontend" -Direction Inbound -Port 3000 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue | Out-Null
Write-Success "Firewall rules added"

# Step 8: Complete
Write-Step "Installation complete!"

Write-Host "`n============================================" -ForegroundColor Green
Write-Host "   Installation Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host "`nAccess the application at:"
Write-Host "   http://localhost:3000" -ForegroundColor Cyan
Write-Host "`nDefault Login:"
Write-Host "   Email: admin@evcharge.com" -ForegroundColor White
Write-Host "   Password: admin123" -ForegroundColor White
Write-Host "`n" -NoNewline
Write-Host "IMPORTANT: " -ForegroundColor Red -NoNewline
Write-Host "Change the admin password immediately!"
Write-Host "`nService Management:"
Write-Host "   Start:  Start-Service EVChargingBackend, EVChargingFrontend"
Write-Host "   Stop:   Stop-Service EVChargingBackend, EVChargingFrontend"
Write-Host "   Status: Get-Service EVCharging*"
Write-Host ""
