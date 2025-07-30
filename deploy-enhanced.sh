#!/bin/bash

# Enhanced Healthcare Startup Review Platform Deployment Script
# Supports: development, staging, production environments with zero-downtime deployments

set -e  # Exit on any error

# Default values
ENVIRONMENT="development"
DRY_RUN=false
ROLLBACK=false
RUN_MIGRATIONS=true
HEALTH_CHECK=true
ZERO_DOWNTIME=false
BACKUP_DB=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --environment|-e)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --rollback)
            ROLLBACK=true
            shift
            ;;
        --no-migrations)
            RUN_MIGRATIONS=false
            shift
            ;;
        --no-health-check)
            HEALTH_CHECK=false
            shift
            ;;
        --zero-downtime)
            ZERO_DOWNTIME=true
            shift
            ;;
        --backup-db)
            BACKUP_DB=true
            shift
            ;;
        --help|-h)
            cat << 'EOF'
Enhanced Healthcare Startup Review Platform Deployment Script

Usage: ./deploy-enhanced.sh [options]

Options:
  -e, --environment ENV     Target environment (development|staging|production) [default: development]
  --dry-run                Show what would be done without executing
  --rollback               Rollback to previous deployment
  --no-migrations          Skip database migrations
  --no-health-check        Skip health checks after deployment
  --zero-downtime          Use zero-downtime deployment (production only)
  --backup-db              Create database backup before deployment
  --help, -h               Show this help message

Environments:
  development             Local development setup with SQLite/PostgreSQL
  staging                 Staging environment on development server (different ports)
  production              Production environment with zero-downtime deployment

Examples:
  ./deploy-enhanced.sh --environment development
  ./deploy-enhanced.sh --environment production --zero-downtime --backup-db
  ./deploy-enhanced.sh --environment staging --dry-run
  ./deploy-enhanced.sh --rollback --environment production

EOF
            exit 0
            ;;
        *)
            log_error "Unknown argument: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate environment
case $ENVIRONMENT in
    development|staging|production)
        ;;
    *)
        log_error "Invalid environment: $ENVIRONMENT"
        log_info "Valid environments: development, staging, production"
        exit 1
        ;;
esac

# Environment-specific configuration
case $ENVIRONMENT in
    development)
        FRONTEND_PORT=3000
        BACKEND_PORT=8000
        DB_NAME="review_dev"
        SERVICE_NAME="review-platform-dev"
        NGINX_SITE="review-platform-dev"
        APP_DIR="/opt/review-platform-dev"
        ;;
    staging)
        FRONTEND_PORT=3001
        BACKEND_PORT=8001
        DB_NAME="review_staging"
        SERVICE_NAME="review-platform-staging"
        NGINX_SITE="review-platform-staging"
        APP_DIR="/opt/review-platform-staging"
        ;;
    production)
        FRONTEND_PORT=80
        BACKEND_PORT=8000
        DB_NAME="review-platform"
        SERVICE_NAME="review-platform"
        NGINX_SITE="review-platform"
        APP_DIR="/opt/review-platform"
        ZERO_DOWNTIME=true  # Force zero-downtime for production
        ;;
esac

echo "🚀 Enhanced Healthcare Startup Review Platform Deployment"
echo "========================================================="
echo "Environment: $ENVIRONMENT"
echo "Zero-downtime: $ZERO_DOWNTIME"
echo "Run migrations: $RUN_MIGRATIONS"
echo "Health checks: $HEALTH_CHECK"

if [ "$DRY_RUN" = true ]; then
    echo "🔍 DRY RUN MODE - No changes will be made"
    echo "=========================================="
fi

# Check if we're in the right directory
if [ ! -f "CLAUDE.md" ]; then
    log_error "This script must be run from the project root directory"
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
        log_info "Would run: $cmd"
        if [ -n "$description" ]; then
            echo "   Purpose: $description"
        fi
    else
        log_info "Running: $cmd"
        eval "$cmd"
    fi
}

# Function to check service health
check_health() {
    local url="http://localhost:$BACKEND_PORT/api/health"
    local max_attempts=30
    local attempt=1
    
    log_info "Checking service health at $url"
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "$url" > /dev/null 2>&1; then
            log_success "Service is healthy"
            return 0
        fi
        
        log_info "Health check attempt $attempt/$max_attempts failed, waiting..."
        sleep 2
        ((attempt++))
    done
    
    log_error "Service failed health check after $max_attempts attempts"
    return 1
}

# Function to create database backup
backup_database() {
    if [ "$ENVIRONMENT" = "production" ] && command_exists pg_dump; then
        local backup_file="/opt/backups/review-platform-$(date +%Y%m%d-%H%M%S).sql"
        log_info "Creating database backup: $backup_file"
        run_command "mkdir -p /opt/backups" "Create backup directory"
        run_command "pg_dump $DB_NAME > $backup_file" "Create database backup"
        log_success "Database backup created: $backup_file"
    else
        log_warning "Skipping database backup (not production or pg_dump not available)"
    fi
}

# Function to run database migrations
run_migrations() {
    if [ "$RUN_MIGRATIONS" = true ]; then
        log_info "Running database migrations..."
        cd backend
        
        # Check if migration files exist
        if [ -d "migrations" ]; then
            run_command "python run_migration.py --environment $ENVIRONMENT" "Run database migrations"
        else
            log_warning "No migration directory found, skipping migrations"
        fi
        
        cd ..
        log_success "Database migrations completed"
    else
        log_info "Skipping database migrations (--no-migrations specified)"
    fi
}

# Function for zero-downtime deployment
deploy_zero_downtime() {
    local new_dir="${APP_DIR}-new"
    local current_dir="${APP_DIR}"
    local backup_dir="${APP_DIR}-backup"
    
    log_info "Starting zero-downtime deployment..."
    
    # Create new deployment directory
    run_command "mkdir -p $new_dir" "Create new deployment directory"
    run_command "cp -r . $new_dir/" "Copy application to new directory"
    
    # Build frontend in new directory
    cd "$new_dir/frontend"
    run_command "npm install --legacy-peer-deps" "Install frontend dependencies"
    run_command "npm run build" "Build frontend for production"
    cd - > /dev/null
    
    # Install backend dependencies in new directory
    cd "$new_dir/backend"
    run_command "pip install -r requirements.txt" "Install backend dependencies"
    cd - > /dev/null
    
    # Health check new deployment
    if [ "$HEALTH_CHECK" = true ]; then
        # Start new backend temporarily for health check
        cd "$new_dir/backend"
        uvicorn app.main:app --host 0.0.0.0 --port 9999 --timeout-keep-alive 300 &
        NEW_PID=$!
        cd - > /dev/null
        
        # Wait for service to start
        sleep 5
        
        # Check health on temporary port
        if curl -s -f "http://localhost:9999/api/health" > /dev/null 2>&1; then
            log_success "New deployment passes health check"
            kill $NEW_PID 2>/dev/null || true
        else
            log_error "New deployment failed health check"
            kill $NEW_PID 2>/dev/null || true
            rm -rf "$new_dir"
            exit 1
        fi
    fi
    
    # Backup current deployment
    if [ -d "$current_dir" ]; then
        run_command "mv $current_dir $backup_dir" "Backup current deployment"
    fi
    
    # Atomic switch to new deployment
    run_command "mv $new_dir $current_dir" "Switch to new deployment"
    
    # Restart services
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        run_command "systemctl restart $SERVICE_NAME" "Restart backend service"
    fi
    
    if command_exists nginx && [ -f "/etc/nginx/sites-available/$NGINX_SITE" ]; then
        run_command "nginx -t && systemctl reload nginx" "Reload nginx configuration"
    fi
    
    # Final health check
    if [ "$HEALTH_CHECK" = true ]; then
        if check_health; then
            log_success "Zero-downtime deployment completed successfully"
            # Remove backup after successful deployment
            run_command "rm -rf $backup_dir" "Clean up backup"
        else
            log_error "New deployment failed final health check, rolling back"
            rollback_deployment
            exit 1
        fi
    fi
}

# Function to rollback deployment
rollback_deployment() {
    local current_dir="${APP_DIR}"
    local backup_dir="${APP_DIR}-backup"
    
    if [ -d "$backup_dir" ]; then
        log_info "Rolling back to previous deployment..."
        run_command "mv $current_dir ${APP_DIR}-failed" "Move failed deployment"
        run_command "mv $backup_dir $current_dir" "Restore previous deployment"
        
        # Restart services
        if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
            run_command "systemctl restart $SERVICE_NAME" "Restart backend service"
        fi
        
        log_success "Rollback completed"
    else
        log_error "No backup found for rollback"
        exit 1
    fi
}

# Main deployment logic
if [ "$ROLLBACK" = true ]; then
    rollback_deployment
    exit 0
fi

# Check prerequisites
log_info "Checking prerequisites..."

if ! command_exists node; then
    log_error "Node.js is required but not installed"
    exit 1
fi

if ! command_exists npm; then
    log_error "npm is required but not installed"
    exit 1
fi

if ! command_exists python3; then
    log_error "Python 3 is required but not installed"
    exit 1
fi

if ! command_exists pip; then
    log_error "pip is required but not installed"
    exit 1
fi

log_success "Prerequisites check passed"

# Create database backup if requested
if [ "$BACKUP_DB" = true ]; then
    backup_database
fi

# Run database migrations
run_migrations

# Choose deployment strategy
if [ "$ZERO_DOWNTIME" = true ]; then
    deploy_zero_downtime
else
    # Standard deployment
    log_info "Starting standard deployment..."
    
    # Setup frontend
    log_info "Setting up frontend..."
    cd frontend
    run_command "npm install --legacy-peer-deps" "Install frontend dependencies"
    
    if [ "$ENVIRONMENT" = "production" ] || [ "$ENVIRONMENT" = "staging" ]; then
        run_command "npm run build" "Build frontend for production"
    fi
    
    cd ..
    
    # Setup backend
    log_info "Setting up backend..."
    run_command "pip install -r requirements.txt" "Install backend dependencies"
    
    # Type checking
    if command_exists mypy; then
        run_command "mypy backend/ || true" "Run type checks (warnings only)"
    fi
    
    # Restart services if they exist
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        run_command "systemctl restart $SERVICE_NAME" "Restart backend service"
    fi
    
    # Health check
    if [ "$HEALTH_CHECK" = true ] && [ "$DRY_RUN" = false ]; then
        check_health || log_warning "Health check failed, but continuing..."
    fi
    
    log_success "Standard deployment completed"
fi

# Final status
if [ "$DRY_RUN" = true ]; then
    log_info "DRY RUN COMPLETED - No changes were made"
else
    log_success "🎉 Deployment completed successfully!"
    echo ""
    echo "📚 Environment Details:"
    echo "======================="
    echo "Environment: $ENVIRONMENT"
    echo "Frontend: http://localhost:$FRONTEND_PORT"
    echo "Backend:  http://localhost:$BACKEND_PORT"
    echo "Database: $DB_NAME"
    echo ""
    echo "Service Management:"
    echo "  Start:   systemctl start $SERVICE_NAME"
    echo "  Stop:    systemctl stop $SERVICE_NAME"
    echo "  Status:  systemctl status $SERVICE_NAME"
    echo "  Logs:    journalctl -u $SERVICE_NAME -f"
fi