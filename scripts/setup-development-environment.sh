#!/bin/bash

# Setup Development Environment Script
# This script sets up the development environment by:
# 1. Exporting production database schema
# 2. Setting up development PostgreSQL
# 3. Importing schema to development
# 4. Mounting shared filesystems
# 5. Configuring development services

set -e

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

# Server IP addresses from screenshot
PRODUCTION_CPU="65.108.32.168"
PRODUCTION_GPU="135.181.63.133" 
DEVELOPMENT_CPU="65.108.32.143"
DEVELOPMENT_GPU="135.181.71.17"

# Database configuration
PROD_DB_NAME="review-platform"
DEV_DB_NAME="review_dev"
STAGING_DB_NAME="review_staging"

# Default values
DRY_RUN=false
EXPORT_SCHEMA=true
SETUP_DEV_DB=true
MOUNT_FILESYSTEM=true
SKIP_PROD_EXPORT=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-schema-export)
            EXPORT_SCHEMA=false
            shift
            ;;
        --no-dev-db)
            SETUP_DEV_DB=false
            shift
            ;;
        --no-mount)
            MOUNT_FILESYSTEM=false
            shift
            ;;
        --skip-prod-export)
            SKIP_PROD_EXPORT=true
            shift
            ;;
        --help|-h)
            cat << 'EOF'
Setup Development Environment Script

This script sets up the complete development environment by:
1. Exporting production database schema from Datacrunch production server
2. Setting up PostgreSQL on development server
3. Creating development and staging databases
4. Importing production schema to development
5. Mounting shared NFS filesystems
6. Configuring development services

Usage: ./setup-development-environment.sh [options]

Options:
  --dry-run              Show what would be done without executing
  --no-schema-export     Skip production schema export
  --no-dev-db           Skip development database setup
  --no-mount            Skip filesystem mounting
  --skip-prod-export    Use existing schema export file
  --help, -h            Show this help message

Server Configuration:
  Production CPU: 65.108.32.168
  Production GPU: 135.181.63.133
  Development CPU: 65.108.32.143
  Development GPU: 135.181.71.17

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

echo "🚀 Setting up Development Environment"
echo "====================================="
echo "Production CPU:  $PRODUCTION_CPU"
echo "Production GPU:  $PRODUCTION_GPU"
echo "Development CPU: $DEVELOPMENT_CPU"
echo "Development GPU: $DEVELOPMENT_GPU"
echo ""

if [ "$DRY_RUN" = true ]; then
    log_warning "DRY RUN MODE - No changes will be made"
    echo ""
fi

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

# Function to run command on remote server
run_remote_command() {
    local server="$1"
    local cmd="$2" 
    local description="$3"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would run on $server: $cmd"
        if [ -n "$description" ]; then
            echo "   Purpose: $description"
        fi
    else
        log_info "Running on $server: $cmd"
        ssh -o StrictHostKeyChecking=no root@"$server" "$cmd"
    fi
}

# Step 1: Export production database schema
export_production_schema() {
    if [ "$EXPORT_SCHEMA" = false ]; then
        log_info "Skipping production schema export"
        return
    fi
    
    if [ "$SKIP_PROD_EXPORT" = true ] && [ -f "production_schema.sql" ]; then
        log_info "Using existing production schema export"
        return
    fi
    
    log_info "Exporting production database schema from $PRODUCTION_CPU..."
    
    # Create schemas directory
    run_command "mkdir -p schemas" "Create schemas directory"
    
    # Export schema from production
    local export_cmd="pg_dump --schema-only --no-owner --no-privileges postgresql://review_user:review_password@localhost:5432/$PROD_DB_NAME"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would export schema from production server"
        log_info "Command on production: $export_cmd > /tmp/production_schema.sql"
        log_info "Would copy schema file to local machine"
    else
        # Export schema on production server
        run_remote_command "$PRODUCTION_CPU" "$export_cmd > /tmp/production_schema.sql" "Export production database schema"
        
        # Copy schema file to local machine
        log_info "Copying schema file from production..."
        scp -o StrictHostKeyChecking=no root@"$PRODUCTION_CPU":/tmp/production_schema.sql schemas/production_schema.sql
        
        # Clean up on production server
        run_remote_command "$PRODUCTION_CPU" "rm -f /tmp/production_schema.sql" "Clean up temporary schema file"
        
        log_success "Production schema exported to schemas/production_schema.sql"
    fi
}

# Step 2: Setup development PostgreSQL
setup_development_database() {
    if [ "$SETUP_DEV_DB" = false ]; then
        log_info "Skipping development database setup"
        return
    fi
    
    log_info "Setting up PostgreSQL on development server $DEVELOPMENT_CPU..."
    
    # Install PostgreSQL on development server
    local install_cmd="apt update && apt install -y postgresql postgresql-contrib"
    run_remote_command "$DEVELOPMENT_CPU" "$install_cmd" "Install PostgreSQL on development server"
    
    # Start PostgreSQL service
    run_remote_command "$DEVELOPMENT_CPU" "systemctl start postgresql && systemctl enable postgresql" "Start and enable PostgreSQL"
    
    # Create development databases and users
    local setup_db_cmd="sudo -u postgres psql -c \"
        -- Create development database and user
        CREATE DATABASE $DEV_DB_NAME;
        CREATE USER dev_user WITH PASSWORD 'dev_password';
        GRANT ALL PRIVILEGES ON DATABASE $DEV_DB_NAME TO dev_user;
        
        -- Create staging database and user  
        CREATE DATABASE $STAGING_DB_NAME;
        CREATE USER staging_user WITH PASSWORD 'staging_password';
        GRANT ALL PRIVILEGES ON DATABASE $STAGING_DB_NAME TO staging_user;
        
        -- Allow connections
        ALTER USER dev_user CREATEDB;
        ALTER USER staging_user CREATEDB;
    \""
    
    run_remote_command "$DEVELOPMENT_CPU" "$setup_db_cmd" "Create development and staging databases"
    
    # Configure PostgreSQL for remote connections
    local config_cmd="
        echo \"listen_addresses = '*'\" >> /etc/postgresql/*/main/postgresql.conf &&
        echo \"host all all 0.0.0.0/0 md5\" >> /etc/postgresql/*/main/pg_hba.conf &&
        systemctl restart postgresql
    "
    run_remote_command "$DEVELOPMENT_CPU" "$config_cmd" "Configure PostgreSQL for remote connections"
    
    log_success "Development PostgreSQL setup completed"
}

# Step 3: Import schema to development databases
import_schema_to_development() {
    if [ ! -f "schemas/production_schema.sql" ] && [ "$DRY_RUN" = false ]; then
        log_error "Production schema file not found. Run with schema export first."
        return 1
    fi
    
    log_info "Importing production schema to development databases..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would copy schema file to development server"
        log_info "Would import schema to development database"
        log_info "Would import schema to staging database"
    else
        # Copy schema file to development server
        scp -o StrictHostKeyChecking=no schemas/production_schema.sql root@"$DEVELOPMENT_CPU":/tmp/
        
        # Import to development database
        local import_dev_cmd="PGPASSWORD=dev_password psql -h localhost -U dev_user -d $DEV_DB_NAME -f /tmp/production_schema.sql"
        run_remote_command "$DEVELOPMENT_CPU" "$import_dev_cmd" "Import schema to development database"
        
        # Import to staging database
        local import_staging_cmd="PGPASSWORD=staging_password psql -h localhost -U staging_user -d $STAGING_DB_NAME -f /tmp/production_schema.sql"
        run_remote_command "$DEVELOPMENT_CPU" "$import_staging_cmd" "Import schema to staging database"
        
        # Clean up
        run_remote_command "$DEVELOPMENT_CPU" "rm -f /tmp/production_schema.sql" "Clean up schema file"
        
        log_success "Schema imported to both development and staging databases"
    fi
}

# Step 4: Mount shared filesystems
mount_shared_filesystems() {
    if [ "$MOUNT_FILESYSTEM" = false ]; then
        log_info "Skipping filesystem mounting"
        return
    fi
    
    log_info "Setting up shared filesystem mounts..."
    
    # Commands for mounting NFS
    local mount_cmd="
        mkdir -p /mnt/dev-CPU-GPU &&
        mkdir -p /mnt/shared-production &&
        # Mount development shared filesystem
        mount -t nfs development-nfs-server:/path/to/shared /mnt/dev-CPU-GPU &&
        # Mount production shared filesystem (read-only for safety)
        mount -t nfs -o ro production-nfs-server:/path/to/shared /mnt/shared-production
    "
    
    # Setup on development CPU
    run_remote_command "$DEVELOPMENT_CPU" "$mount_cmd" "Mount shared filesystems on development CPU"
    
    # Setup on development GPU
    run_remote_command "$DEVELOPMENT_GPU" "$mount_cmd" "Mount shared filesystems on development GPU"
    
    # Add to fstab for persistence
    local fstab_cmd="
        echo 'development-nfs-server:/path/to/shared /mnt/dev-CPU-GPU nfs defaults 0 0' >> /etc/fstab &&
        echo 'production-nfs-server:/path/to/shared /mnt/shared-production nfs ro,defaults 0 0' >> /etc/fstab
    "
    
    run_remote_command "$DEVELOPMENT_CPU" "$fstab_cmd" "Add mounts to fstab on development CPU"
    run_remote_command "$DEVELOPMENT_GPU" "$fstab_cmd" "Add mounts to fstab on development GPU"
    
    log_success "Shared filesystem mounts configured"
}

# Step 5: Copy project to development server
copy_project_to_development() {
    log_info "Copying project files to development server..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would copy project files to development server"
        log_info "Would set up project directory structure"
    else
        # Create project directory on development server
        run_remote_command "$DEVELOPMENT_CPU" "mkdir -p /opt/review-platform-dev" "Create development project directory"
        
        # Copy project files (excluding .git and other unnecessary files)
        log_info "Copying project files..."
        rsync -av --exclude='.git' --exclude='node_modules' --exclude='__pycache__' --exclude='*.pyc' \
            ./ root@"$DEVELOPMENT_CPU":/opt/review-platform-dev/
        
        # Set up Python virtual environment
        run_remote_command "$DEVELOPMENT_CPU" "cd /opt/review-platform-dev && python3 -m venv venv" "Create Python virtual environment"
        
        # Install Python dependencies
        run_remote_command "$DEVELOPMENT_CPU" "cd /opt/review-platform-dev && ./venv/bin/pip install -r requirements.txt" "Install Python dependencies"
        
        log_success "Project files copied and dependencies installed"
    fi
}

# Step 6: Verify setup
verify_setup() {
    log_info "Verifying development environment setup..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would verify database connections"
        log_info "Would verify filesystem mounts"
        log_info "Would verify GPU connectivity"
    else
        # Test database connections
        local test_dev_db="PGPASSWORD=dev_password psql -h localhost -U dev_user -d $DEV_DB_NAME -c 'SELECT 1;'"
        run_remote_command "$DEVELOPMENT_CPU" "$test_dev_db" "Test development database connection"
        
        local test_staging_db="PGPASSWORD=staging_password psql -h localhost -U staging_user -d $STAGING_DB_NAME -c 'SELECT 1;'"  
        run_remote_command "$DEVELOPMENT_CPU" "$test_staging_db" "Test staging database connection"
        
        # Test filesystem mounts
        run_remote_command "$DEVELOPMENT_CPU" "ls -la /mnt/dev-CPU-GPU" "Verify development filesystem mount"
        run_remote_command "$DEVELOPMENT_CPU" "ls -la /mnt/shared-production" "Verify production filesystem mount"
        
        # Test GPU connectivity
        run_remote_command "$DEVELOPMENT_CPU" "curl -f http://$DEVELOPMENT_GPU:8001/api/health || echo 'GPU not ready yet'" "Test GPU connectivity"
        
        log_success "Development environment verification completed"
    fi
}

# Main execution
main() {
    log_info "Starting development environment setup..."
    
    # Step 1: Export production schema
    export_production_schema
    
    # Step 2: Setup development PostgreSQL
    setup_development_database
    
    # Step 3: Import schema
    import_schema_to_development
    
    # Step 4: Mount filesystems
    mount_shared_filesystems
    
    # Step 5: Copy project
    copy_project_to_development
    
    # Step 6: Verify setup
    verify_setup
    
    if [ "$DRY_RUN" = true ]; then
        log_info "DRY RUN COMPLETED - No changes were made"
    else
        log_success "🎉 Development environment setup completed!"
        echo ""
        echo "📚 Next Steps:"
        echo "=============="
        echo "1. SSH to development server: ssh root@$DEVELOPMENT_CPU"
        echo "2. Start development backend: cd /opt/review-platform-dev && ./venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
        echo "3. Start development frontend: cd /opt/review-platform-dev/frontend && npm start"
        echo "4. Access development environment: http://$DEVELOPMENT_CPU:3000"
        echo ""
        echo "Database Connections:"
        echo "Development: postgresql://dev_user:dev_password@$DEVELOPMENT_CPU:5432/$DEV_DB_NAME"
        echo "Staging:     postgresql://staging_user:staging_password@$DEVELOPMENT_CPU:5432/$STAGING_DB_NAME"
    fi
}

# Run main function
main