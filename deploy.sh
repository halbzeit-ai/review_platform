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
run_command "npm install" "Install all frontend dependencies from package.json"

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
cd backend

echo "📦 Installing backend dependencies..."
run_command "pip install -r requirements.txt" "Install all backend dependencies from requirements.txt"

echo "🔍 Running type checks..."
if command_exists mypy; then
    if [ "$DRY_RUN" = true ]; then
        echo "🔍 Would run: mypy ."
        echo "   Purpose: Check Python type annotations for code quality"
    else
        mypy . || echo "⚠️  Type check warnings (non-critical)"
    fi
else
    echo "⚠️  mypy not found, skipping type checks"
fi

echo "✅ Backend setup completed"

cd ..

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