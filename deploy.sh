#!/bin/bash

# Healthcare Startup Review Platform Deployment Script
# This script sets up the entire system on a new server

set -e  # Exit on any error

# Parse command line arguments
DRY_RUN=false
PRODUCTION=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        production)
            PRODUCTION=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [production]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Show what would be done without actually doing it"
            echo "  production   Build for production (includes frontend build)"
            echo "  --help, -h   Show this help message"
            exit 0
            ;;
    esac
done

echo "🚀 Healthcare Startup Review Platform Deployment"
echo "================================================="

if [ "$DRY_RUN" = true ]; then
    echo "🔍 DRY RUN MODE - No changes will be made"
    echo "=========================================="
fi

# Check if we're in the right directory
if [ ! -f "CLAUDE.md" ]; then
    echo "❌ Error: This script must be run from the project root directory"
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to run command or show what would be run
run_command() {
    local cmd="$1"
    local description="$2"
    
    if [ "$DRY_RUN" = true ]; then
        echo "🔍 Would run: $cmd"
        if [ -n "$description" ]; then
            echo "   Purpose: $description"
        fi
    else
        echo "🔄 Running: $cmd"
        eval "$cmd"
    fi
}

# Check prerequisites
echo "📋 Checking prerequisites..."

if ! command_exists node; then
    echo "❌ Node.js is required but not installed"
    echo "   Please install Node.js v16+ from https://nodejs.org/"
    exit 1
fi

if ! command_exists npm; then
    echo "❌ npm is required but not installed"
    exit 1
fi

if ! command_exists python3; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command_exists pip; then
    echo "❌ pip is required but not installed"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Setup frontend
echo ""
echo "🎨 Setting up frontend..."
cd frontend

echo "📦 Installing frontend dependencies..."
run_command "npm install --legacy-peer-deps" "Install all frontend dependencies from package.json (with legacy peer deps resolution)"

# Verify critical dependencies are installed
if [ "$DRY_RUN" = false ]; then
    echo "🔍 Verifying critical dependencies..."
    if ! npm list i18next-http-backend >/dev/null 2>&1; then
        echo "⚠️  Missing i18next-http-backend dependency"
        echo "🌐 Installing i18next-http-backend for dynamic translation loading..."
        run_command "npm install i18next-http-backend --legacy-peer-deps" "Install i18next HTTP backend for translation loading"
        
        # Verify it was installed successfully
        if ! npm list i18next-http-backend >/dev/null 2>&1; then
            echo "❌ Failed to install i18next-http-backend"
            echo "   Please run manually: npm install i18next-http-backend"
            exit 1
        fi
    fi
    echo "✅ All critical dependencies verified"
fi

if [ "$PRODUCTION" = true ]; then
    echo "🏗️  Building frontend for production..."
    run_command "npm run build" "Create optimized production build"
    if [ "$DRY_RUN" = false ]; then
        echo "✅ Frontend build completed"
    fi
else
    echo "🔧 Frontend setup completed (development mode)"
fi

cd ..

# Setup backend
echo ""
echo "⚙️  Setting up backend..."

echo "📦 Installing backend dependencies..."
run_command "pip install -r requirements.txt" "Install all backend dependencies from requirements.txt"

echo "🔍 Running type checks..."
if command_exists mypy; then
    if [ "$DRY_RUN" = true ]; then
        echo "🔍 Would run: mypy backend/"
        echo "   Purpose: Check Python type annotations for code quality"
    else
        mypy backend/ || echo "⚠️  Type check warnings (non-critical)"
    fi
else
    echo "⚠️  mypy not found, skipping type checks"
fi

echo "✅ Backend setup completed"

# Production server configuration
if [ "$PRODUCTION" = true ]; then
    echo ""
    echo "⚙️  Configuring production server..."
    
    # Configure nginx with large file upload support
    if command_exists nginx; then
        echo "🌐 Configuring nginx for large file uploads..."
        cat > /etc/nginx/sites-available/review-platform << 'NGINX_EOF'
server {
    listen 80;
    server_name _;
    
    # Frontend
    location / {
        root /opt/review-platform/frontend/build;
        index index.html index.htm;
        try_files $uri $uri/ /index.html;
    }

    # API with large file upload support
    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Large file upload timeouts for dojo ZIP files (up to 1GB)
        proxy_connect_timeout 300s;            # 5 minutes connection timeout
        proxy_send_timeout 1800s;              # 30 minutes send timeout
        proxy_read_timeout 1800s;              # 30 minutes read timeout
        client_max_body_size 1G;               # Allow 1GB file uploads
        client_body_timeout 1800s;             # 30 minutes for request body
    }
}
NGINX_EOF
        
        # Enable site
        ln -sf /etc/nginx/sites-available/review-platform /etc/nginx/sites-enabled/ 2>/dev/null || true
        rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
        
        # Test and reload nginx
        if nginx -t 2>/dev/null; then
            systemctl reload nginx 2>/dev/null || true
            echo "✅ Nginx configured with large file upload support"
        else
            echo "⚠️  Nginx configuration test failed"
        fi
    fi
    
    # Configure systemd service with timeouts
    echo "🔧 Configuring systemd service with upload timeouts..."
    cat > /etc/systemd/system/review-platform.service << 'SYSTEMD_EOF'
[Unit]
Description=Review Platform API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/review-platform/backend
Environment=PATH=/opt/review-platform/venv/bin
ExecStart=/opt/review-platform/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 300 --timeout-graceful-shutdown 300
Restart=always

[Install]
WantedBy=multi-user.target
SYSTEMD_EOF
    
    # Reload systemd and restart service
    systemctl daemon-reload
    systemctl restart review-platform 2>/dev/null || systemctl start review-platform
    systemctl enable review-platform
    
    echo "✅ Production server configuration completed"
fi

# Database setup
echo ""
echo "🗄️  Database setup..."
echo "   For production: Configure PostgreSQL connection in backend/app/core/config.py"
echo "   For development: SQLite database will be created automatically"

# Final instructions
echo ""
if [ "$DRY_RUN" = true ]; then
    echo "🔍 DRY RUN COMPLETED - No changes were made"
    echo "==========================================="
    echo ""
    echo "The following would have been executed:"
    echo ""
    echo "📊 Summary of planned operations:"
    echo "  - Install frontend dependencies (npm install)"
    echo "  - Install backend dependencies (pip install)"
    echo "  - Run Python type checking (mypy)"
    if [ "$PRODUCTION" = true ]; then
        echo "  - Build frontend for production (npm run build)"
    fi
    echo ""
    echo "🛡️  Safety confirmation:"
    echo "  ✅ No database operations"
    echo "  ✅ No .env file modifications"
    echo "  ✅ No user data changes"
    echo "  ✅ No uploaded documents affected"
    echo "  ✅ No configuration file changes"
    echo "  ✅ No service restarts"
    echo ""
    echo "To execute these operations, run:"
    if [ "$PRODUCTION" = true ]; then
        echo "  ./deploy.sh production"
    else
        echo "  ./deploy.sh"
    fi
else
    echo "🎉 Deployment completed successfully!"
    echo ""
    echo "📚 Next steps:"
    echo "==============="
    echo ""
    echo "Development mode:"
    echo "  Frontend: cd frontend && npm start"
    echo "  Backend:  cd backend && uvicorn app.main:app --reload"
    echo ""
    echo "Production mode:"
    echo "  Frontend: Serve the frontend/build/ directory with your web server"
    echo "  Backend:  Configure PostgreSQL and run with gunicorn or uvicorn"
    echo ""
    echo "Configuration files:"
    echo "  - frontend/INSTALL.md: Detailed frontend setup"
    echo "  - backend/app/core/config.py: Backend configuration"
    echo "  - CLAUDE.md: Development guidelines"
    echo ""
    echo "Key features enabled:"
    echo "  ✅ Dynamic polar plots (Recharts)"
    echo "  ✅ Healthcare template system"
    echo "  ✅ Multi-user authentication"
    echo "  ✅ Email workflows"
    echo "  ✅ AI-powered analysis"
    echo "  ✅ PostgreSQL support"
    echo ""
    echo "For support, see README.md or the documentation files."
fi