#!/bin/bash

# HALBZEIT API Debug Helper Script
# Provides easy access to debug endpoints without authentication

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="http://localhost:8000/api/debug"
TIMEOUT=10

# Helper functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_section() { echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}\n${CYAN}► $1${NC}\n${CYAN}═══════════════════════════════════════════════${NC}"; }

# Function to make API call and format output
api_call() {
    local endpoint=$1
    local description=$2
    
    echo -e "\n${YELLOW}🔍 Testing: $description${NC}"
    echo -e "${BLUE}📡 Endpoint: GET $BASE_URL$endpoint${NC}"
    
    response=$(curl -s -w "\nHTTP_CODE:%{http_code}" --max-time $TIMEOUT "$BASE_URL$endpoint" 2>/dev/null || echo "CURL_ERROR")
    
    if [[ "$response" == "CURL_ERROR" ]]; then
        log_error "Network error or timeout"
        return 1
    fi
    
    # Extract HTTP code
    http_code=$(echo "$response" | tail -n1 | cut -d: -f2)
    content=$(echo "$response" | head -n -1)
    
    if [[ "$http_code" == "200" ]]; then
        log_success "Success (HTTP $http_code)"
        echo -e "${GREEN}Response:${NC}"
        echo "$content" | python3 -m json.tool 2>/dev/null || echo "$content"
    else
        log_error "Failed (HTTP $http_code)"
        echo "$content"
    fi
    
    return 0
}

# Main function
show_help() {
    cat << EOF
🛠️  HALBZEIT API Debug Helper

This script provides quick access to debug endpoints without authentication.

Usage: $0 [command] [options]

Commands:
  health           - Detailed health check
  deck <id>        - Get deck status and processing info
  specialized <id> - Get specialized analysis results for deck
  tables           - List all database tables
  table <name>     - Get table structure and info
  env              - Show environment configuration
  project <id>     - Analyze project data and relationships
  user <email>     - Analyze user relationships and dependencies
  deletion <id>    - Preview project deletion impact (what would be deleted)
  orphans          - List and analyze orphaned projects
  all              - Run all debug checks
  help             - Show this help

Examples:
  $0 health                    # Basic health check
  $0 deck 143                  # Check deck 143 status
  $0 specialized 151          # Get specialized analysis for deck 151
  $0 table pitch_decks         # Get pitch_decks table info
  $0 project 31                # Analyze project 31 data and relationships
  $0 user user@company.com     # Check user relationships
  $0 deletion 31               # Preview what would be deleted for project 31
  $0 orphans                   # List orphaned projects
  $0 tables                    # List all tables
  $0 all                       # Run comprehensive debug

Debug Endpoints Available:
  GET /api/debug/health-detailed
  GET /api/debug/deck/{id}/status
  GET /api/debug/deck/{id}/specialized-analysis
  GET /api/debug/database/tables
  GET /api/debug/database/table/{name}/info
  GET /api/debug/environment

EOF
}

# Command handlers
cmd_health() {
    log_section "System Health Check"
    api_call "/health-detailed" "Comprehensive system health"
}

cmd_deck() {
    local deck_id=$1
    if [[ -z "$deck_id" ]]; then
        log_error "Please provide a deck ID"
        echo "Usage: $0 deck <deck_id>"
        exit 1
    fi
    
    log_section "Deck Status Check"
    api_call "/deck/$deck_id/status" "Deck $deck_id processing status"
}

cmd_specialized() {
    local deck_id=$1
    if [[ -z "$deck_id" ]]; then
        log_error "Please provide a deck ID"
        echo "Usage: $0 specialized <deck_id>"
        exit 1
    fi
    
    log_section "Specialized Analysis Results"
    api_call "/deck/$deck_id/specialized-analysis" "Specialized analysis for deck $deck_id (clinical_validation, regulatory_pathway, scientific_hypothesis)"
}

cmd_tables() {
    log_section "Database Tables"
    api_call "/database/tables" "List all database tables"
}

cmd_table() {
    local table_name=$1
    if [[ -z "$table_name" ]]; then
        log_error "Please provide a table name"
        echo "Usage: $0 table <table_name>"
        exit 1
    fi
    
    log_section "Table Information"
    api_call "/database/table/$table_name/info" "Table $table_name structure and data"
}

cmd_env() {
    log_section "Environment Configuration"
    api_call "/environment" "Server environment information"
}

# NEW: Enhanced command handlers for project management debugging

cmd_project() {
    local project_id=$1
    if [[ -z "$project_id" ]]; then
        log_error "Please provide a project ID"
        echo "Usage: $0 project <project_id>"
        exit 1
    fi
    
    log_section "Project Analysis"
    
    # Direct database query to analyze project relationships
    log_info "Analyzing project $project_id data and relationships..."
    
    # Get comprehensive project information
    echo -e "\n${YELLOW}📊 Project Overview${NC}"
    psql -h 65.108.32.143 -U review_user -d review_dev -c "
    SELECT 
        p.id,
        p.company_id,
        p.project_name,
        p.funding_round,
        p.funding_sought,
        p.is_test,
        p.is_active,
        COUNT(DISTINCT pd.id) as document_count,
        COUNT(DISTINCT pm.id) as member_count,
        COUNT(DISTINCT pi.id) as invitation_count
    FROM projects p
    LEFT JOIN project_documents pd ON p.id = pd.project_id
    LEFT JOIN project_members pm ON p.id = pm.project_id
    LEFT JOIN project_invitations pi ON p.id = pi.project_id
    WHERE p.id = $project_id
    GROUP BY p.id, p.company_id, p.project_name, p.funding_round, p.funding_sought, p.is_test, p.is_active;
    " 2>/dev/null || log_error "Database connection failed - using API fallback"
    
    # Show related data
    echo -e "\n${YELLOW}📄 Project Documents${NC}"
    psql -h 65.108.32.143 -U review_user -d review_dev -c "
    SELECT file_name, document_type, processing_status, upload_date, 
           CASE WHEN uploaded_by IS NOT NULL THEN 'User ' || uploaded_by ELSE 'System' END as uploader
    FROM project_documents 
    WHERE project_id = $project_id 
    ORDER BY upload_date DESC;
    " 2>/dev/null || true
    
    echo -e "\n${YELLOW}👥 Project Members${NC}"
    psql -h 65.108.32.143 -U review_user -d review_dev -c "
    SELECT u.email, pm.role, pm.added_at
    FROM project_members pm
    JOIN users u ON pm.user_id = u.id
    WHERE pm.project_id = $project_id;
    " 2>/dev/null || true
}

cmd_user() {
    local user_email=$1
    if [[ -z "$user_email" ]]; then
        log_error "Please provide a user email"
        echo "Usage: $0 user <user_email>"
        exit 1
    fi
    
    log_section "User Relationship Analysis"
    
    log_info "Analyzing relationships for user: $user_email"
    
    echo -e "\n${YELLOW}👤 User Information${NC}"
    psql -h 65.108.32.143 -U review_user -d review_dev -c "
    SELECT id, email, role, company_name, is_verified, created_at, last_login
    FROM users 
    WHERE email = '$user_email';
    " 2>/dev/null || log_error "Database connection failed"
    
    echo -e "\n${YELLOW}🏗️ Project Memberships${NC}"
    psql -h 65.108.32.143 -U review_user -d review_dev -c "
    SELECT p.id, p.company_id, p.project_name, pm.role, pm.added_at
    FROM project_members pm
    JOIN projects p ON pm.project_id = p.id
    JOIN users u ON pm.user_id = u.id
    WHERE u.email = '$user_email';
    " 2>/dev/null || true
    
    echo -e "\n${YELLOW}📧 Pending Invitations${NC}"
    psql -h 65.108.32.143 -U review_user -d review_dev -c "
    SELECT p.id, p.project_name, pi.status, pi.created_at, pi.expires_at
    FROM project_invitations pi
    JOIN projects p ON pi.project_id = p.id
    WHERE pi.email = '$user_email' AND pi.status = 'pending';
    " 2>/dev/null || true
}

cmd_deletion() {
    local project_id=$1
    if [[ -z "$project_id" ]]; then
        log_error "Please provide a project ID"
        echo "Usage: $0 deletion <project_id>"
        exit 1
    fi
    
    log_section "Project Deletion Impact Preview"
    
    log_warning "This shows what WOULD BE DELETED if you deleted project $project_id"
    
    echo -e "\n${YELLOW}🗂️ Files that would be deleted${NC}"
    psql -h 65.108.32.143 -U review_user -d review_dev -c "
    SELECT file_name, file_path, file_size, document_type
    FROM project_documents
    WHERE project_id = $project_id;
    " 2>/dev/null || true
    
    echo -e "\n${YELLOW}👥 Users that might be deleted${NC}"
    echo -e "${BLUE}(Only users who ONLY belong to this project)${NC}"
    psql -h 65.108.32.143 -U review_user -d review_dev -c "
    SELECT DISTINCT u.email, u.role
    FROM users u
    JOIN project_members pm ON u.id = pm.user_id
    WHERE pm.project_id = $project_id 
    AND u.role = 'startup'
    AND u.id NOT IN (
        SELECT DISTINCT pm2.user_id
        FROM project_members pm2
        WHERE pm2.project_id != $project_id
        UNION
        SELECT DISTINCT pi.accepted_by_id
        FROM project_invitations pi
        WHERE pi.project_id != $project_id AND pi.accepted_by_id IS NOT NULL
    );
    " 2>/dev/null || true
    
    echo -e "\n${YELLOW}📊 Computed Results that would be deleted${NC}"
    psql -h 65.108.32.143 -U review_user -d review_dev -c "
    SELECT 'Specialized Analysis Results' as data_type, COUNT(*) as count
    FROM specialized_analysis_results 
    WHERE pitch_deck_id IN (
        SELECT reference_pitch_deck_id 
        FROM project_documents 
        WHERE project_id = $project_id AND reference_pitch_deck_id IS NOT NULL
    )
    UNION ALL
    SELECT 'Visual Analysis Cache' as data_type, COUNT(*) as count
    FROM visual_analysis_cache 
    WHERE pitch_deck_id IN (
        SELECT reference_pitch_deck_id 
        FROM project_documents 
        WHERE project_id = $project_id AND reference_pitch_deck_id IS NOT NULL
    )
    UNION ALL
    SELECT 'Reviews' as data_type, COUNT(*) as count
    FROM reviews 
    WHERE pitch_deck_id IN (
        SELECT reference_pitch_deck_id 
        FROM project_documents 
        WHERE project_id = $project_id AND reference_pitch_deck_id IS NOT NULL
    );
    " 2>/dev/null || true
    
    echo -e "\n${RED}⚠️ WARNING: This is a preview only. Actual deletion is irreversible!${NC}"
}

cmd_orphans() {
    log_section "Orphaned Projects Analysis"
    
    log_info "Finding projects with no members and no pending invitations..."
    
    echo -e "\n${YELLOW}🏚️ Orphaned Projects${NC}"
    psql -h 65.108.32.143 -U review_user -d review_dev -c "
    SELECT 
        p.id,
        p.company_id,
        p.project_name,
        p.funding_round,
        COUNT(pd.id) as document_count,
        STRING_AGG(DISTINCT u_deleted.email, ', ') as deleted_user_emails,
        p.created_at
    FROM projects p
    LEFT JOIN project_members pm ON p.id = pm.project_id
    LEFT JOIN project_invitations pi ON p.id = pi.project_id AND pi.status = 'pending'
    LEFT JOIN project_documents pd ON p.id = pd.project_id
    -- Look for users who uploaded documents but are not members
    LEFT JOIN users u_deleted ON u_deleted.id = pd.uploaded_by 
        AND u_deleted.id NOT IN (
            SELECT DISTINCT user_id FROM project_members WHERE project_id = p.id
            UNION
            SELECT DISTINCT accepted_by_id FROM project_invitations WHERE project_id = p.id AND accepted_by_id IS NOT NULL
        )
    WHERE p.is_active = TRUE
    GROUP BY p.id, p.company_id, p.project_name, p.funding_round, p.created_at
    HAVING COUNT(pm.id) = 0 AND COUNT(pi.id) = 0
    ORDER BY p.created_at DESC;
    " 2>/dev/null || log_error "Database connection failed"
    
    echo -e "\n${BLUE}💡 These projects can be recovered by inviting new users or deleted permanently.${NC}"
}

cmd_all() {
    log_section "Comprehensive Debug Report"
    
    cmd_health
    cmd_env
    cmd_tables
    cmd_orphans
    
    # Test a few specific decks if they exist
    log_section "Sample Deck Checks"
    for deck_id in 140 143 144; do
        api_call "/deck/$deck_id/status" "Deck $deck_id status" || true
    done
}

# Parse command line arguments
case "${1:-help}" in
    "health")
        cmd_health
        ;;
    "deck")
        cmd_deck "$2"
        ;;
    "specialized")
        cmd_specialized "$2"
        ;;
    "tables")
        cmd_tables
        ;;
    "table")
        cmd_table "$2"
        ;;
    "env")
        cmd_env
        ;;
    "project")
        cmd_project "$2"
        ;;
    "user")
        cmd_user "$2"
        ;;
    "deletion")
        cmd_deletion "$2"
        ;;
    "orphans")
        cmd_orphans
        ;;
    "all")
        cmd_all
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac