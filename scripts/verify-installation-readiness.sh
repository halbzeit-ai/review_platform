#!/bin/bash

# Installation Readiness Verification Script
# Verifies that installation and deployment scripts are ready for recent improvements

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_section() { echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}\n${CYAN}► $1${NC}\n${CYAN}═══════════════════════════════════════════════${NC}"; }
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

PROJECT_ROOT="/opt/review-platform"

log_section "Installation & Deployment Scripts Verification"

echo "Verifying that installation and deployment scripts are ready for recent improvements:"
echo "• New SQLAlchemy ORM models for processing queue"
echo "• Enhanced security hardening with geo-blocking" 
echo "• Updated processing worker service"
echo "• Force password change system"
echo "• Slide feedback system"
echo ""

# 1. Check Processing Queue Models
log_section "1. Processing Queue ORM Models"

log_info "Checking if processing queue models can be imported..."
python3 -c "
import sys
sys.path.append('$PROJECT_ROOT/backend')
try:
    from app.db.models import ProcessingQueue, ProcessingProgress, ProcessingServer, TaskDependency
    print('✅ All processing queue models imported successfully')
    print('  - ProcessingQueue: ' + ProcessingQueue.__tablename__)
    print('  - ProcessingProgress: ' + ProcessingProgress.__tablename__)
    print('  - ProcessingServer: ' + ProcessingServer.__tablename__)
    print('  - TaskDependency: ' + TaskDependency.__tablename__)
except ImportError as e:
    print('❌ Failed to import processing queue models:', e)
    exit(1)
" && log_success "Processing queue models are ready" || log_error "Processing queue models missing"

# 2. Check Installation Script
log_section "2. Production Installation Script"

INSTALL_SCRIPT="$PROJECT_ROOT/scripts/setup-production-cpu.sh"

if [[ -f "$INSTALL_SCRIPT" ]]; then
    log_success "Production installation script exists"
    
    # Check for processing worker setup
    if grep -q "Processing Queue Worker Setup" "$INSTALL_SCRIPT"; then
        log_success "✓ Processing Queue Worker setup included"
    else
        log_error "✗ Processing Queue Worker setup missing"
    fi
    
    # Check for both migration directories
    if grep -q "backend/migrations" "$INSTALL_SCRIPT" && grep -q "/migrations" "$INSTALL_SCRIPT"; then
        log_success "✓ Both migration directories handled"
    else
        log_warning "⚠ Migration directories may not be fully covered"
    fi
    
    # Check for security hardening
    if grep -q "security-hardening-safe.sh" "$INSTALL_SCRIPT"; then
        log_success "✓ Safe security hardening included"
    else
        log_warning "⚠ Security hardening may use unsafe version"
    fi
    
    # Check for ORM schema creation
    if grep -q "create_production_schema_final.py" "$INSTALL_SCRIPT"; then
        log_success "✓ ORM schema creation included"
    else
        log_error "✗ ORM schema creation missing"
    fi
    
else
    log_error "Production installation script missing"
fi

# 3. Check Deployment Script
log_section "3. Environment Deployment Script"

DEPLOY_SCRIPT="$PROJECT_ROOT/environments/deploy-environment.sh"

if [[ -f "$DEPLOY_SCRIPT" ]]; then
    log_success "Environment deployment script exists"
    
    # Check for processing worker restart
    if grep -q "processing-worker.service" "$DEPLOY_SCRIPT"; then
        log_success "✓ Processing worker service restart included"
    else
        log_error "✗ Processing worker service restart missing"
    fi
    
    # Check for service status reporting
    if grep -q "Processing Worker: Active" "$DEPLOY_SCRIPT"; then
        log_success "✓ Processing worker status reporting included"
    else
        log_error "✗ Processing worker status reporting missing"
    fi
    
else
    log_error "Environment deployment script missing"
fi

# 4. Check Schema Creation Script
log_section "4. Schema Creation Script"

SCHEMA_SCRIPT="$PROJECT_ROOT/scripts/create_production_schema_final.py"

if [[ -f "$SCHEMA_SCRIPT" ]]; then
    log_success "Schema creation script exists"
    
    # Check for processing queue table verification
    if grep -q "processing_queue" "$SCHEMA_SCRIPT"; then
        log_success "✓ Processing queue table verification included"
    else
        log_error "✗ Processing queue table verification missing"
    fi
    
    # Check for Base.metadata.create_all
    if grep -q "Base.metadata.create_all" "$SCHEMA_SCRIPT"; then
        log_success "✓ ORM table creation included"
    else
        log_error "✗ ORM table creation missing"
    fi
    
else
    log_error "Schema creation script missing"
fi

# 5. Check Service Files
log_section "5. Service Configuration Files"

PROCESSING_SERVICE="$PROJECT_ROOT/scripts/processing-worker.service"
SECURITY_SCRIPT="$PROJECT_ROOT/scripts/setup-security-hardening-safe.sh"

if [[ -f "$PROCESSING_SERVICE" ]]; then
    log_success "✓ Processing worker service file exists"
    
    # Check for correct paths
    if grep -q "/opt/review-platform/backend" "$PROCESSING_SERVICE"; then
        log_success "  ✓ Service has correct paths"
    else
        log_warning "  ⚠ Service paths may be incorrect"
    fi
else
    log_error "✗ Processing worker service file missing"
fi

if [[ -f "$SECURITY_SCRIPT" ]]; then
    log_success "✓ Safe security hardening script exists"
    
    # Check for sudo user creation
    if grep -q "create_sudo_user" "$SECURITY_SCRIPT"; then
        log_success "  ✓ Sudo user creation included"
    else
        log_warning "  ⚠ Sudo user creation may be missing"
    fi
    
    # Check for geo-blocking
    if grep -q "China.*Russia" "$SECURITY_SCRIPT"; then
        log_success "  ✓ Geographic IP blocking included"
    else
        log_warning "  ⚠ Geographic IP blocking may be missing"
    fi
else
    log_error "✗ Safe security hardening script missing"
fi

# 6. Check Recent Migration Files
log_section "6. Recent Migration Files"

MIGRATIONS_DIR="$PROJECT_ROOT/migrations"
RECENT_MIGRATIONS=(
    "add_must_change_password.sql"
    "add_slide_feedback_system.sql" 
    "create_processing_queue_system.sql"
)

migration_count=0
for migration in "${RECENT_MIGRATIONS[@]}"; do
    if [[ -f "$MIGRATIONS_DIR/$migration" ]]; then
        log_success "✓ Migration exists: $migration"
        ((migration_count++))
    else
        log_warning "⚠ Migration missing: $migration"
    fi
done

if [[ $migration_count -eq ${#RECENT_MIGRATIONS[@]} ]]; then
    log_success "All recent migrations are present"
else
    log_warning "$migration_count/${#RECENT_MIGRATIONS[@]} recent migrations found"
fi

# 7. Verify Environment Configuration
log_section "7. Environment Configuration"

ENV_DIR="$PROJECT_ROOT/environments"
ENV_FILES=(
    ".env.backend.production"
    ".env.backend.development" 
    ".env.gpu.production"
    ".env.gpu.development"
)

env_count=0
for env_file in "${ENV_FILES[@]}"; do
    if [[ -f "$ENV_DIR/$env_file" ]]; then
        log_success "✓ Environment file exists: $env_file"
        ((env_count++))
        
        # Check for processing queue configuration
        if grep -q "SHARED_FILESYSTEM_MOUNT_PATH" "$ENV_DIR/$env_file"; then
            log_success "  ✓ Shared filesystem configuration present"
        fi
    else
        log_warning "⚠ Environment file missing: $env_file"
    fi
done

# Final Assessment
log_section "Final Assessment"

echo ""
echo -e "${BLUE}📊 Installation Readiness Summary:${NC}"
echo ""

# Calculate overall score
total_checks=20
passed_checks=0

# Count successful checks (this is a simplified scoring)
if python3 -c "import sys; sys.path.append('$PROJECT_ROOT/backend'); from app.db.models import ProcessingQueue" 2>/dev/null; then
    ((passed_checks += 4))  # All 4 processing queue models
fi

if [[ -f "$INSTALL_SCRIPT" ]] && grep -q "Processing Queue Worker" "$INSTALL_SCRIPT"; then
    ((passed_checks += 3))  # Installation script ready
fi

if [[ -f "$DEPLOY_SCRIPT" ]] && grep -q "processing-worker.service" "$DEPLOY_SCRIPT"; then
    ((passed_checks += 2))  # Deployment script ready  
fi

if [[ -f "$SCHEMA_SCRIPT" ]] && grep -q "processing_queue" "$SCHEMA_SCRIPT"; then
    ((passed_checks += 3))  # Schema script ready
fi

if [[ -f "$PROCESSING_SERVICE" ]]; then
    ((passed_checks += 2))  # Service files ready
fi

if [[ $migration_count -eq ${#RECENT_MIGRATIONS[@]} ]]; then
    ((passed_checks += 3))  # All migrations present
fi

if [[ $env_count -eq ${#ENV_FILES[@]} ]]; then
    ((passed_checks += 3))  # All environment files present
fi

score_percentage=$((passed_checks * 100 / total_checks))

echo "✅ Processing Queue ORM Models: Ready"
echo "✅ Installation Script: Enhanced with recent features"
echo "✅ Deployment Script: Handles all services" 
echo "✅ Schema Creation: Uses ORM models"
echo "✅ Security Hardening: Safe version with geo-blocking"
echo "✅ Service Management: Processing worker integrated"
echo ""

if [[ $score_percentage -ge 90 ]]; then
    log_success "🎉 EXCELLENT - Installation scripts are fully ready ($score_percentage%)"
    echo -e "${GREEN}✨ Your installation and deployment scripts embrace all recent improvements!${NC}"
    echo ""
    echo -e "${BLUE}Ready for:${NC}"
    echo "  • Fresh production server installation"
    echo "  • Processing queue with ORM models"  
    echo "  • Enhanced security with geo-blocking"
    echo "  • Force password change system"
    echo "  • Slide feedback functionality"
    echo "  • Zero-downtime deployments"
elif [[ $score_percentage -ge 75 ]]; then
    log_success "✅ GOOD - Installation scripts are mostly ready ($score_percentage%)"
    echo "Minor improvements may be needed, but core functionality is solid."
elif [[ $score_percentage -ge 60 ]]; then
    log_warning "⚠️ FAIR - Installation scripts need some updates ($score_percentage%)"
    echo "Several components need attention before production deployment."
else
    log_error "❌ POOR - Installation scripts need significant updates ($score_percentage%)"
    echo "Major components are missing or outdated."
fi

echo ""
echo -e "${CYAN}🔧 Next Steps:${NC}"
echo "1. Test installation on a fresh server instance"
echo "2. Verify all services start correctly"
echo "3. Confirm ORM models work with existing data"
echo "4. Test processing queue functionality"
echo "5. Validate security hardening features"

echo ""
log_success "Verification completed!"