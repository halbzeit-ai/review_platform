#!/bin/bash

# CI/CD Pipeline for Review Platform
# Orchestrates deployment from development through staging to production

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_SCRIPT="$PROJECT_ROOT/deploy-enhanced.sh"

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

# Default values
STAGE="development"
AUTO_PROMOTE=false
SKIP_TESTS=false
DRY_RUN=false
FORCE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --stage|-s)
            STAGE="$2"
            shift 2
            ;;
        --auto-promote)
            AUTO_PROMOTE=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            cat << 'EOF'
CI/CD Pipeline for Review Platform

Usage: ./cicd-pipeline.sh [options]

Options:
  -s, --stage STAGE        Pipeline stage (development|staging|production|full) [default: development]
  --auto-promote           Automatically promote to next stage on success
  --skip-tests             Skip automated testing
  --dry-run               Show what would be done without executing
  --force                 Force deployment even if tests fail
  --help, -h              Show this help message

Stages:
  development             Deploy to development environment
  staging                 Deploy to staging environment
  production              Deploy to production environment
  full                    Run complete pipeline: dev → staging → production

Examples:
  ./cicd-pipeline.sh --stage development
  ./cicd-pipeline.sh --stage staging --auto-promote
  ./cicd-pipeline.sh --stage full
  ./cicd-pipeline.sh --stage production --dry-run

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

# Change to project root
cd "$PROJECT_ROOT"

# Function to run tests
run_tests() {
    local environment="$1"
    
    if [ "$SKIP_TESTS" = true ]; then
        log_warning "Skipping tests (--skip-tests specified)"
        return 0
    fi
    
    log_info "Running tests for $environment environment..."
    
    # Backend tests
    if [ -f "backend/requirements.txt" ]; then
        log_info "Running backend type checks..."
        if command -v mypy >/dev/null 2>&1; then
            if [ "$DRY_RUN" = true ]; then
                log_info "Would run: mypy backend/"
            else
                cd backend
                mypy . || {
                    log_error "Backend type checks failed"
                    [ "$FORCE" = true ] || return 1
                }
                cd ..
            fi
        else
            log_warning "mypy not found, skipping type checks"
        fi
    fi
    
    # Frontend tests
    if [ -f "frontend/package.json" ]; then
        log_info "Running frontend tests..."
        if [ "$DRY_RUN" = true ]; then
            log_info "Would run: cd frontend && npm test -- --watchAll=false"
        else
            cd frontend
            if npm test -- --watchAll=false; then
                log_success "Frontend tests passed"
            else
                log_error "Frontend tests failed"
                [ "$FORCE" = true ] || return 1
            fi
            cd ..
        fi
    fi
    
    # Environment-specific health checks
    case $environment in
        staging)
            log_info "Running staging health checks..."
            if [ "$DRY_RUN" = true ]; then
                log_info "Would check: http://localhost:3001/health and http://localhost:8001/api/health"
            else
                # Wait for services to be ready
                sleep 10
                
                # Check frontend health
                if curl -s -f "http://localhost:3001/health" > /dev/null; then
                    log_success "Staging frontend health check passed"
                else
                    log_error "Staging frontend health check failed"
                    [ "$FORCE" = true ] || return 1
                fi
                
                # Check backend health
                if curl -s -f "http://localhost:8001/api/health" > /dev/null; then
                    log_success "Staging backend health check passed"
                else
                    log_error "Staging backend health check failed"
                    [ "$FORCE" = true ] || return 1
                fi
            fi
            ;;
        production)
            log_info "Running production readiness checks..."
            if [ "$DRY_RUN" = true ]; then
                log_info "Would verify production configuration and run smoke tests"
            else
                # Verify production configuration
                if [ ! -f "environments/production.env" ]; then
                    log_error "Production environment file not found"
                    return 1
                fi
                
                # Check for placeholder values in production config
                if grep -q "CHANGE-THIS" environments/production.env; then
                    log_error "Production environment contains placeholder values"
                    return 1
                fi
                
                log_success "Production readiness checks passed"
            fi
            ;;
    esac
    
    log_success "All tests and checks passed for $environment"
    return 0
}

# Function to deploy to specific environment
deploy_environment() {
    local environment="$1"
    local deploy_args=""
    
    log_info "Deploying to $environment environment..."
    
    # Build deployment arguments
    deploy_args="--environment $environment"
    
    if [ "$DRY_RUN" = true ]; then
        deploy_args="$deploy_args --dry-run"
    fi
    
    case $environment in
        staging)
            # Use Docker Compose for staging
            if [ "$DRY_RUN" = true ]; then
                log_info "Would run: docker-compose -f docker-compose.staging.yml up -d"
            else
                log_info "Starting staging environment with Docker Compose..."
                docker-compose -f docker-compose.staging.yml up -d
                
                # Wait for services to be ready
                log_info "Waiting for staging services to start..."
                sleep 30
            fi
            ;;
        production)
            deploy_args="$deploy_args --zero-downtime --backup-db"
            ;;
    esac
    
    # Run deployment script
    if [ "$DRY_RUN" = true ]; then
        log_info "Would run: $DEPLOY_SCRIPT $deploy_args"
    else
        "$DEPLOY_SCRIPT" $deploy_args
    fi
    
    log_success "$environment deployment completed"
}

# Function to promote to next stage
promote_to_next_stage() {
    local current_stage="$1"
    
    case $current_stage in
        development)
            log_info "Promoting from development to staging..."
            deploy_and_test "staging"
            ;;
        staging)
            log_info "Promoting from staging to production..."
            
            # Additional confirmation for production
            if [ "$DRY_RUN" = false ] && [ "$FORCE" = false ]; then
                read -p "🚨 Deploy to PRODUCTION? This will affect live users. (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    log_info "Production deployment cancelled by user"
                    return 0
                fi
            fi
            
            deploy_and_test "production"
            ;;
        production)
            log_info "Already at production stage"
            ;;
    esac
}

# Function to deploy and test an environment
deploy_and_test() {
    local environment="$1"
    
    # Deploy
    deploy_environment "$environment"
    
    # Test
    if run_tests "$environment"; then
        log_success "$environment deployment and testing successful"
        
        # Auto-promote if requested
        if [ "$AUTO_PROMOTE" = true ]; then
            promote_to_next_stage "$environment"
        fi
    else
        log_error "$environment deployment failed tests"
        
        # Rollback on failure (except for development)
        if [ "$environment" != "development" ] && [ "$DRY_RUN" = false ]; then
            log_warning "Rolling back $environment deployment..."
            "$DEPLOY_SCRIPT" --environment "$environment" --rollback
        fi
        
        return 1
    fi
}

# Main pipeline logic
main() {
    echo "🚀 CI/CD Pipeline for Review Platform"
    echo "======================================"
    echo "Stage: $STAGE"
    echo "Auto-promote: $AUTO_PROMOTE"
    echo "Skip tests: $SKIP_TESTS"
    echo "Dry run: $DRY_RUN"
    echo ""
    
    case $STAGE in
        development)
            deploy_and_test "development"
            ;;
        staging)
            deploy_and_test "staging"
            ;;
        production)
            deploy_and_test "production"
            ;;
        full)
            log_info "Running full pipeline: development → staging → production"
            
            # Development
            if deploy_and_test "development"; then
                log_success "Development stage completed"
                
                # Staging
                if deploy_and_test "staging"; then
                    log_success "Staging stage completed"
                    
                    # Production (with confirmation)
                    if [ "$DRY_RUN" = false ] && [ "$FORCE" = false ]; then
                        read -p "🚨 Continue to PRODUCTION? This will affect live users. (y/N): " -n 1 -r
                        echo
                        if [[ $REPLY =~ ^[Yy]$ ]]; then
                            deploy_and_test "production"
                        else
                            log_info "Full pipeline stopped before production"
                        fi
                    else
                        deploy_and_test "production"
                    fi
                else
                    log_error "Staging deployment failed, stopping pipeline"
                    exit 1
                fi
            else
                log_error "Development deployment failed, stopping pipeline"
                exit 1
            fi
            ;;
        *)
            log_error "Unknown stage: $STAGE"
            exit 1
            ;;
    esac
    
    log_success "🎉 Pipeline completed successfully!"
}

# Check prerequisites
if [ ! -f "$DEPLOY_SCRIPT" ]; then
    log_error "Deploy script not found: $DEPLOY_SCRIPT"
    exit 1
fi

if [ ! -f "CLAUDE.md" ]; then
    log_error "Not in project root directory (CLAUDE.md not found)"
    exit 1
fi

# Run main pipeline
main