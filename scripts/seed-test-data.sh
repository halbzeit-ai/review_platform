#!/bin/bash

# Test Data Seeding Script
# Creates a complete test environment with users and projects for testing

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
AUTH_HELPER="$SCRIPT_DIR/auth-helper.sh"

# Test data configuration
GP_USERS=(
    "test-gp-alpha@example.com|SecurePass907|Test GP Alpha|Alpha|GP|en"
    "test-gp-beta@example.com|SecurePass908|Test GP Beta|Beta|GP|en"
)

STARTUP_USERS=(
    "test-startup-alpha@example.com|RandomPass978|Test Startup Alpha|Alpha|User|en"
    "test-startup-beta@example.com|RandomPass979|Test Startup Beta|Beta|User|en"
    "test-startup-gamma@example.com|RandomPass980|Test Startup Gamma|Gamma|User|en"
)

# Check dependencies
check_dependencies() {
    if [[ ! -f "$AUTH_HELPER" ]]; then
        log_error "Auth helper script not found: $AUTH_HELPER"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq is required but not installed"
        exit 1
    fi
    
    if ! command -v sudo &> /dev/null || ! sudo -u postgres psql --version &> /dev/null; then
        log_error "This script requires database access (sudo + PostgreSQL)"
        exit 1
    fi
}

# Create test users
create_test_users() {
    log_section "Creating Test Users"
    
    # Create GP users
    log_info "Creating GP users..."
    for user_data in "${GP_USERS[@]}"; do
        IFS='|' read -r email password company first_name last_name language <<< "$user_data"
        
        log_info "Creating GP: $email"
        if "$AUTH_HELPER" register "$email" "$password" "startup" "$company" "$first_name" "$last_name" "$language" > /dev/null 2>&1; then
            "$AUTH_HELPER" promote "$email" "gp" > /dev/null 2>&1
            "$AUTH_HELPER" verify "$email" > /dev/null 2>&1
            log_success "GP user created: $email"
        else
            log_warning "GP user might already exist: $email"
        fi
    done
    
    # Create startup users
    log_info "Creating startup users..."
    for user_data in "${STARTUP_USERS[@]}"; do
        IFS='|' read -r email password company first_name last_name language <<< "$user_data"
        
        log_info "Creating startup: $email"
        if "$AUTH_HELPER" register "$email" "$password" "startup" "$company" "$first_name" "$last_name" "$language" > /dev/null 2>&1; then
            "$AUTH_HELPER" verify "$email" > /dev/null 2>&1
            log_success "Startup user created: $email"
        else
            log_warning "Startup user might already exist: $email"
        fi
    done
}

# Create test projects
create_test_projects() {
    log_section "Creating Test Projects"
    
    # Login as first GP user
    local gp_email="${GP_USERS[0]%%|*}"
    local gp_password=$(echo "${GP_USERS[0]}" | cut -d'|' -f2)
    
    log_info "Logging in as GP: $gp_email"
    if ! echo "$gp_password" | "$AUTH_HELPER" login "gp" "$gp_email" > /dev/null 2>&1; then
        log_error "Failed to login as GP user"
        return 1
    fi
    
    # Create test projects
    local projects=(
        "AI Health Analytics|series_a|MedTech Innovations Inc|AI-powered healthcare analytics platform for predictive diagnostics"
        "Fintech Revolution|series_b|FinanceFlow Corp|Blockchain-based financial services platform for SMEs"
        "Green Energy Solutions|seed|EcoTech Ventures|Solar panel optimization using IoT and machine learning"
    )
    
    for project_data in "${projects[@]}"; do
        IFS='|' read -r project_name funding_round company_name offering <<< "$project_data"
        
        log_info "Creating project: $project_name"
        local project_id
        project_id=$("$AUTH_HELPER" create-project "$project_name" "$funding_round" "$company_name" "$offering" "project_id" 2>/dev/null)
        
        if [[ "$project_id" != "ERROR" && -n "$project_id" ]]; then
            log_success "Project created: $project_name (ID: $project_id)"
            
            # Invite a random startup user to this project
            local startup_email="${STARTUP_USERS[$((RANDOM % ${#STARTUP_USERS[@]}))]}"
            startup_email="${startup_email%%|*}"
            
            log_info "Inviting startup user: $startup_email"
            local invitation_token
            invitation_token=$("$AUTH_HELPER" invite-to-project "$project_id" "$startup_email" "invitation_token" 2>/dev/null)
            
            if [[ "$invitation_token" != "ERROR" && -n "$invitation_token" ]]; then
                log_success "Invitation sent to: $startup_email"
                
                # Auto-accept invitation
                if "$AUTH_HELPER" accept-invitation "$invitation_token" > /dev/null 2>&1; then
                    log_success "Invitation auto-accepted"
                fi
            fi
        else
            log_warning "Failed to create project: $project_name"
        fi
    done
}

# Show test environment status
show_environment_status() {
    log_section "Test Environment Status"
    
    # Count users by role
    local gp_count startup_count total_users
    gp_count=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM users WHERE role = 'gp';" 2>/dev/null | tr -d ' ')
    startup_count=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM users WHERE role = 'startup';" 2>/dev/null | tr -d ' ')
    total_users=$((gp_count + startup_count))
    
    # Count projects and memberships
    local project_count member_count
    project_count=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM projects;" 2>/dev/null | tr -d ' ')
    member_count=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM project_members;" 2>/dev/null | tr -d ' ')
    
    log_info "Users: $total_users total ($gp_count GPs, $startup_count startups)"
    log_info "Projects: $project_count total"
    log_info "Project memberships: $member_count total"
    
    echo ""
    log_success "Test environment ready!"
    echo ""
    echo "Test GP Users:"
    for user_data in "${GP_USERS[@]}"; do
        local email="${user_data%%|*}"
        echo "  - $email"
    done
    
    echo ""
    echo "Test Startup Users:"
    for user_data in "${STARTUP_USERS[@]}"; do
        local email="${user_data%%|*}"
        echo "  - $email"
    done
    
    echo ""
    log_info "Use: $AUTH_HELPER login <role> <email> to test authentication"
}

# Cleanup function
cleanup_test_data() {
    if [[ "$1" == "--clean" ]]; then
        log_section "Cleaning Test Data"
        log_warning "This will remove all test users and projects!"
        
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            # Delete test users (this will cascade to projects and memberships)
            for user_data in "${GP_USERS[@]}" "${STARTUP_USERS[@]}"; do
                local email="${user_data%%|*}"
                sudo -u postgres psql review-platform -c "DELETE FROM users WHERE email = '$email';" > /dev/null 2>&1
                log_info "Deleted user: $email"
            done
            
            log_success "Test data cleaned up"
        else
            log_info "Cleanup cancelled"
        fi
        exit 0
    fi
}

# Main function
main() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        cat << EOF
🌱 Test Data Seeding Script

Usage: $0 [options]

Options:
  --clean    Clean up all test data
  --help     Show this help message

This script creates a complete test environment with:
- 2 GP users (test-gp-alpha@example.com, test-gp-beta@example.com)  
- 3 Startup users (test-startup-alpha/beta/gamma@example.com)
- 3 Test projects with automatic invitations and acceptances
- All users are automatically verified and ready for testing

Examples:
  $0                    # Seed test data
  $0 --clean            # Remove all test data
  $0 --help             # Show this help

After seeding, you can test with:
  ./scripts/auth-helper.sh login gp test-gp-alpha@example.com
  ./scripts/auth-helper.sh workflow-test
EOF
        exit 0
    fi
    
    cleanup_test_data "$1"
    
    log_section "Test Data Seeding"
    log_info "Creating comprehensive test environment..."
    
    check_dependencies
    create_test_users
    create_test_projects
    show_environment_status
    
    echo ""
    log_success "Test data seeding complete!"
    log_info "Run: $0 --clean to remove all test data"
}

# Run main function
main "$@"