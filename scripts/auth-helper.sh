#!/bin/bash

# Secure Authentication Helper for Claude Code
# Uses real authentication endpoints, no backdoors or bypasses
# Provides convenient API testing while maintaining security

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOKEN_FILE="/tmp/claude-auth-token-$(whoami)"
CONFIG_FILE="$SCRIPT_DIR/test-users.conf"
BASE_URL="http://localhost:8000"

# Security: Detect environment and warn if production
detect_environment() {
    local env_result
    if [[ -x "$SCRIPT_DIR/detect-claude-environment.sh" ]]; then
        env_result=$("$SCRIPT_DIR/detect-claude-environment.sh" 2>/dev/null | head -1)
        if [[ "$env_result" == "prod_cpu" ]]; then
            echo -e "${RED}⚠️  WARNING: Running on production server!${NC}"
            echo -e "${YELLOW}This script should primarily be used in development.${NC}"
            echo -e "${YELLOW}Proceed with caution. Press Ctrl+C to abort, Enter to continue.${NC}"
            read -r
        fi
    fi
}

# Helper functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_section() { echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}\n${CYAN}► $1${NC}\n${CYAN}═══════════════════════════════════════════════${NC}"; }

# Ensure jq is available
check_dependencies() {
    if ! command -v jq &> /dev/null; then
        log_error "jq is required but not installed. Please install jq first."
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        log_error "curl is required but not installed. Please install curl first."
        exit 1
    fi
}

# Create secure config file if it doesn't exist
init_config() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_info "Creating test users configuration file..."
        cat > "$CONFIG_FILE" << 'EOF'
# Test Users Configuration for Auth Helper
# Format: email:password:role
# Security: This file contains passwords - keep it secure!
#
# Example entries:
# testuser@startup.com:SecureTestPass123:startup
# testgp@halbzeit.ai:GPTestPass456:gp
#
# Add your test users below:

EOF
        chmod 600 "$CONFIG_FILE"
        log_success "Created secure config file: $CONFIG_FILE"
        log_warning "Please add test user credentials to $CONFIG_FILE before using login command"
        echo -e "${BLUE}Example format: testuser@startup.com:password123:startup${NC}"
    fi
}

# Get user credentials from config
get_credentials() {
    local email=$1
    local line
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "Config file not found: $CONFIG_FILE"
        log_info "Run '$0 setup' to create it"
        return 1
    fi
    
    line=$(grep "^$email:" "$CONFIG_FILE" 2>/dev/null | head -1)
    if [[ -z "$line" ]]; then
        log_error "No credentials found for $email"
        log_info "Add to $CONFIG_FILE: $email:password:role"
        log_info "Available users:"
        grep "^[^#].*:.*:.*$" "$CONFIG_FILE" 2>/dev/null | cut -d: -f1 | sed 's/^/  - /' || echo "  (none configured)"
        return 1
    fi
    
    echo "$line"
}

# Login function - uses real authentication
cmd_login() {
    local role=$1
    local email=$2
    
    if [[ -z "$role" ]] || [[ -z "$email" ]]; then
        log_error "Usage: $0 login <role> <email>"
        log_info "Roles: startup, gp"
        log_info "Example: $0 login startup testuser@startup.com"
        return 1
    fi
    
    log_section "Authenticating as $email ($role)"
    
    # Get credentials from secure config
    local creds
    creds=$(get_credentials "$email")
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    
    local password
    password=$(echo "$creds" | cut -d: -f2)
    local config_role
    config_role=$(echo "$creds" | cut -d: -f3)
    
    # Validate role matches config
    if [[ "$role" != "$config_role" ]]; then
        log_error "Role mismatch: requested '$role' but config has '$config_role' for $email"
        return 1
    fi
    
    log_info "Authenticating with backend..."
    
    # Use REAL login endpoint - no backdoors!
    local response
    response=$(curl -s -X POST "$BASE_URL/api/auth/login" \
               -H "Content-Type: application/json" \
               -d "{\"email\":\"$email\", \"password\":\"$password\"}" 2>/dev/null)
    
    if [[ $? -ne 0 ]]; then
        log_error "Network error connecting to $BASE_URL"
        return 1
    fi
    
    # Check for authentication success
    local token
    token=$(echo "$response" | jq -r '.access_token // empty' 2>/dev/null)
    
    if [[ -n "$token" && "$token" != "null" ]]; then
        # Save token securely
        echo "$token" > "$TOKEN_FILE"
        chmod 600 "$TOKEN_FILE"
        
        # Save user context for reference
        echo "$email:$role" > "${TOKEN_FILE}.user"
        chmod 600 "${TOKEN_FILE}.user"
        
        log_success "Authenticated as $email ($role)"
        log_info "Token saved securely to $TOKEN_FILE"
        
        # Show user info
        cmd_whoami
    else
        local error
        error=$(echo "$response" | jq -r '.detail // "Unknown authentication error"' 2>/dev/null)
        log_error "Authentication failed: $error"
        log_info "Check credentials in $CONFIG_FILE"
        return 1
    fi
}

# Make authenticated API calls
cmd_api() {
    local method=$1
    local endpoint=$2
    shift 2
    
    if [[ -z "$method" ]] || [[ -z "$endpoint" ]]; then
        log_error "Usage: $0 api <METHOD> <endpoint> [curl_options]"
        log_info "Examples:"
        log_info "  $0 api GET /api/projects/my-projects"
        log_info "  $0 api POST /api/projects/upload -F file=@document.pdf"
        log_info "  $0 api GET /api/projects/extraction-results"
        return 1
    fi
    
    # Check authentication
    if [[ ! -f "$TOKEN_FILE" ]]; then
        log_error "Not authenticated. Run: $0 login <role> <email>"
        return 1
    fi
    
    local token
    token=$(cat "$TOKEN_FILE" 2>/dev/null)
    if [[ -z "$token" ]]; then
        log_error "Invalid token file. Please login again."
        return 1
    fi
    
    # Show current user context
    local user_context
    if [[ -f "${TOKEN_FILE}.user" ]]; then
        user_context=$(cat "${TOKEN_FILE}.user" 2>/dev/null)
        log_info "Making API call as: $user_context"
    fi
    
    # Ensure endpoint starts with /
    if [[ ! "$endpoint" =~ ^/ ]]; then
        endpoint="/$endpoint"
    fi
    
    log_info "$method $BASE_URL$endpoint"
    
    # Make authenticated request
    curl -s -X "$method" "$BASE_URL$endpoint" \
         -H "Authorization: Bearer $token" \
         -H "Content-Type: application/json" \
         "$@" | jq '.' 2>/dev/null || {
         # If jq fails, show raw response
         curl -s -X "$method" "$BASE_URL$endpoint" \
              -H "Authorization: Bearer $token" \
              -H "Content-Type: application/json" \
              "$@"
         }
}

# Show current user info
cmd_whoami() {
    if [[ ! -f "$TOKEN_FILE" ]]; then
        log_error "Not authenticated"
        return 1
    fi
    
    local token
    token=$(cat "$TOKEN_FILE" 2>/dev/null)
    if [[ -z "$token" ]]; then
        log_error "Invalid token file. Please login again."
        return 1
    fi
    
    log_info "Fetching current user information..."
    local response
    response=$(curl -s "$BASE_URL/api/auth/me" \
               -H "Authorization: Bearer $token" 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
    else
        log_error "Failed to fetch user information. Token may be expired."
        return 1
    fi
}

# Logout and cleanup
cmd_logout() {
    if [[ -f "$TOKEN_FILE" ]]; then
        rm -f "$TOKEN_FILE"
        log_success "Logged out and cleaned up token"
    fi
    
    if [[ -f "${TOKEN_FILE}.user" ]]; then
        rm -f "${TOKEN_FILE}.user"
    fi
    
    if [[ ! -f "$TOKEN_FILE" ]]; then
        log_info "Not currently logged in"
    fi
}

# Show configuration and test users
cmd_config() {
    log_section "Auth Helper Configuration"
    
    echo -e "${BLUE}Configuration file: ${NC}$CONFIG_FILE"
    echo -e "${BLUE}Token file: ${NC}$TOKEN_FILE"
    echo -e "${BLUE}Base URL: ${NC}$BASE_URL"
    
    if [[ -f "$CONFIG_FILE" ]]; then
        echo -e "\n${BLUE}Configured test users:${NC}"
        grep "^[^#].*:.*:.*$" "$CONFIG_FILE" 2>/dev/null | while IFS=: read -r email password role; do
            echo -e "  ${GREEN}✓${NC} $email ($role)"
        done
        
        local count
        count=$(grep -c "^[^#].*:.*:.*$" "$CONFIG_FILE" 2>/dev/null || echo "0")
        count=${count//[^0-9]/}  # Remove any non-numeric characters
        if [[ "${count:-0}" -eq 0 ]]; then
            echo -e "  ${YELLOW}(none configured)${NC}"
            log_info "Add test users to $CONFIG_FILE"
        fi
    else
        echo -e "\n${YELLOW}Config file not found. Run '$0 setup' to create it.${NC}"
    fi
    
    # Show current login status
    if [[ -f "$TOKEN_FILE" ]] && [[ -f "${TOKEN_FILE}.user" ]]; then
        local user_context
        user_context=$(cat "${TOKEN_FILE}.user" 2>/dev/null)
        echo -e "\n${BLUE}Currently logged in as: ${GREEN}$user_context${NC}"
    else
        echo -e "\n${BLUE}Currently logged in: ${YELLOW}No${NC}"
    fi
}

# Setup command
cmd_setup() {
    log_section "Setting up Auth Helper"
    
    detect_environment
    check_dependencies
    init_config
    
    log_success "Setup complete!"
    log_info "Next steps:"
    log_info "1. Add test user credentials to $CONFIG_FILE"
    log_info "2. Run: $0 config (to verify setup)"
    log_info "3. Run: $0 login startup test@example.com"
}

# Show usage help
show_help() {
    cat << EOF
🔐 Secure Authentication Helper for Claude Code

This script provides secure API testing capabilities using real authentication.
No backdoors, no bypasses - uses legitimate login endpoints only.

Usage: $0 <command> [options]

SETUP & CONFIGURATION:
  setup                    - Initial setup and dependency check
  config                   - Show current configuration and test users
  
AUTHENTICATION:
  login <role> <email>     - Authenticate using real credentials
  whoami                   - Show current user information
  logout                   - Logout and cleanup tokens

API TESTING:
  api <METHOD> <endpoint> [options]  - Make authenticated API calls
  
Examples:
  $0 setup
  $0 config
  $0 login startup testuser@startup.com
  $0 login gp testgp@halbzeit.ai
  $0 whoami
  $0 api GET /api/projects/my-projects
  $0 api GET /api/projects/extraction-results  
  $0 api POST /api/projects/upload -F file=@test.pdf
  $0 logout

SECURITY FEATURES:
  ✓ Uses real authentication endpoints only
  ✓ No backdoors or authentication bypasses
  ✓ Secure token storage with proper permissions  
  ✓ Production environment warnings
  ✓ Credential validation and role checking
  ✓ Automatic token cleanup on logout

CONFIGURATION:
  Config file: $CONFIG_FILE
  Token file:  $TOKEN_FILE
  Base URL:    $BASE_URL

Add test users to config file in format:
  email:password:role

Security: Keep your config file secure (chmod 600) as it contains passwords.

EOF
}

# Main command dispatcher
main() {
    # Always check dependencies for active commands
    case "${1:-help}" in
        "setup"|"login"|"api"|"whoami"|"logout"|"config")
            check_dependencies
            ;;
    esac
    
    case "${1:-help}" in
        "setup")
            cmd_setup
            ;;
        "login")
            detect_environment
            cmd_login "$2" "$3"
            ;;
        "api")
            shift
            cmd_api "$@"
            ;;
        "whoami")
            cmd_whoami
            ;;
        "logout")
            cmd_logout
            ;;
        "config")
            cmd_config
            ;;
        "help"|"-h"|"--help")
            show_help
            ;;
        *)
            log_error "Unknown command: ${1:-help}"
            echo ""
            log_info "Available commands: setup, config, login, logout, whoami, api"
            log_info "Run '$0 help' for detailed usage information."
            exit 1
            ;;
    esac
}

# Run main function
main "$@"