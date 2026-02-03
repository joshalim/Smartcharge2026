# EV Charging Management System - Self-Hosted Installation Guide

This guide covers deploying the Smart Charge EV Charging Management System on self-hosted servers.

## Deployment Options

| Platform | Guide | Best For |
|----------|-------|----------|
| **Docker** | [Docker Compose](#docker-deployment) | Quick setup, any OS |
| **Windows Server 2016** | [INSTALL_WINDOWS.md](INSTALL_WINDOWS.md) | Windows environments |
| **Ubuntu Linux** | [Manual Installation](#manual-installation) | Linux servers |

## Software Requirements

| Component | Windows | Linux | Docker |
|-----------|---------|-------|--------|
| Node.js | v25.5.0 | v20.x | v20-alpine |
| NPM | v11.8.0 | v10.x | included |
| Python | v3.14 | v3.11+ | v3.11-slim |
| PostgreSQL | v16 | v15+ | v16-alpine |

---

## Docker Deployment

### Prerequisites
- Docker and Docker Compose installed
- Domain name (optional, for SSL)

### Quick Start with Docker

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/ev-charging-management.git
cd ev-charging-management

# Create environment file
cp .env.example .env

# Edit .env file with your settings
nano .env
# Set JWT_SECRET to a secure random string
# Set REACT_APP_BACKEND_URL to your domain or IP

# Generate secure JWT secret
JWT_SECRET=$(openssl rand -hex 32)
sed -i "s/your-super-secure-jwt-secret-change-this/$JWT_SECRET/" .env

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Access at http://localhost or your domain
```

### Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend

# Access MongoDB shell
docker exec -it evcharging-mongodb mongosh

# Backup MongoDB
docker exec evcharging-mongodb mongodump --out /data/backup
docker cp evcharging-mongodb:/data/backup ./backup

# Restore MongoDB
docker cp ./backup evcharging-mongodb:/data/backup
docker exec evcharging-mongodb mongorestore /data/backup
```

### Docker with SSL (Traefik)

For production with SSL, add Traefik as a reverse proxy:

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  traefik:
    image: traefik:v2.10
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge=true"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - "/var/run/docker.sock:/var/run/docker.sock:ro"
      - "./letsencrypt:/letsencrypt"
    networks:
      - evcharging-network

  frontend:
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.frontend.rule=Host(`yourdomain.com`)"
      - "traefik.http.routers.frontend.entrypoints=websecure"
      - "traefik.http.routers.frontend.tls.certresolver=letsencrypt"
    # Remove ports section from frontend in main docker-compose.yml
```

---

## Prerequisites (Manual Installation)

- Ubuntu 20.04 LTS or 22.04 LTS
- Domain name pointing to your server (for SSL)
- Root or sudo access
- At least 2GB RAM, 20GB disk space

## Quick Start

```bash
# Clone and run the automated installer
git clone https://github.com/YOUR_USERNAME/ev-charging-management.git
cd ev-charging-management
sudo chmod +x install.sh
sudo ./install.sh
```

---

## Manual Installation

### Step 1: System Updates & Dependencies

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git build-essential software-properties-common
```

### Step 2: Install Node.js 20.x (LTS)

```bash
# Add NodeSource repository
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -

# Install Node.js
sudo apt install -y nodejs

# Install Yarn globally
sudo npm install -g yarn

# Verify installation
node --version  # Should show v20.x.x
yarn --version
```

### Step 3: Install Python 3.10+

```bash
# Install Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Verify installation
python3 --version  # Should show 3.10+
```

### Step 4: Install PostgreSQL 15

```bash
# Install PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE evcharging;
CREATE USER evcharging_user WITH ENCRYPTED PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE evcharging TO evcharging_user;
\c evcharging
GRANT ALL ON SCHEMA public TO evcharging_user;
EOF

# Verify PostgreSQL is running
sudo systemctl status postgresql
psql --version  # Should show v15.x or similar
```

### Step 5: Install Nginx

```bash
sudo apt install -y nginx
sudo systemctl enable nginx
```

### Step 6: Clone Repository

```bash
# Create application directory
sudo mkdir -p /opt/evcharging
sudo chown $USER:$USER /opt/evcharging

# Clone repository
cd /opt/evcharging
git clone https://github.com/YOUR_USERNAME/ev-charging-management.git .
```

### Step 7: Backend Setup

```bash
cd /opt/evcharging/backend

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create environment file
cat > .env << 'EOF'
MONGO_URL=mongodb://localhost:27017
DB_NAME=evcharging
JWT_SECRET=your-super-secure-jwt-secret-change-this-in-production
EOF

# Generate a secure JWT secret
JWT_SECRET=$(openssl rand -hex 32)
sed -i "s/your-super-secure-jwt-secret-change-this-in-production/$JWT_SECRET/" .env

# Deactivate virtual environment
deactivate
```

### Step 8: Frontend Setup

```bash
cd /opt/evcharging/frontend

# Install dependencies
yarn install

# Create environment file with your domain
cat > .env << 'EOF'
REACT_APP_BACKEND_URL=https://your-domain.com
EOF

# Build production bundle
yarn build
```

### Step 9: Create Systemd Service for Backend

```bash
sudo cat > /etc/systemd/system/evcharging-backend.service << 'EOF'
[Unit]
Description=EV Charging Backend API
After=network.target mongod.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/evcharging/backend
Environment="PATH=/opt/evcharging/backend/venv/bin"
ExecStart=/opt/evcharging/backend/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Set correct ownership
sudo chown -R www-data:www-data /opt/evcharging

# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable evcharging-backend
sudo systemctl start evcharging-backend

# Check status
sudo systemctl status evcharging-backend
```

### Step 10: Configure Nginx

```bash
sudo cat > /etc/nginx/sites-available/evcharging << 'EOF'
server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS (uncomment after SSL setup)
    # return 301 https://$server_name$request_uri;

    # Frontend static files
    root /opt/evcharging/frontend/build;
    index index.html;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # API proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        client_max_body_size 50M;
    }

    # React Router - serve index.html for all routes
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Cache static assets
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Replace your-domain.com with actual domain
sudo sed -i 's/your-domain.com/YOUR_ACTUAL_DOMAIN/g' /etc/nginx/sites-available/evcharging

# Enable site
sudo ln -sf /etc/nginx/sites-available/evcharging /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test and reload Nginx
sudo nginx -t
sudo systemctl reload nginx
```

### Step 11: SSL Certificate with Let's Encrypt (Recommended)

```bash
# Install Certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal is configured automatically
# Test renewal
sudo certbot renew --dry-run
```

### Step 12: Configure Firewall

```bash
# Enable UFW firewall
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable

# Verify
sudo ufw status
```

### Step 13: Create Admin User

```bash
# The application creates a default admin user on first run
# Default credentials:
# Email: admin@evcharge.com
# Password: admin123

# IMPORTANT: Change the password immediately after first login!
```

---

## Post-Installation

### Verify Installation

```bash
# Check all services are running
sudo systemctl status mongod
sudo systemctl status evcharging-backend
sudo systemctl status nginx

# Test API endpoint
curl http://localhost:8001/api/health

# Access the application
# Open https://your-domain.com in your browser
```

### View Logs

```bash
# Backend logs
sudo journalctl -u evcharging-backend -f

# Nginx access logs
sudo tail -f /var/log/nginx/access.log

# Nginx error logs
sudo tail -f /var/log/nginx/error.log

# MongoDB logs
sudo tail -f /var/log/mongodb/mongod.log
```

### Update Application

```bash
cd /opt/evcharging

# Pull latest changes
git pull origin main

# Update backend
cd backend
source venv/bin/activate
pip install -r requirements.txt
deactivate

# Update frontend
cd ../frontend
yarn install
yarn build

# Restart services
sudo systemctl restart evcharging-backend
sudo systemctl reload nginx
```

---

## Configuration Options

### Environment Variables (Backend)

| Variable | Description | Default |
|----------|-------------|---------|
| `MONGO_URL` | MongoDB connection string | `mongodb://localhost:27017` |
| `DB_NAME` | Database name | `evcharging` |
| `JWT_SECRET` | Secret for JWT tokens | (required) |

### Environment Variables (Frontend)

| Variable | Description | Example |
|----------|-------------|---------|
| `REACT_APP_BACKEND_URL` | Backend API URL | `https://your-domain.com` |

---

## Security Recommendations

1. **Change Default Passwords**: Immediately change the admin password after first login
2. **Secure MongoDB**: Configure MongoDB authentication for production
3. **Regular Backups**: Set up automated MongoDB backups
4. **Keep Updated**: Regularly update system packages and application
5. **Monitor Logs**: Set up log monitoring for suspicious activity

### Secure MongoDB (Optional but Recommended)

```bash
# Connect to MongoDB
mongosh

# Create admin user
use admin
db.createUser({
  user: "evcharging_admin",
  pwd: "YOUR_SECURE_PASSWORD",
  roles: [{ role: "userAdminAnyDatabase", db: "admin" }]
})

# Create application user
use evcharging
db.createUser({
  user: "evcharging_app",
  pwd: "YOUR_APP_PASSWORD",
  roles: [{ role: "readWrite", db: "evcharging" }]
})

exit

# Enable authentication in MongoDB
sudo nano /etc/mongod.conf
# Add under security:
# security:
#   authorization: enabled

# Restart MongoDB
sudo systemctl restart mongod

# Update backend .env with authenticated URL
# MONGO_URL=mongodb://evcharging_app:YOUR_APP_PASSWORD@localhost:27017/evcharging
```

---

## Troubleshooting

### Backend won't start

```bash
# Check logs
sudo journalctl -u evcharging-backend -n 50

# Verify Python environment
cd /opt/evcharging/backend
source venv/bin/activate
python -c "import fastapi; print('OK')"

# Check MongoDB connection
mongosh --eval "db.runCommand({ping:1})"
```

### Frontend shows blank page

```bash
# Verify build exists
ls -la /opt/evcharging/frontend/build/

# Check Nginx config
sudo nginx -t

# Verify REACT_APP_BACKEND_URL is correct in .env
cat /opt/evcharging/frontend/.env
```

### 502 Bad Gateway

```bash
# Backend is likely not running
sudo systemctl status evcharging-backend

# Restart backend
sudo systemctl restart evcharging-backend
```

### Permission denied errors

```bash
# Fix ownership
sudo chown -R www-data:www-data /opt/evcharging
```

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/YOUR_USERNAME/ev-charging-management/issues
- Documentation: https://github.com/YOUR_USERNAME/ev-charging-management/wiki

---

## License

MIT License - See LICENSE file for details.
