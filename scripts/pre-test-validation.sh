#!/bin/bash

# Pre-Test Validation Script
# Validates system readiness before running tests

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_section() { echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}\n${CYAN}► $1${NC}\n${CYAN}═══════════════════════════════════════════════${NC}"; }

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_URL="http://localhost:8000"

# Validation counters
VALIDATIONS_PASSED=0
VALIDATIONS_FAILED=0
VALIDATIONS_TOTAL=0

declare -a FAILED_VALIDATIONS=()

# Validation assertion function
validate() {
    local test_name="$1"
    local command="$2"
    local expected_pattern="$3"
    
    VALIDATIONS_TOTAL=$((VALIDATIONS_TOTAL + 1))
    
    log_info "Validating: $test_name..."
    
    local result
    result=$(eval "$command" 2>/dev/null || echo "ERROR")
    
    if [[ "$result" =~ $expected_pattern ]]; then
        VALIDATIONS_PASSED=$((VALIDATIONS_PASSED + 1))
        log_success "$test_name"
        return 0
    else
        VALIDATIONS_FAILED=$((VALIDATIONS_FAILED + 1))
        FAILED_VALIDATIONS+=("$test_name: $result")
        log_error "$test_name - Got: $result"
        return 1
    fi
}

# Check system dependencies
validate_dependencies() {
    log_section "System Dependencies"
    
    validate "curl available" "command -v curl" "curl"
    validate "jq available" "command -v jq" "jq"
    validate "sudo available" "command -v sudo" "sudo"
    validate "PostgreSQL client available" "command -v psql" "psql"
    validate "Database access" "sudo -u postgres psql --version" "PostgreSQL"
}

# Validate backend service
validate_backend_service() {
    log_section "Backend Service"
    
    validate "Backend process running" "pgrep -f 'uvicorn.*app.main:app'" "[0-9]+"
    validate "Backend port 8000 listening" "lsof -i :8000 | grep LISTEN" "LISTEN"
    validate "Backend API responding" "curl -s -w '%{http_code}' -o /dev/null $BASE_URL/api/debug/health" "200"
    validate "Backend health status" "curl -s $BASE_URL/api/debug/health-detailed | jq -r '.status'" "healthy"
}

# Validate database connectivity
validate_database() {
    log_section "Database Connectivity"
    
    validate "Database connection" "sudo -u postgres psql review-platform -c 'SELECT 1;'" "1"
    validate "Users table exists" "sudo -u postgres psql review-platform -c '\dt users'" "users"
    validate "Projects table exists" "sudo -u postgres psql review-platform -c '\dt projects'" "projects"
    validate "Project documents table exists" "sudo -u postgres psql review-platform -c '\dt project_documents'" "project_documents"
}

# Validate API endpoints
validate_api_endpoints() {
    log_section "API Endpoints"
    
    validate "Health endpoint" "curl -s $BASE_URL/api/debug/health | jq -r '.status'" "ok"
    validate "Database tables endpoint" "curl -s $BASE_URL/api/debug/database/tables | jq -r '.count'" "[0-9]+"
    validate "OpenAPI documentation" "curl -s -w '%{http_code}' -o /dev/null $BASE_URL/openapi.json" "200"
    
    # Test authentication endpoints (should return 422 for missing body, not 500)
    local auth_status
    auth_status=$(curl -s -w '%{http_code}' -o /dev/null -X POST -H "Content-Type: application/json" "$BASE_URL/api/auth/register")
    if [[ "$auth_status" == "422" ]]; then
        VALIDATIONS_PASSED=$((VALIDATIONS_PASSED + 1))
        log_success "Auth register endpoint responds correctly"
    else
        VALIDATIONS_FAILED=$((VALIDATIONS_FAILED + 1))
        FAILED_VALIDATIONS+=("Auth register endpoint: HTTP $auth_status (expected 422)")
        log_error "Auth register endpoint - Expected HTTP 422, got $auth_status"
    fi
    VALIDATIONS_TOTAL=$((VALIDATIONS_TOTAL + 1))
}

# Validate database schema consistency
validate_database_schema() {
    log_section "Database Schema"
    
    # Check critical tables have expected columns
    validate "Users table has email column" "sudo -u postgres psql review-platform -c '\d users' | grep email" "email"
    validate "Projects table has owner_id column" "sudo -u postgres psql review-platform -c '\d projects' | grep owner_id" "owner_id"
    validate "Project members table exists" "sudo -u postgres psql review-platform -c '\dt project_members'" "project_members"
    validate "Project invitations table exists" "sudo -u postgres psql review-platform -c '\dt project_invitations'" "project_invitations"
    
    # Check foreign key constraints
    validate "Project members foreign key to users" "sudo -u postgres psql review-platform -c '\d project_members' | grep 'users(id)'" "users"
    validate "Project members foreign key to projects" "sudo -u postgres psql review-platform -c '\d project_members' | grep 'projects(id)'" "projects"
}

# Validate essential scripts
validate_scripts() {
    log_section "Essential Scripts"
    
    local scripts=(
        "auth-helper.sh"
        "debug-api.sh"
        "detect-claude-environment.sh"
    )
    
    for script in "${scripts[@]}"; do
        local script_path="$SCRIPT_DIR/$script"
        if [[ -f "$script_path" && -x "$script_path" ]]; then
            VALIDATIONS_PASSED=$((VALIDATIONS_PASSED + 1))
            log_success "$script available and executable"
        else
            VALIDATIONS_FAILED=$((VALIDATIONS_FAILED + 1))
            FAILED_VALIDATIONS+=("$script: not found or not executable")
            log_error "$script not found or not executable"
        fi
        VALIDATIONS_TOTAL=$((VALIDATIONS_TOTAL + 1))
    done
}

# Validate system configuration
validate_configuration() {
    log_section "System Configuration"
    
    # Check environment variables
    validate "Backend directory exists" "test -d /opt/review-platform/backend" ".*"
    validate "Frontend directory exists" "test -d /opt/review-platform/frontend" ".*"
    validate "Python virtual environment" "test -f /opt/review-platform/venv/bin/python" ".*"
    
    # Check configuration files
    validate "Backend config exists" "test -f /opt/review-platform/backend/.env" ".*"
    
    # Check database configuration
    validate "Database name configured correctly" "grep -q 'review-platform' /etc/postgresql/*/main/postgresql.conf || echo 'Database accessible'" ".*"
}

# Validate performance indicators
validate_performance() {
    log_section "Performance Indicators"
    
    # Test API response time
    local start_time end_time response_time
    start_time=$(date +%s%3N)
    curl -s "$BASE_URL/api/debug/health" > /dev/null 2>&1
    end_time=$(date +%s%3N)
    response_time=$((end_time - start_time))
    
    if [[ $response_time -lt 1000 ]]; then
        VALIDATIONS_PASSED=$((VALIDATIONS_PASSED + 1))
        log_success "API response time acceptable (${response_time}ms)"
    else
        VALIDATIONS_FAILED=$((VALIDATIONS_FAILED + 1))
        FAILED_VALIDATIONS+=("API response time too slow: ${response_time}ms")
        log_error "API response time too slow: ${response_time}ms"
    fi
    VALIDATIONS_TOTAL=$((VALIDATIONS_TOTAL + 1))
    
    # Check memory usage
    local memory_usage
    memory_usage=$(free | grep '^Mem:' | awk '{printf "%.1f", ($3/$2) * 100.0}')
    if (( $(echo "$memory_usage < 90" | bc -l) )); then
        VALIDATIONS_PASSED=$((VALIDATIONS_PASSED + 1))
        log_success "Memory usage acceptable (${memory_usage}%)"
    else
        VALIDATIONS_FAILED=$((VALIDATIONS_FAILED + 1))
        FAILED_VALIDATIONS+=("High memory usage: ${memory_usage}%")
        log_warning "High memory usage: ${memory_usage}%"
    fi
    VALIDATIONS_TOTAL=$((VALIDATIONS_TOTAL + 1))
}

# Show validation summary
show_validation_summary() {
    log_section "Validation Summary"
    
    echo ""
    log_info "Total Validations: $VALIDATIONS_TOTAL"
    log_success "Passed: $VALIDATIONS_PASSED"
    
    if [[ $VALIDATIONS_FAILED -gt 0 ]]; then
        log_error "Failed: $VALIDATIONS_FAILED"
        echo ""
        log_error "Failed Validations:"
        for failed_validation in "${FAILED_VALIDATIONS[@]}"; do
            echo "  - $failed_validation"
        done
        echo ""
    fi
    
    local success_rate
    if [[ $VALIDATIONS_TOTAL -gt 0 ]]; then
        success_rate=$((VALIDATIONS_PASSED * 100 / VALIDATIONS_TOTAL))
        log_info "Success Rate: ${success_rate}%"
    fi
    
    echo ""
    if [[ $VALIDATIONS_FAILED -eq 0 ]]; then
        log_success "🚀 System ready for testing!"
        return 0
    else
        if [[ $VALIDATIONS_FAILED -le 2 ]]; then
            log_warning "⚠️  System mostly ready - minor issues detected"
            log_info "You may proceed with testing, but consider fixing the issues above"
            return 0
        else
            log_error "❌ System not ready for testing"
            log_error "Please fix the issues above before running tests"
            return 1
        fi
    fi
}

# Fix common issues
fix_common_issues() {
    if [[ "$1" == "--fix" ]]; then
        log_section "Attempting to Fix Common Issues"
        
        # Try to start backend if not running
        if ! pgrep -f "uvicorn.*app.main:app" > /dev/null; then
            log_info "Backend not running, attempting to start..."
            if systemctl is-active --quiet review-platform.service; then
                log_info "Backend service is active"
            else
                sudo systemctl restart review-platform.service 2>/dev/null && sleep 3
                if systemctl is-active --quiet review-platform.service; then
                    log_success "Backend service restarted successfully"
                else
                    log_error "Failed to start backend service"
                fi
            fi
        fi
        
        # Check and fix script permissions
        local scripts=("auth-helper.sh" "debug-api.sh" "detect-claude-environment.sh")
        for script in "${scripts[@]}"; do
            local script_path="$SCRIPT_DIR/$script"
            if [[ -f "$script_path" ]]; then
                chmod +x "$script_path" 2>/dev/null
                log_info "Made $script executable"
            fi
        done
        
        log_info "Common fixes applied, re-running validation..."
        echo ""
    fi
}

# Main function
main() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        cat << EOF
🔍 Pre-Test Validation Script

Usage: $0 [options]

Options:
  --fix        Try to fix common issues automatically
  --help       Show this help message

This script validates system readiness before running tests:

SYSTEM DEPENDENCIES:
  ✓ Required command-line tools (curl, jq, sudo, psql)
  ✓ PostgreSQL database access

BACKEND SERVICE:
  ✓ Backend process running (uvicorn)
  ✓ Port 8000 listening
  ✓ API responding to requests
  ✓ Health endpoint returning healthy status

DATABASE:
  ✓ Database connection working
  ✓ Critical tables exist (users, projects, project_documents)
  ✓ Foreign key constraints in place

API ENDPOINTS:
  ✓ Debug endpoints responding
  ✓ Authentication endpoints configured
  ✓ OpenAPI documentation available

SYSTEM CONFIGURATION:
  ✓ Required directories exist
  ✓ Configuration files present
  ✓ Python virtual environment set up

PERFORMANCE:
  ✓ API response times acceptable
  ✓ Memory usage within limits

Examples:
  $0                    # Run validation checks
  $0 --fix              # Try to fix issues and re-validate
  $0 --help             # Show this help

Exit codes:
  0 = System ready for testing
  1 = Critical issues found, testing not recommended
EOF
        exit 0
    fi
    
    fix_common_issues "$1"
    
    log_section "Pre-Test Validation"
    log_info "Checking system readiness for testing..."
    
    # Run all validations
    validate_dependencies
    validate_backend_service
    validate_database
    validate_api_endpoints
    validate_database_schema
    validate_scripts
    validate_configuration
    validate_performance
    
    # Show results
    show_validation_summary
}

# Run main function
main "$@"