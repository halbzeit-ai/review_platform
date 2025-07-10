#!/bin/bash
# Deployment script for Review Platform on Datacrunch.io instance

set -e  # Exit on any error

echo "🚀 Deploying Review Platform..."

# Configuration
APP_DIR="/opt/review-platform"
REPO_URL="https://github.com/halbzeit-ai/review_platform.git"  # Update with your repo
DOMAIN="your-domain.com"  # Update with your domain

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root"
    exit 1
fi

# Create application directory
print_status "Creating application directory..."
mkdir -p $APP_DIR
cd $APP_DIR

# Option 1: Clone from git (if you have a repo)
#if [ ! -z "$REPO_URL" ] && [ "$REPO_URL" != "https://github.com/your-username/review-platform.git" ]; then
#    print_status "Cloning repository..."
#    git clone $REPO_URL .
#else
#    print_warning "No git repository configured. Please upload your code manually to $APP_DIR"
#    print_warning "You can use: scp -r /path/to/review_platform/* root@YOUR_IP:$APP_DIR/"
#    echo "Press Enter when code is uploaded..."
#    read
#fi

# Create Python virtual environment
apt install python3.12
apt install python3.12-venv

print_status "Setting up Python environment..."
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
print_status "Installing Python dependencies..."
pip install -r requirements.txt
cd backend

# Create environment file
print_status "Setting up environment configuration..."
if [ ! -f .env ]; then
    cp .env.example .env
    print_warning "Please edit $APP_DIR/backend/.env with your configuration"
    print_warning "Required variables:"
    echo "  - DATACRUNCH_CLIENT_ID"
    echo "  - DATACRUNCH_CLIENT_SECRET" 
    echo "  - DATACRUNCH_VOLUME_ID"
    echo "  - SECRET_KEY (generate a secure key)"
fi

# Install Node.js dependencies and build frontend
print_status "Building frontend..."
apt-get install -y nodejs npm

cd ../frontend
npm install
npm run build

# Setup Nginx configuration
print_status "Configuring Nginx..."
apt-get install -y nginx
cat > /etc/nginx/sites-available/review-platform << EOF
server {
    listen 80;
    server_name $DOMAIN \$public_ipv4;

    # Frontend
    location / {
        root $APP_DIR/frontend/build;
        index index.html index.htm;
        try_files \$uri \$uri/ /index.html;
    }

    # API
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Static files
    location /static {
        root $APP_DIR/frontend/build;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}
EOF

# Enable site
ln -sf /etc/nginx/sites-available/review-platform /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx configuration
nginx -t

# Create database directory and setup
print_status "Setting up database..."
mkdir -p $APP_DIR/data
cd $APP_DIR/backend

# Initialize database (create tables)
python -c "
from app.db.database import engine
from app.db.models import Base
Base.metadata.create_all(bind=engine)
print('Database initialized successfully')
"

# Create shared filesystem directories
print_status "Setting up shared filesystem..."

# Mount NFS shared filesystem
mkdir -p /mnt/shared

# Check if already mounted
if mountpoint -q /mnt/shared; then
    print_status "Shared filesystem already mounted"
else
    print_status "Mounting shared filesystem..."
    mount -t nfs nfs.fin-01.datacrunch.io:/SFS-5gkKcxHe-6721608d /mnt/shared

    # Add to fstab for automatic mounting at boot
    if ! grep -q "nfs.fin-01.datacrunch.io:/SFS-5gkKcxHe-6721608d" /etc/fstab; then
        echo "nfs.fin-01.datacrunch.io:/SFS-5gkKcxHe-6721608d /mnt/shared nfs defaults 0 0" >> /etc/fstab
        print_status "Added NFS mount to fstab"
    fi
fi

# Create required directories
mkdir -p /mnt/shared/{uploads,results,temp}
chown -R root:root /mnt/shared
chmod -R 755 /mnt/shared

# Test read/write access
if echo "test" > /mnt/shared/test.txt && cat /mnt/shared/test.txt > /dev/null && rm /mnt/shared/test.txt; then
    print_status "Shared filesystem is working correctly"
else
    print_error "Shared filesystem test failed"
fi

#print_status "Setting up shared volume directories..."
#MOUNT_PATH="/mnt/shared"
#if mountpoint -q $MOUNT_PATH; then
#    mkdir -p $MOUNT_PATH/{uploads,results,temp}
#    chown -R root:root $MOUNT_PATH
#    chmod -R 755 $MOUNT_PATH
#    print_status "Shared volume directories created"
#else
#    print_warning "Shared volume not mounted at $MOUNT_PATH"
#    print_warning "Please mount your shared volume and run: mkdir -p $MOUNT_PATH/{uploads,results,temp}"
#fi

# Start services
print_status "Starting services..."
systemctl restart nginx
systemctl start review-platform
systemctl enable review-platform

# Check service status
sleep 3
if systemctl is-active --quiet review-platform; then
    print_status "Backend service is running"
else
    print_error "Backend service failed to start"
    systemctl status review-platform
fi

if systemctl is-active --quiet nginx; then
    print_status "Nginx is running"
else
    print_error "Nginx failed to start"
    systemctl status nginx
fi

# Get public IP
PUBLIC_IP=$(curl -s ifconfig.me || echo "Unable to get public IP")

print_status "Deployment completed!"
echo ""
echo "🌐 Your application should be available at:"
echo "   http://$PUBLIC_IP"
if [ "$DOMAIN" != "your-domain.com" ]; then
    echo "   http://$DOMAIN"
fi
echo ""
echo "📝 Next steps:"
echo "   1. Edit $APP_DIR/backend/.env with your Datacrunch credentials"
echo "   2. Mount and configure your shared volume"
echo "   3. Restart the service: systemctl restart review-platform"
echo "   4. Check logs: journalctl -f -u review-platform"
echo ""
echo "🔧 Useful commands:"
echo "   - View logs: journalctl -f -u review-platform"
echo "   - Restart API: systemctl restart review-platform"
echo "   - Restart Nginx: systemctl restart nginx"
echo "   - Check status: systemctl status review-platform"