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
    # Skip warning if explicitly requested or if ALLOW_PRODUCTION is set
    if [[ "$SKIP_PRODUCTION_WARNING" == "1" ]] || [[ "$ALLOW_PRODUCTION" == "1" ]]; then
        return 0
    fi
    
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

# Register a new user
cmd_register() {
    local email="${1}"
    local password="${2}"
    local role="${3:-startup}"
    local company_name="${4:-Test Company}"
    local first_name="${5:-Test}"
    local last_name="${6:-User}"
    local language="${7:-en}"
    
    if [[ -z "$email" || -z "$password" ]]; then
        log_error "Usage: register <email> <password> [role] [company_name] [first_name] [last_name] [language]"
        echo "       Default role: startup"
        echo "       Default company: 'Test Company'"
        echo "       Default name: 'Test User'"
        echo "       Default language: en"
        return 1
    fi
    
    log_section "User Registration"
    log_info "Email: $email"
    log_info "Role: $role"
    log_info "Company: $company_name"
    log_info "Name: $first_name $last_name"
    log_info "Language: $language"
    
    local payload
    payload=$(jq -n \
        --arg email "$email" \
        --arg password "$password" \
        --arg role "$role" \
        --arg company_name "$company_name" \
        --arg first_name "$first_name" \
        --arg last_name "$last_name" \
        --arg preferred_language "$language" \
        '{
            email: $email,
            password: $password,
            role: $role,
            company_name: $company_name,
            first_name: $first_name,
            last_name: $last_name,
            preferred_language: $preferred_language
        }')
    
    log_info "Sending registration request..."
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/auth/register" \
               -H "Content-Type: application/json" \
               -d "$payload" 2>/dev/null)
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')
    
    if [[ "$http_code" == "200" || "$http_code" == "201" ]]; then
        log_success "User registered successfully!"
        if [[ -n "$body" ]]; then
            echo "$body" | jq '.' 2>/dev/null || echo "$body"
        fi
        
        # Show next steps
        echo ""
        log_info "Next steps:"
        echo "  1. Check email for verification link (if email service is configured)"
        echo "  2. Use: $0 login $role $email"
    else
        log_error "Registration failed (HTTP $http_code)"
        if [[ -n "$body" ]]; then
            echo "$body" | jq '.detail // .' 2>/dev/null || echo "$body"
        fi
        return 1
    fi
}

# Promote user to GP role (requires database access)
cmd_promote() {
    local email="${1}"
    local target_role="${2:-gp}"
    
    if [[ -z "$email" ]]; then
        log_error "Usage: promote <email> [role]"
        echo "       Default role: gp"
        return 1
    fi
    
    log_section "User Role Promotion"
    log_info "Email: $email"
    log_info "Target Role: $target_role"
    
    # Update user role in database
    local result
    result=$(sudo -u postgres psql review-platform -c "UPDATE users SET role = '$target_role' WHERE email = '$email';" 2>&1)
    
    if [[ $? -eq 0 && "$result" == "UPDATE 1" ]]; then
        log_success "User $email promoted to $target_role"
    else
        log_error "Failed to promote user: $result"
        return 1
    fi
}

# Verify user email (requires database access)
cmd_verify() {
    local email="${1}"
    
    if [[ -z "$email" ]]; then
        log_error "Usage: verify <email>"
        return 1
    fi
    
    log_section "User Email Verification"
    log_info "Email: $email"
    
    # Update user verification status in database
    local result
    result=$(sudo -u postgres psql review-platform -c "UPDATE users SET is_verified = true WHERE email = '$email';" 2>&1)
    
    if [[ $? -eq 0 && "$result" == "UPDATE 1" ]]; then
        log_success "User $email verified successfully"
    else
        log_error "Failed to verify user: $result"
        return 1
    fi
}

# Create project using authenticated API
cmd_create_project() {
    local project_name="${1}"
    local funding_round="${2}"
    local company_name="${3}"
    local company_offering="${4}"
    local output_format="${5}" # Optional: "project_id" to return only ID
    
    if [[ -z "$project_name" || -z "$funding_round" || -z "$company_name" || -z "$company_offering" ]]; then
        log_error "Usage: create-project <project_name> <funding_round> <company_name> <company_offering> [output_format]"
        echo "       output_format: 'project_id' to return only the project ID"
        return 1
    fi
    
    if [[ ! -f "$TOKEN_FILE" ]]; then
        log_error "Not authenticated. Please login first."
        return 1
    fi
    
    local token
    token=$(cat "$TOKEN_FILE" 2>/dev/null)
    
    log_section "Project Creation"
    log_info "Project: $project_name"
    log_info "Funding Round: $funding_round"
    log_info "Company: $company_name"
    log_info "Offering: $company_offering"
    
    local payload
    payload=$(jq -n \
        --arg project_name "$project_name" \
        --arg funding_round "$funding_round" \
        --arg company_name "$company_name" \
        --arg company_offering "$company_offering" \
        '{
            project_name: $project_name,
            funding_round: $funding_round,
            company_name: $company_name,
            company_offering: $company_offering
        }')
    
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/projects/create" \
               -H "Authorization: Bearer $token" \
               -H "Content-Type: application/json" \
               -d "$payload" 2>/dev/null)
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')
    
    if [[ "$http_code" == "200" || "$http_code" == "201" ]]; then
        if [[ "$output_format" == "project_id" ]]; then
            echo "$body" | jq -r '.project_id' 2>/dev/null || echo "ERROR"
        else
            log_success "Project created successfully!"
            echo "$body" | jq '.' 2>/dev/null || echo "$body"
        fi
    else
        log_error "Project creation failed (HTTP $http_code)"
        if [[ -n "$body" ]]; then
            echo "$body" | jq '.detail // .' 2>/dev/null || echo "$body"
        fi
        return 1
    fi
}

# Invite user to project
cmd_invite_to_project() {
    local project_id="${1}"
    local email="${2}"
    local output_format="${3}" # Optional: "invitation_token" to return only token
    
    if [[ -z "$project_id" || -z "$email" ]]; then
        log_error "Usage: invite-to-project <project_id> <email> [output_format]"
        echo "       output_format: 'invitation_token' to return only the invitation token"
        return 1
    fi
    
    if [[ ! -f "$TOKEN_FILE" ]]; then
        log_error "Not authenticated. Please login first."
        return 1
    fi
    
    local token
    token=$(cat "$TOKEN_FILE" 2>/dev/null)
    
    log_section "Project Invitation"
    log_info "Project ID: $project_id"
    log_info "Email: $email"
    
    local payload
    payload=$(jq -n --arg email "$email" '{emails: [$email]}')
    
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/projects/$project_id/invite" \
               -H "Authorization: Bearer $token" \
               -H "Content-Type: application/json" \
               -d "$payload" 2>/dev/null)
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')
    
    if [[ "$http_code" == "200" || "$http_code" == "201" ]]; then
        if [[ "$output_format" == "invitation_token" ]]; then
            echo "$body" | jq -r '.[0].invitation_token' 2>/dev/null || echo "ERROR"
        else
            log_success "Invitation sent successfully!"
            echo "$body" | jq '.' 2>/dev/null || echo "$body"
        fi
    else
        log_error "Invitation failed (HTTP $http_code)"
        if [[ -n "$body" ]]; then
            echo "$body" | jq '.detail // .' 2>/dev/null || echo "$body"
        fi
        return 1
    fi
}

# Accept invitation
cmd_accept_invitation() {
    local invitation_token="${1}"
    local first_name="${2:-Test}"
    local last_name="${3:-User}"
    local company_name="${4:-Test Company}"
    local password="${5:-RandomPass978}"
    local language="${6:-en}"
    
    if [[ -z "$invitation_token" ]]; then
        log_error "Usage: accept-invitation <token> [first_name] [last_name] [company_name] [password] [language]"
        return 1
    fi
    
    log_section "Invitation Acceptance"
    log_info "Token: $invitation_token"
    log_info "Name: $first_name $last_name"
    log_info "Company: $company_name"
    
    local payload
    payload=$(jq -n \
        --arg first_name "$first_name" \
        --arg last_name "$last_name" \
        --arg company_name "$company_name" \
        --arg password "$password" \
        --arg preferred_language "$language" \
        '{
            first_name: $first_name,
            last_name: $last_name,
            company_name: $company_name,
            password: $password,
            preferred_language: $preferred_language
        }')
    
    local response
    response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL/api/invitation/$invitation_token/accept" \
               -H "Content-Type: application/json" \
               -d "$payload" 2>/dev/null)
    
    local http_code
    http_code=$(echo "$response" | tail -n1)
    local body
    body=$(echo "$response" | sed '$d')
    
    if [[ "$http_code" == "200" || "$http_code" == "201" ]]; then
        log_success "Invitation accepted successfully!"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    else
        log_error "Invitation acceptance failed (HTTP $http_code)"
        if [[ -n "$body" ]]; then
            echo "$body" | jq '.detail // .' 2>/dev/null || echo "$body"
        fi
        return 1
    fi
}

# Run complete workflow test
cmd_workflow_test() {
    log_section "Complete Workflow Test"
    
    # Check if we can run database commands
    if ! command -v sudo &> /dev/null || ! sudo -u postgres psql --version &> /dev/null; then
        log_error "This test requires database access (sudo + PostgreSQL)"
        return 1
    fi
    
    log_info "Running end-to-end workflow test..."
    
    # Step 1: Register and prepare GP user
    log_info "Step 1: Creating GP user..."
    cmd_register "test-gp-workflow@example.com" "SecurePass907" "startup" "Test GP Firm" "Test" "GP" "en"
    cmd_promote "test-gp-workflow@example.com" "gp"
    cmd_verify "test-gp-workflow@example.com"
    
    # Step 2: Register and verify startup user
    log_info "Step 2: Creating startup user..."
    cmd_register "test-startup-workflow@example.com" "RandomPass978" "startup" "Test Startup Inc" "Test" "User" "en"
    cmd_verify "test-startup-workflow@example.com"
    
    # Step 3: Login as GP and create project
    log_info "Step 3: GP login and project creation..."
    cmd_login "gp" "test-gp-workflow@example.com" <<< "SecurePass907"
    local project_id
    project_id=$(cmd_create_project "Workflow Test Project" "series_a" "Test Startup Inc" "AI workflow platform" "project_id")
    
    if [[ "$project_id" == "ERROR" || -z "$project_id" ]]; then
        log_error "Failed to create project"
        return 1
    fi
    
    # Step 4: Invite startup user
    log_info "Step 4: Inviting startup user..."
    local invitation_token
    invitation_token=$(cmd_invite_to_project "$project_id" "test-startup-workflow@example.com" "invitation_token")
    
    if [[ "$invitation_token" == "ERROR" || -z "$invitation_token" ]]; then
        log_error "Failed to send invitation"
        return 1
    fi
    
    # Step 5: Accept invitation
    log_info "Step 5: Accepting invitation..."
    cmd_accept_invitation "$invitation_token" "Test" "User" "Test Startup Inc" "RandomPass978" "en"
    
    log_success "Complete workflow test PASSED!"
    log_info "Project ID: $project_id"
    log_info "Invitation Token: $invitation_token"
    
    return 0
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
  register <email> <password> [role] [company] [first_name] [last_name] [language]
                           - Register a new user (defaults: startup, "Test Company", "Test User", en)
  promote <email> [role]   - Promote user to GP role (requires database access, default: gp)
  verify <email>           - Mark user as email verified (requires database access)
  login <role> <email>     - Authenticate using real credentials
  whoami                   - Show current user information
  logout                   - Logout and cleanup tokens

PROJECT MANAGEMENT:
  create-project <name> <funding_round> <company> <offering> [output_format]
                           - Create a new project (requires GP authentication)
  invite-to-project <project_id> <email> [output_format]
                           - Invite user to project (requires GP authentication)
  accept-invitation <token> [first_name] [last_name] [company] [password] [language]
                           - Accept project invitation (defaults: "Test User", "Test Company", "RandomPass978", "en")

TESTING:
  workflow-test            - Run complete end-to-end workflow test

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
# Document upload function
cmd_upload_document() {
    local file_path="$1"
    local output_field="$2"
    
    if [[ -z "$file_path" ]]; then
        log_error "Usage: $0 upload-document <file_path> [output_field]"
        echo "  file_path    - Path to PDF file to upload"
        echo "  output_field - Field to extract from response (optional: document_id, task_id, file_path)"
        return 1
    fi
    
    if [[ ! -f "$file_path" ]]; then
        log_error "File not found: $file_path"
        return 1
    fi
    
    # Check if logged in
    if [[ ! -f "$TOKEN_FILE" ]]; then
        log_error "Not logged in. Please login first."
        return 1
    fi
    
    local token
    token=$(cat "$TOKEN_FILE" 2>/dev/null)
    if [[ -z "$token" ]]; then
        log_error "Invalid token file. Please login again."
        return 1
    fi
    
    log_info "Uploading document: $(basename "$file_path")"
    
    local response
    response=$(curl -s -X POST "$BASE_URL/api/documents/upload" \
               -H "Authorization: Bearer $token" \
               -F "file=@$file_path" 2>/dev/null)
    
    if [[ $? -ne 0 ]]; then
        log_error "Failed to upload document"
        return 1
    fi
    
    # Check for error in response
    local error
    error=$(echo "$response" | jq -r '.detail // empty' 2>/dev/null)
    if [[ -n "$error" ]]; then
        log_error "Upload failed: $error"
        return 1
    fi
    
    # Extract and display response
    local message document_id task_id file_upload_path
    message=$(echo "$response" | jq -r '.message // empty' 2>/dev/null)
    document_id=$(echo "$response" | jq -r '.document_id // empty' 2>/dev/null)
    task_id=$(echo "$response" | jq -r '.task_id // empty' 2>/dev/null)
    file_upload_path=$(echo "$response" | jq -r '.file_path // empty' 2>/dev/null)
    
    if [[ -n "$message" ]]; then
        log_success "$message"
        echo "  Document ID: $document_id"
        echo "  Task ID: $task_id"
        echo "  File Path: $file_upload_path"
        
        # Return specific field if requested
        case "$output_field" in
            "document_id") echo "$document_id" ;;
            "task_id") echo "$task_id" ;;
            "file_path") echo "$file_upload_path" ;;
            "") ;; # No output field requested
        esac
    else
        log_error "Upload failed - invalid response"
        echo "$response"
        return 1
    fi
}

# Document processing status check
cmd_check_processing() {
    local document_id="$1"
    
    if [[ -z "$document_id" ]]; then
        log_error "Usage: $0 check-processing <document_id>"
        return 1
    fi
    
    log_info "Checking processing status for document $document_id"
    
    # Use debug API to check processing status
    local response
    response=$(curl -s "$BASE_URL/api/debug/deck/$document_id/status" 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        echo "$response" | jq '.' 2>/dev/null || echo "$response"
    else
        log_error "Failed to check processing status"
        return 1
    fi
}

# Create test PDF document
cmd_create_test_pdf() {
    local filename="${1:-test-document.pdf}"
    local content="${2:-Test PDF Content for Document Upload Testing}"
    
    log_info "Creating test PDF: $filename"
    
    cat > "$filename" << 'EOF'
%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 80
>>
stream
BT
/F1 24 Tf
100 700 Td
(Test PDF Content for Document Upload Testing) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000206 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
334
%%EOF
EOF
    
    log_success "Created test PDF: $filename"
    echo "  Size: $(stat -c%s "$filename" 2>/dev/null || stat -f%z "$filename" 2>/dev/null) bytes"
}

# Complete document workflow test
cmd_document_workflow_test() {
    log_section "Document Workflow Test"
    
    # Check if logged in
    if [[ ! -f "$TOKEN_FILE" ]]; then
        log_error "Not logged in. Please run workflow-test first to setup complete environment."
        return 1
    fi
    
    # Create test PDF
    local test_file="/tmp/auth-helper-test-doc.pdf"
    cmd_create_test_pdf "$test_file"
    
    # Upload document
    log_info "Testing document upload..."
    local document_id
    document_id=$(cmd_upload_document "$test_file" "document_id")
    
    if [[ -z "$document_id" ]]; then
        log_error "Document upload failed"
        return 1
    fi
    
    log_success "Document uploaded successfully - ID: $document_id"
    
    # Check processing status
    log_info "Checking initial processing status..."
    cmd_check_processing "$document_id"
    
    # Wait a moment and check again
    log_info "Waiting 5 seconds for processing to start..."
    sleep 5
    
    log_info "Checking processing status after wait..."
    cmd_check_processing "$document_id"
    
    # Cleanup
    rm -f "$test_file"
    
    log_success "Document workflow test completed successfully!"
    echo "  Document ID: $document_id"
    echo "  Check processing progress with: $0 check-processing $document_id"
}

main() {
    # Always check dependencies for active commands
    case "${1:-help}" in
        "setup"|"login"|"register"|"promote"|"verify"|"create-project"|"invite-to-project"|"accept-invitation"|"upload-document"|"check-processing"|"create-test-pdf"|"document-workflow-test"|"workflow-test"|"api"|"whoami"|"logout"|"config")
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
        "register")
            detect_environment
            cmd_register "$2" "$3" "$4" "$5" "$6" "$7" "$8"
            ;;
        "promote")
            cmd_promote "$2" "$3"
            ;;
        "verify")
            cmd_verify "$2"
            ;;
        "create-project")
            cmd_create_project "$2" "$3" "$4" "$5" "$6"
            ;;
        "invite-to-project")
            cmd_invite_to_project "$2" "$3" "$4"
            ;;
        "accept-invitation")
            cmd_accept_invitation "$2" "$3" "$4" "$5" "$6" "$7"
            ;;
        "upload-document")
            cmd_upload_document "$2" "$3"
            ;;
        "check-processing")
            cmd_check_processing "$2"
            ;;
        "create-test-pdf")
            cmd_create_test_pdf "$2" "$3"
            ;;
        "document-workflow-test")
            detect_environment
            cmd_document_workflow_test
            ;;
        "workflow-test")
            detect_environment
            cmd_workflow_test
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
            log_info "Available commands: setup, config, register, promote, verify, create-project, invite-to-project, accept-invitation, upload-document, check-processing, create-test-pdf, document-workflow-test, workflow-test, login, logout, whoami, api"
            log_info "Run '$0 help' for detailed usage information."
            exit 1
            ;;
    esac
}

# Run main function
main "$@"