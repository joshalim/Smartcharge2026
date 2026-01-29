#!/bin/bash

#######################################
# EV Charging Management System
# Automated Installation Script
# Ubuntu 20.04/22.04 LTS
#######################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/opt/evcharging"
APP_USER="www-data"
DOMAIN=""
ENABLE_SSL="n"

# Print colored message
print_msg() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[i]${NC} $1"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "Please run as root (sudo ./install.sh)"
        exit 1
    fi
}

# Detect Ubuntu version
detect_ubuntu() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        if [ "$ID" != "ubuntu" ]; then
            print_error "This script is designed for Ubuntu. Detected: $ID"
            exit 1
        fi
        UBUNTU_VERSION=$VERSION_ID
        print_msg "Detected Ubuntu $UBUNTU_VERSION"
    else
        print_error "Cannot detect OS version"
        exit 1
    fi
}

# Get user input
get_config() {
    echo ""
    echo "============================================"
    echo "   EV Charging Management System Installer"
    echo "============================================"
    echo ""
    
    read -p "Enter your domain name (e.g., evcharging.example.com): " DOMAIN
    if [ -z "$DOMAIN" ]; then
        DOMAIN="localhost"
        print_warn "No domain provided, using localhost"
    fi
    
    read -p "Enable SSL with Let's Encrypt? (y/n) [n]: " ENABLE_SSL
    ENABLE_SSL=${ENABLE_SSL:-n}
    
    if [ "$ENABLE_SSL" = "y" ] && [ "$DOMAIN" = "localhost" ]; then
        print_warn "SSL requires a valid domain. Disabling SSL."
        ENABLE_SSL="n"
    fi
    
    echo ""
    print_info "Configuration:"
    print_info "  Domain: $DOMAIN"
    print_info "  SSL: $ENABLE_SSL"
    print_info "  Install Directory: $APP_DIR"
    echo ""
    
    read -p "Continue with installation? (y/n) [y]: " CONTINUE
    CONTINUE=${CONTINUE:-y}
    if [ "$CONTINUE" != "y" ]; then
        print_warn "Installation cancelled"
        exit 0
    fi
}

# Install system dependencies
install_dependencies() {
    print_msg "Updating system packages..."
    apt update && apt upgrade -y
    
    print_msg "Installing system dependencies..."
    apt install -y \
        curl \
        wget \
        git \
        build-essential \
        software-properties-common \
        gnupg \
        lsb-release
}

# Install Node.js
install_nodejs() {
    print_msg "Installing Node.js 20.x LTS..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt install -y nodejs
    npm install -g yarn
    print_msg "Node.js $(node --version) installed"
}

# Install Python
install_python() {
    print_msg "Installing Python 3..."
    apt install -y python3 python3-pip python3-venv
    print_msg "Python $(python3 --version) installed"
}

# Install MongoDB
install_mongodb() {
    print_msg "Installing MongoDB 4.2 (compatible with non-AVX CPUs)..."
    
    # Install gnupg and curl
    apt-get install -y gnupg curl
    
    # Import GPG key for MongoDB 4.2
    wget -qO - https://www.mongodb.org/static/pgp/server-4.2.asc | apt-key add -
    
    # Add repository for Ubuntu Focal (works for both 20.04 and compatible systems)
    echo "deb [ arch=amd64,arm64 ] https://repo.mongodb.org/apt/ubuntu focal/mongodb-org/4.2 multiverse" | tee /etc/apt/sources.list.d/mongodb-org-4.2.list
    
    apt update
    apt install -y mongodb-org
    
    systemctl start mongod
    systemctl enable mongod
    
    print_msg "MongoDB $(mongod --version | head -1) installed and running"
}

# Install Nginx
install_nginx() {
    print_msg "Installing Nginx..."
    apt install -y nginx
    systemctl enable nginx
    print_msg "Nginx installed"
}

# Setup application
setup_application() {
    print_msg "Setting up application directory..."
    
    # Create directory if not exists (for fresh installs)
    if [ ! -d "$APP_DIR" ]; then
        mkdir -p $APP_DIR
        print_warn "Directory created. You need to clone your repository here."
        print_info "Run: git clone YOUR_REPO_URL $APP_DIR"
    fi
    
    # Check if we're already in the repo directory
    if [ -f "./backend/server.py" ]; then
        print_msg "Found application in current directory, copying..."
        cp -r . $APP_DIR/
    fi
    
    chown -R $APP_USER:$APP_USER $APP_DIR
}

# Setup backend
setup_backend() {
    print_msg "Setting up backend..."
    
    cd $APP_DIR/backend
    
    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate
    
    # Install dependencies
    pip install --upgrade pip
    pip install -r requirements.txt
    
    # Create .env file
    JWT_SECRET=$(openssl rand -hex 32)
    cat > .env << EOF
MONGO_URL=mongodb://localhost:27017
DB_NAME=evcharging
JWT_SECRET=$JWT_SECRET
EOF
    
    deactivate
    
    print_msg "Backend configured"
}

# Setup frontend
setup_frontend() {
    print_msg "Setting up frontend..."
    
    cd $APP_DIR/frontend
    
    # Install dependencies
    yarn install
    
    # Create .env file
    if [ "$ENABLE_SSL" = "y" ]; then
        BACKEND_URL="https://$DOMAIN"
    else
        BACKEND_URL="http://$DOMAIN"
    fi
    
    cat > .env << EOF
REACT_APP_BACKEND_URL=$BACKEND_URL
EOF
    
    # Build production bundle
    yarn build
    
    print_msg "Frontend built"
}

# Create systemd service
create_systemd_service() {
    print_msg "Creating systemd service..."
    
    cat > /etc/systemd/system/evcharging-backend.service << EOF
[Unit]
Description=EV Charging Backend API
After=network.target mongod.service

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR/backend
Environment="PATH=$APP_DIR/backend/venv/bin"
ExecStart=$APP_DIR/backend/venv/bin/uvicorn server:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable evcharging-backend
    systemctl start evcharging-backend
    
    print_msg "Backend service created and started"
}

# Configure Nginx
configure_nginx() {
    print_msg "Configuring Nginx..."
    
    cat > /etc/nginx/sites-available/evcharging << EOF
server {
    listen 80;
    server_name $DOMAIN;

    root $APP_DIR/frontend/build;
    index index.html;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    location /api/ {
        proxy_pass http://127.0.0.1:8001/api/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
        client_max_body_size 50M;
    }

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

    # Enable site
    ln -sf /etc/nginx/sites-available/evcharging /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    
    # Test and reload
    nginx -t
    systemctl reload nginx
    
    print_msg "Nginx configured"
}

# Setup SSL
setup_ssl() {
    if [ "$ENABLE_SSL" = "y" ]; then
        print_msg "Setting up SSL with Let's Encrypt..."
        
        apt install -y certbot python3-certbot-nginx
        certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@$DOMAIN
        
        print_msg "SSL certificate installed"
    fi
}

# Configure firewall
configure_firewall() {
    print_msg "Configuring firewall..."
    
    ufw allow OpenSSH
    ufw allow 'Nginx Full'
    ufw --force enable
    
    print_msg "Firewall configured"
}

# Print completion message
print_completion() {
    echo ""
    echo "============================================"
    echo -e "${GREEN}   Installation Complete!${NC}"
    echo "============================================"
    echo ""
    
    if [ "$ENABLE_SSL" = "y" ]; then
        echo -e "Access your application at: ${BLUE}https://$DOMAIN${NC}"
    else
        echo -e "Access your application at: ${BLUE}http://$DOMAIN${NC}"
    fi
    
    echo ""
    echo "Default Admin Credentials:"
    echo "  Email: admin@evcharge.com"
    echo "  Password: admin123"
    echo ""
    echo -e "${YELLOW}IMPORTANT: Change the admin password immediately!${NC}"
    echo ""
    echo "Useful commands:"
    echo "  - View backend logs: sudo journalctl -u evcharging-backend -f"
    echo "  - Restart backend: sudo systemctl restart evcharging-backend"
    echo "  - Restart Nginx: sudo systemctl reload nginx"
    echo ""
    echo "Documentation: $APP_DIR/INSTALL.md"
    echo ""
}

# Main installation flow
main() {
    check_root
    detect_ubuntu
    get_config
    
    echo ""
    print_msg "Starting installation..."
    echo ""
    
    install_dependencies
    install_nodejs
    install_python
    install_mongodb
    install_nginx
    setup_application
    
    if [ -f "$APP_DIR/backend/server.py" ]; then
        setup_backend
        setup_frontend
        create_systemd_service
        configure_nginx
        setup_ssl
        configure_firewall
        
        # Fix permissions
        chown -R $APP_USER:$APP_USER $APP_DIR
        
        print_completion
    else
        echo ""
        print_warn "Application files not found in $APP_DIR"
        print_info "Please clone your repository and run setup manually:"
        echo ""
        echo "  cd $APP_DIR"
        echo "  git clone YOUR_REPO_URL ."
        echo "  sudo ./install.sh"
        echo ""
    fi
}

# Run main function
main "$@"
