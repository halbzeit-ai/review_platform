#!/bin/bash

# Comprehensive Production CPU Server Setup Script
# This script sets up a complete production CPU server from scratch
# Includes: PostgreSQL, Backend, Frontend, Processing Queue, Security

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions
log_section() { echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}\n${CYAN}► $1${NC}\n${CYAN}═══════════════════════════════════════════════${NC}"; }
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; exit 1; }

# Configuration
PRODUCTION_CPU_IP="135.181.63.224"
PRODUCTION_GPU_IP="135.181.63.133"
PROJECT_ROOT="/opt/review-platform"
SHARED_FILESYSTEM="/mnt/CPU-GPU"
DB_NAME="review-platform"
DB_USER="review_user"
DB_PASSWORD="simpleprod2024"

# Parse command line arguments
SKIP_SECURITY=false
SKIP_BACKUP=false
RESTORE_DB=""
CREATE_SUDO_USER=""
SETUP_SSL="auto"  # Default to auto-detect
DOMAIN_NAME="halbzeit.ai"
SSL_EMAIL="ramin@halbzeit.ai"

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-security)
            SKIP_SECURITY=true
            shift
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --restore-db)
            RESTORE_DB="$2"
            shift 2
            ;;
        --create-user)
            CREATE_SUDO_USER="$2"
            shift 2
            ;;
        --setup-ssl)
            SETUP_SSL="yes"
            shift
            ;;
        --no-ssl)
            SETUP_SSL="no"
            shift
            ;;
        --domain)
            DOMAIN_NAME="$2"
            shift 2
            ;;
        --ssl-email)
            SSL_EMAIL="$2"
            shift 2
            ;;
        --help|-h)
            cat << 'EOF'
Production CPU Server Setup Script

This script sets up a complete production CPU server including:
- System dependencies and packages
- PostgreSQL database server
- Backend API service (FastAPI)
- Frontend static files (React)
- Processing Queue Worker service
- Nginx web server
- Security hardening (optional)
- SSL/TLS certificates (Let's Encrypt)

Usage: ./setup-production-cpu.sh [options]

Options:
  --skip-security      Skip security hardening steps
  --skip-backup       Skip database backup step
  --restore-db FILE   Restore database from backup file
  --create-user NAME  Create sudo user with given name
  --setup-ssl         Force SSL/TLS certificate setup (default: auto-detect)
  --no-ssl           Skip SSL setup entirely
  --domain NAME       Domain name for SSL certificates (default: halbzeit.ai)
  --ssl-email EMAIL   Email for Let's Encrypt notifications (default: ramin@halbzeit.ai)
  --help, -h         Show this help message

SSL Configuration:
  By default, the script auto-detects if SSL certificates should be installed
  by checking if the domain points to this server. This prevents the network
  errors that occur when frontend expects HTTPS but server only has HTTP.

Examples:
  # Fresh installation
  ./setup-production-cpu.sh

  # Fresh installation with SSL
  ./setup-production-cpu.sh --setup-ssl --domain halbzeit.ai --ssl-email admin@halbzeit.ai

  # Restore from backup
  ./setup-production-cpu.sh --restore-db backup_production_20250807.sql

  # Setup with new sudo user and SSL
  ./setup-production-cpu.sh --create-user admin --setup-ssl

Environment:
  Production CPU: 135.181.63.224
  Production GPU: 135.181.63.133
  Shared Storage: /mnt/CPU-GPU

EOF
            exit 0
            ;;
        *)
            log_error "Unknown argument: $1\nUse --help for usage information"
            ;;
    esac
done

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
fi

# Detect server environment
log_section "Server Environment Detection"
CURRENT_IP=$(hostname -I | awk '{print $1}')
log_info "Current server IP: $CURRENT_IP"

if [[ "$CURRENT_IP" != "$PRODUCTION_CPU_IP" ]]; then
    log_warning "This script is intended for production CPU server ($PRODUCTION_CPU_IP)"
    read -p "Continue anyway? (yes/no): " CONTINUE
    [[ "$CONTINUE" != "yes" ]] && exit 1
fi

# Step 1: System Updates and Dependencies
log_section "Step 1: System Updates and Dependencies"

log_info "Updating system packages..."
apt update && apt upgrade -y

log_info "Installing required packages..."
apt install -y \
    build-essential \
    python3-pip \
    python3-dev \
    python3-venv \
    postgresql \
    postgresql-contrib \
    nginx \
    certbot \
    python3-certbot-nginx \
    git \
    curl \
    wget \
    htop \
    net-tools \
    ufw \
    fail2ban \
    redis-server \
    supervisor \
    nodejs \
    npm

log_success "System dependencies installed"

# Step 2: Clone Repository (if not exists)
log_section "Step 2: Repository Setup"

#if [[ ! -d "$PROJECT_ROOT" ]]; then
#    log_info "Cloning repository..."
#    git clone git@github.com:halbzeit-ai/review_platform.git "$PROJECT_ROOT"
#    cd "$PROJECT_ROOT"
#else
#    log_info "Repository already exists at $PROJECT_ROOT"
#    cd "$PROJECT_ROOT"
#    git pull origin main || log_warning "Could not pull latest changes"
#fi

# Step 3: PostgreSQL Setup
log_section "Step 3: PostgreSQL Database Setup"

log_info "Configuring PostgreSQL..."

# Create database user
sudo -u postgres psql -c "SELECT 1 FROM pg_user WHERE usename = '$DB_USER'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"

# Create database
sudo -u postgres psql -c "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" | grep -q 1 || \
    sudo -u postgres psql -c "CREATE DATABASE \"$DB_NAME\" OWNER $DB_USER;"

# Grant all privileges
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE \"$DB_NAME\" TO $DB_USER;"

# Configure PostgreSQL for remote connections (from GPU server)
# Use a more reliable method to detect PostgreSQL version
PG_VERSION=$(ls /etc/postgresql/ | head -1)
PG_CONFIG="/etc/postgresql/$PG_VERSION/main/postgresql.conf"
PG_HBA="/etc/postgresql/$PG_VERSION/main/pg_hba.conf"

# Verify config files exist
if [[ ! -f "$PG_CONFIG" ]]; then
    log_error "PostgreSQL config file not found at $PG_CONFIG"
fi

# Update listen_addresses
grep -q "^listen_addresses = '\*'" "$PG_CONFIG" || \
    echo "listen_addresses = '*'" >> "$PG_CONFIG"

# Add GPU server to allowed connections
grep -q "$PRODUCTION_GPU_IP" "$PG_HBA" || \
    echo "host    all             all             $PRODUCTION_GPU_IP/32            md5" >> "$PG_HBA"

systemctl restart postgresql
log_success "PostgreSQL configured"

# Restore database if backup provided
if [[ -n "$RESTORE_DB" ]]; then
    log_info "Restoring database from $RESTORE_DB..."
    PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d $DB_NAME < "$RESTORE_DB"
    log_success "Database restored"
else
    # Run migrations from both directories
    log_info "Running database migrations..."
    
    # Run backend migrations first (older)
    cd "$PROJECT_ROOT/backend"
    for migration in migrations/*.sql; do
        if [[ -f "$migration" ]]; then
            log_info "  Running backend migration: $(basename "$migration")"
            PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d $DB_NAME < "$migration"
        fi
    done
    
    # Run newer migrations (including processing queue)
    cd "$PROJECT_ROOT"
    for migration in migrations/*.sql; do
        if [[ -f "$migration" ]]; then
            log_info "  Running migration: $(basename "$migration")"
            PGPASSWORD=$DB_PASSWORD psql -h localhost -U $DB_USER -d $DB_NAME < "$migration"
        fi
    done
    
    # Run Python schema creation
    python3 scripts/create_production_schema_final.py || log_warning "Schema creation script failed"
fi

# Step 4: Backend Setup
log_section "Step 4: Backend API Setup"

cd "$PROJECT_ROOT/backend"

# Create virtual environment
log_info "Setting up Python virtual environment..."
python3 -m venv "$PROJECT_ROOT/venv"
source "$PROJECT_ROOT/venv/bin/activate"

# Install dependencies
log_info "Installing Python dependencies..."
pip install --upgrade pip
pip install -r "$PROJECT_ROOT/requirements.txt"

# Deploy production environment configuration
log_info "Deploying production environment configuration..."
cd "$PROJECT_ROOT"
./environments/deploy-environment.sh production

# Create systemd service for backend
log_info "Creating backend systemd service..."
cat > /etc/systemd/system/review-platform.service << 'EOF'
[Unit]
Description=HALBZEIT Review Platform Backend API
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=/opt/review-platform/backend
EnvironmentFile=/opt/review-platform/backend/.env
ExecStart=/opt/review-platform/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable review-platform.service
systemctl start review-platform.service
log_success "Backend API service started"

# Step 5: Processing Queue Worker Setup
log_section "Step 5: Processing Queue Worker Setup"

log_info "Setting up Processing Queue Worker..."

# Copy service file
cp "$PROJECT_ROOT/scripts/processing-worker.service" /etc/systemd/system/

systemctl daemon-reload
systemctl enable processing-worker.service
systemctl start processing-worker.service
log_success "Processing Queue Worker service started"

# Step 6: Frontend Setup
log_section "Step 6: Frontend Setup"

cd "$PROJECT_ROOT/frontend"

# Install Node.js dependencies
log_info "Installing frontend dependencies..."
npm install

# Build production frontend with correct API URL
log_info "Building frontend for production..."

# Determine API URL based on SSL setup
if [[ "$SETUP_SSL" == "yes" ]]; then
    FRONTEND_API_URL="https://$DOMAIN_NAME"
    log_info "Building frontend with HTTPS API URL: $FRONTEND_API_URL"
else
    FRONTEND_API_URL="http://$DOMAIN_NAME"
    log_info "Building frontend with HTTP API URL: $FRONTEND_API_URL"
    log_warning "⚠️  Frontend will use HTTP - consider setting up SSL for production security"
fi

REACT_APP_API_URL="$FRONTEND_API_URL" npm run build

# Deploy with zero-downtime method
log_info "Deploying frontend with zero-downtime..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BUILD_DIR="/var/www/html/build_$TIMESTAMP"
cp -r build "$BUILD_DIR"
ln -sfn "$BUILD_DIR" /var/www/html/build
log_success "Frontend deployed"

# Step 7: Nginx Configuration
log_section "Step 7: Nginx Web Server Setup"

log_info "Configuring Nginx..."

cat > /etc/nginx/sites-available/review-platform << EOF
server {
    listen 80;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;

    # Frontend
    root /var/www/html/build;
    index index.html;

    # API proxy
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts for long-running requests
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    # Frontend routing
    location / {
        try_files $uri $uri/ /index.html;
    }

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # File upload size limit
    client_max_body_size 100M;
}
EOF

ln -sf /etc/nginx/sites-available/review-platform /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
log_success "Nginx configured"

# Step 8: SSL/TLS Setup (auto-detect or manual)
log_section "Step 8: SSL/TLS Certificate Setup"

# Function to check if domain resolves to this server
check_domain_resolution() {
    local domain=$1
    local server_ip=$2
    
    # Get domain's IP address
    domain_ip=$(dig +short "$domain" | head -1)
    
    if [[ "$domain_ip" == "$server_ip" ]]; then
        return 0  # Domain points to this server
    else
        return 1  # Domain doesn't point to this server
    fi
}

# Auto-detect SSL setup need
if [[ "$SETUP_SSL" == "auto" ]]; then
    log_info "Auto-detecting SSL setup requirements for $DOMAIN_NAME..."
    
    if check_domain_resolution "$DOMAIN_NAME" "$PRODUCTION_CPU_IP"; then
        log_info "✅ Domain $DOMAIN_NAME resolves to this server ($PRODUCTION_CPU_IP)"
        log_info "🔒 Setting up SSL certificates automatically..."
        SETUP_SSL="yes"
    else
        domain_ip=$(dig +short "$DOMAIN_NAME" | head -1)
        log_warning "⚠️  Domain $DOMAIN_NAME resolves to $domain_ip, not this server ($PRODUCTION_CPU_IP)"
        log_warning "SSL setup will be skipped. Update DNS or use --setup-ssl to force SSL setup."
        SETUP_SSL="no"
    fi
fi

# Setup SSL if enabled
if [[ "$SETUP_SSL" == "yes" ]]; then
    log_info "Setting up Let's Encrypt SSL certificates for $DOMAIN_NAME..."
    
    # Install certbot if not present
    if ! command -v certbot &> /dev/null; then
        log_info "Installing certbot..."
        apt install -y certbot python3-certbot-nginx
    fi
    
    # Setup SSL certificates
    if certbot --nginx -d "$DOMAIN_NAME" -d "www.$DOMAIN_NAME" --non-interactive --agree-tos --email "$SSL_EMAIL"; then
        log_success "SSL certificates installed for $DOMAIN_NAME"
        
        # Test HTTPS endpoint
        sleep 2
        if curl -s -f "https://$DOMAIN_NAME/api/health" >/dev/null; then
            log_success "HTTPS endpoint verification successful"
        else
            log_warning "HTTPS endpoint test failed - please check manually"
        fi
    else
        log_error "SSL certificate installation failed"
    fi
else
    log_info "SSL setup skipped"
    log_warning "⚠️  IMPORTANT: Frontend may expect HTTPS. Consider setting up SSL certificates manually:"
    log_warning "   certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --email $SSL_EMAIL"
fi

# Step 9: Shared Filesystem Mount
log_section "Step 9: Shared Filesystem Setup"

if [[ ! -d "$SHARED_FILESYSTEM" ]]; then
    log_info "Creating shared filesystem mount point..."
    mkdir -p "$SHARED_FILESYSTEM"
    
    # Add to /etc/fstab if not already there
    if ! grep -q "$SHARED_FILESYSTEM" /etc/fstab; then
        log_warning "Add NFS mount to /etc/fstab manually:"
        echo "Example: <NFS_SERVER>:/export/shared $SHARED_FILESYSTEM nfs defaults 0 0"
    fi
else
    log_info "Shared filesystem already mounted at $SHARED_FILESYSTEM"
fi

# Step 10: Security Hardening (unless skipped)
if [[ "$SKIP_SECURITY" != "true" ]]; then
    log_section "Step 10: Security Hardening"
    
    # Create sudo user if requested
    if [[ -n "$CREATE_SUDO_USER" ]]; then
        log_info "Creating sudo user: $CREATE_SUDO_USER"
        adduser --gecos "" "$CREATE_SUDO_USER"
        usermod -aG sudo "$CREATE_SUDO_USER"
        log_success "Sudo user created"
    fi
    
    # Run security hardening script
    if [[ -f "$PROJECT_ROOT/scripts/setup-security-hardening-safe.sh" ]]; then
        log_info "Running security hardening script..."
        bash "$PROJECT_ROOT/scripts/setup-security-hardening-safe.sh"
    else
        log_warning "Security hardening script not found"
    fi
else
    log_warning "Security hardening skipped (--skip-security flag used)"
fi

# Step 11: GPU Server Communication Test
log_section "Step 11: GPU Server Communication Test"

log_info "Testing connection to GPU server..."
if ping -c 1 "$PRODUCTION_GPU_IP" &> /dev/null; then
    log_success "GPU server is reachable"
    
    # Test GPU HTTP server
    if curl -s "http://$PRODUCTION_GPU_IP:5000/api/health" | grep -q "healthy"; then
        log_success "GPU HTTP server is responding"
    else
        log_warning "GPU HTTP server not responding on port 5000"
    fi
else
    log_warning "GPU server is not reachable"
fi

# Step 12: Service Health Check
log_section "Step 12: Service Health Check"

log_info "Checking all services..."

# Check PostgreSQL
systemctl is-active --quiet postgresql && \
    log_success "PostgreSQL: Active" || log_warning "PostgreSQL: Inactive"

# Check Backend API
systemctl is-active --quiet review-platform && \
    log_success "Backend API: Active" || log_warning "Backend API: Inactive"

# Check Processing Worker
systemctl is-active --quiet processing-worker && \
    log_success "Processing Worker: Active" || log_warning "Processing Worker: Inactive"

# Check Nginx
systemctl is-active --quiet nginx && \
    log_success "Nginx: Active" || log_warning "Nginx: Inactive"

# Check API endpoints
log_info "Testing API endpoints..."

# Test backend directly
if curl -s "http://localhost:8000/api/health" | grep -q "healthy"; then
    log_success "Backend API: Health check passed"
else
    log_warning "Backend API: Health check failed"
fi

# Test through Nginx (HTTP)
if curl -s "http://localhost/api/health" | grep -q "healthy"; then
    log_success "Nginx Proxy (HTTP): Working"
else
    log_warning "Nginx Proxy (HTTP): Failed"
fi

# Test HTTPS if SSL was configured
if [[ "$SETUP_SSL" == "yes" ]]; then
    log_info "Testing HTTPS configuration..."
    
    if curl -s -f "https://$DOMAIN_NAME/api/health" | grep -q "healthy"; then
        log_success "HTTPS API: Working correctly"
    else
        log_warning "HTTPS API: Failed - frontend may experience network errors"
        log_warning "Manual SSL setup may be required"
    fi
    
    # Check SSL certificate
    if openssl s_client -connect "$DOMAIN_NAME:443" -servername "$DOMAIN_NAME" </dev/null 2>/dev/null | grep -q "Verify return code: 0"; then
        log_success "SSL Certificate: Valid"
    else
        log_warning "SSL Certificate: Validation issues detected"
    fi
else
    log_warning "HTTPS: Not configured - frontend may expect HTTPS endpoints"
    log_info "To enable HTTPS later: certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --email $SSL_EMAIL"
fi

# Final Summary
log_section "Installation Complete!"

echo -e "${GREEN}✨ Production CPU server setup completed successfully!${NC}"
echo ""
echo -e "${BLUE}Service Status:${NC}"
echo "  • Backend API: http://localhost:8000"
echo "  • Frontend: http://localhost (Nginx)"
echo "  • Database: PostgreSQL on port 5432"
echo "  • Processing Queue: Active"
echo ""
echo -e "${BLUE}Important Commands:${NC}"
echo "  • View backend logs: journalctl -u review-platform -f"
echo "  • View worker logs: journalctl -u processing-worker -f"
echo "  • Restart backend: systemctl restart review-platform"
echo "  • Restart worker: systemctl restart processing-worker"
echo "  • Check status: systemctl status review-platform processing-worker"
echo ""

if [[ "$SKIP_SECURITY" == "true" ]]; then
    echo -e "${YELLOW}⚠️  Security hardening was skipped!${NC}"
    echo "  Run this to secure the server:"
    echo "  $PROJECT_ROOT/scripts/setup-security-hardening-safe.sh"
    echo ""
fi

if [[ -z "$CREATE_SUDO_USER" ]] && [[ "$SKIP_SECURITY" == "true" ]]; then
    echo -e "${RED}⚠️  WARNING: No sudo user created and root login may be disabled!${NC}"
    echo "  Create a sudo user immediately:"
    echo "  adduser <username> && usermod -aG sudo <username>"
    echo ""
fi

echo -e "${GREEN}🎉 Setup complete! Your production server is ready.${NC}"

# Create installation log
LOG_FILE="$PROJECT_ROOT/installation_$(date +%Y%m%d_%H%M%S).log"
echo "Installation completed at $(date)" > "$LOG_FILE"
echo "Server IP: $CURRENT_IP" >> "$LOG_FILE"
echo "Services installed: PostgreSQL, Backend API, Processing Worker, Nginx" >> "$LOG_FILE"
log_info "Installation log saved to: $LOG_FILE"
