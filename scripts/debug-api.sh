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

# Database configuration for production
export PGPASSWORD="simpleprod2024"

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
🛠️  HALBZEIT API Debug Helper - COMPREHENSIVE EDITION

This script provides extensive debugging capabilities without authentication.

Usage: $0 [command] [options]

📊 SYSTEM & ENVIRONMENT:
  health                       - Detailed health check
  env                          - Show environment configuration
  tables                       - List all database tables
  table <name>                 - Get table structure and info
  models                       - Show AI model configuration
  prompts [stage]              - Show pipeline prompts (all stages or specific)

🔧 PROCESSING & DOCUMENTS:
  processing [deck_id]         - Processing queue analysis (optionally for specific deck)
  queue                        - Processing queue health and statistics
  deck <id>                    - Get deck status and processing info
  specialized <id>             - Get specialized analysis results for deck

🏗️ PROJECTS & USERS:
  project <id>                 - Analyze project data and relationships
  project-docs <id>            - Analyze project document processing pipeline
  user <email>                 - Analyze user relationships and dependencies
  invitations <email|project>  - Debug invitation flow (by email or project ID)
  deletion <id>                - Preview project deletion impact
  orphans                      - List and analyze orphaned projects

🧪 DOJO & EXPERIMENTS:
  dojo stats                   - Dojo system statistics
  dojo experiments             - Active extraction experiments
  dojo cache                   - Visual analysis cache status
  dojo projects                - Dojo test projects
  dojo cleanup                 - Cleanup analysis and storage impact

🏥 HEALTHCARE TEMPLATES:
  templates list               - Available healthcare templates
  templates performance        - Template usage and performance metrics
  templates sectors            - Healthcare sectors and classification
  templates customizations     - GP template customizations

⚡ QUICK ACTIONS:
  all                          - Run comprehensive debug report
  help                         - Show this help

Examples:
  $0 health                           # System health check
  $0 processing 143                   # Check deck 143 processing details
  $0 queue                            # Processing queue health
  $0 project-docs 31                  # Analyze project 31 document pipeline
  $0 invitations user@startup.com     # Check user's invitations
  $0 invitations 42                   # Check project 42 invitations
  $0 dojo experiments                 # Show active experiments
  $0 templates performance            # Template usage metrics
  $0 models                           # AI model configuration

🌐 Debug Endpoints (API + Database):
  Authentication-free API endpoints:
  • GET /api/debug/health-detailed
  • GET /api/debug/processing/queue-stats
  • GET /api/debug/processing/deck/{id}
  • GET /api/debug/dojo/experiments-summary
  • GET /api/debug/templates/performance
  • GET /api/debug/models/config
  
  Direct database queries (no API endpoints needed):
  • Project analysis, user relationships, invitation flows
  • Dojo experiments, template analysis, configuration debugging

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
    psql -h localhost -U review_user -d review-platform -c "
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
    psql -h localhost -U review_user -d review-platform -c "
    SELECT file_name, document_type, processing_status, upload_date, 
           CASE WHEN uploaded_by IS NOT NULL THEN 'User ' || uploaded_by ELSE 'System' END as uploader
    FROM project_documents 
    WHERE project_id = $project_id 
    ORDER BY upload_date DESC;
    " 2>/dev/null || true
    
    echo -e "\n${YELLOW}👥 Project Members${NC}"
    psql -h localhost -U review_user -d review-platform -c "
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
    psql -h localhost -U review_user -d review-platform -c "
    SELECT id, email, role, company_name, is_verified, created_at, last_login
    FROM users 
    WHERE email = '$user_email';
    " 2>/dev/null || log_error "Database connection failed"
    
    echo -e "\n${YELLOW}🏗️ Project Memberships${NC}"
    psql -h localhost -U review_user -d review-platform -c "
    SELECT p.id, p.company_id, p.project_name, pm.role, pm.added_at
    FROM project_members pm
    JOIN projects p ON pm.project_id = p.id
    JOIN users u ON pm.user_id = u.id
    WHERE u.email = '$user_email';
    " 2>/dev/null || true
    
    echo -e "\n${YELLOW}📧 Pending Invitations${NC}"
    psql -h localhost -U review_user -d review-platform -c "
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
    psql -h localhost -U review_user -d review-platform -c "
    SELECT file_name, file_path, file_size, document_type
    FROM project_documents
    WHERE project_id = $project_id;
    " 2>/dev/null || true
    
    echo -e "\n${YELLOW}👥 Users that might be deleted${NC}"
    echo -e "${BLUE}(Only users who ONLY belong to this project)${NC}"
    psql -h localhost -U review_user -d review-platform -c "
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
    psql -h localhost -U review_user -d review-platform -c "
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
    psql -h localhost -U review_user -d review-platform -c "
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

# NEW: Processing Queue Analysis
cmd_processing() {
    local deck_id=$1
    log_section "Document Processing Analysis"
    
    echo -e "\n${YELLOW}📄 Processing Queue Status${NC}"
    psql -h localhost -U review_user -d review-platform -c "
    SELECT 
        status, 
        COUNT(*) as count, 
        ROUND(AVG(progress_percentage), 1) as avg_progress,
        ROUND(AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, NOW()) - created_at))/60), 1) as avg_duration_min
    FROM processing_queue 
    GROUP BY status 
    ORDER BY count DESC;
    " 2>/dev/null || log_error "Database connection failed"
    
    if [[ -n "$deck_id" ]]; then
        echo -e "\n${YELLOW}🔍 Deck $deck_id Processing Details${NC}"
        psql -h localhost -U review_user -d review-platform -c "
        SELECT 
            pq.status, 
            pq.progress_percentage, 
            pq.current_step, 
            pq.progress_message,
            pq.retry_count,
            pq.created_at, 
            pq.started_at, 
            pq.completed_at,
            pd.file_name, 
            pd.processing_status as deck_status,
            CASE WHEN pq.last_error IS NOT NULL THEN SUBSTRING(pq.last_error, 1, 100) || '...' ELSE 'No errors' END as error_preview
        FROM processing_queue pq
        JOIN pitch_decks pd ON pq.pitch_deck_id = pd.id
        WHERE pq.pitch_deck_id = $deck_id
        ORDER BY pq.created_at DESC;
        " 2>/dev/null || log_error "Failed to get deck processing details"
        
        echo -e "\n${YELLOW}📊 Processing Steps for Deck $deck_id${NC}"
        psql -h localhost -U review_user -d review-platform -c "
        SELECT 
            pp.step_name,
            pp.step_status,
            pp.progress_percentage,
            pp.message,
            pp.created_at
        FROM processing_progress pp
        JOIN processing_queue pq ON pp.processing_queue_id = pq.id
        WHERE pq.pitch_deck_id = $deck_id
        ORDER BY pp.created_at DESC
        LIMIT 10;
        " 2>/dev/null || true
    else
        echo -e "\n${YELLOW}🔥 Recent Processing Activity${NC}"
        psql -h localhost -U review_user -d review-platform -c "
        SELECT 
            pd.file_name,
            pq.status,
            pq.progress_percentage,
            pq.current_step,
            pq.created_at,
            CASE WHEN pq.last_error IS NOT NULL THEN '❌' ELSE '✅' END as has_errors
        FROM processing_queue pq
        JOIN pitch_decks pd ON pq.pitch_deck_id = pd.id
        ORDER BY pq.created_at DESC
        LIMIT 15;
        " 2>/dev/null || true
    fi
}

cmd_queue() {
    log_section "Processing Queue Health"
    
    echo -e "\n${YELLOW}⚡ Queue Statistics${NC}"
    psql -h localhost -U review_user -d review-platform -c "
    SELECT 
        COUNT(*) as total_tasks,
        COUNT(*) FILTER (WHERE status = 'queued') as queued,
        COUNT(*) FILTER (WHERE status = 'processing') as processing,
        COUNT(*) FILTER (WHERE status = 'completed') as completed,
        COUNT(*) FILTER (WHERE status = 'failed') as failed,
        COUNT(*) FILTER (WHERE status = 'retry') as retry,
        ROUND(AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, NOW()) - created_at))/60), 1) as avg_duration_minutes
    FROM processing_queue;
    " 2>/dev/null || log_error "Database connection failed"
    
    echo -e "\n${YELLOW}🚨 Failed Tasks (Last 10)${NC}"
    psql -h localhost -U review_user -d review-platform -c "
    SELECT 
        pd.file_name,
        pq.retry_count,
        pq.created_at,
        SUBSTRING(pq.last_error, 1, 100) || '...' as error_preview
    FROM processing_queue pq
    JOIN pitch_decks pd ON pq.pitch_deck_id = pd.id
    WHERE pq.status = 'failed'
    ORDER BY pq.created_at DESC
    LIMIT 10;
    " 2>/dev/null || true
    
    echo -e "\n${YELLOW}🔄 Processing Servers${NC}"
    psql -h localhost -U review_user -d review-platform -c "
    SELECT 
        id as server_id,
        server_type,
        status,
        current_load,
        max_concurrent_tasks,
        last_heartbeat,
        EXTRACT(EPOCH FROM (NOW() - last_heartbeat))/60 as minutes_since_heartbeat
    FROM processing_servers
    ORDER BY last_heartbeat DESC;
    " 2>/dev/null || log_warning "No processing server data found"
}

# NEW: Enhanced Project Document Analysis
cmd_project_docs() {
    local project_id=$1
    if [[ -z "$project_id" ]]; then
        log_error "Please provide a project ID"
        echo "Usage: $0 project-docs <project_id>"
        exit 1
    fi
    
    log_section "Project Document Analysis"
    
    echo -e "\n${YELLOW}📎 Document Processing Pipeline${NC}"
    psql -h localhost -U review_user -d review-platform -c "
    SELECT 
        pd.file_name,
        pd.document_type,
        pd.processing_status,
        pq.status as queue_status,
        pq.progress_percentage,
        pq.current_step,
        pd.upload_date,
        pq.created_at as queued_at,
        CASE WHEN pq.last_error IS NOT NULL THEN '❌' ELSE '✅' END as has_errors
    FROM project_documents pd
    LEFT JOIN processing_queue pq ON pd.reference_pitch_deck_id = pq.pitch_deck_id
    WHERE pd.project_id = $project_id
    ORDER BY pd.upload_date DESC;
    " 2>/dev/null || log_error "Failed to get project documents"
    
    echo -e "\n${YELLOW}📊 Analysis Results Status${NC}"
    psql -h localhost -U review_user -d review-platform -c "
    SELECT 
        pd.file_name,
        COUNT(DISTINCT sar.id) as specialized_analyses,
        COUNT(DISTINCT vac.id) as visual_cache_entries,
        COUNT(DISTINCT r.id) as reviews,
        COUNT(DISTINCT sf.id) as slide_feedback
    FROM project_documents pd
    LEFT JOIN specialized_analysis_results sar ON pd.reference_pitch_deck_id = sar.pitch_deck_id
    LEFT JOIN visual_analysis_cache vac ON pd.reference_pitch_deck_id = vac.pitch_deck_id
    LEFT JOIN reviews r ON pd.reference_pitch_deck_id = r.pitch_deck_id
    LEFT JOIN slide_feedback sf ON pd.reference_pitch_deck_id = sf.pitch_deck_id
    WHERE pd.project_id = $project_id
    GROUP BY pd.id, pd.file_name
    ORDER BY pd.file_name;
    " 2>/dev/null || true
}

# NEW: Invitation Flow Debugging
cmd_invitations() {
    local email_or_project=$1
    if [[ -z "$email_or_project" ]]; then
        log_error "Please provide an email address or project ID"
        echo "Usage: $0 invitations <email@example.com> OR $0 invitations <project_id>"
        exit 1
    fi
    
    log_section "Invitation Flow Analysis"
    
    if [[ "$email_or_project" =~ @ ]]; then
        log_info "Analyzing invitations for user: $email_or_project"
        
        echo -e "\n${YELLOW}📧 Invitations for $email_or_project${NC}"
        psql -h localhost -U review_user -d review-platform -c "
        SELECT 
            p.project_name,
            p.company_id,
            pi.status,
            pi.created_at,
            pi.expires_at,
            pi.accepted_at,
            u.email as invited_by,
            CASE 
                WHEN pi.expires_at < NOW() THEN '🕒 Expired'
                WHEN pi.status = 'accepted' THEN '✅ Accepted'
                WHEN pi.status = 'pending' THEN '⏳ Pending'
                ELSE '❓ ' || pi.status
            END as status_icon
        FROM project_invitations pi
        JOIN projects p ON pi.project_id = p.id
        JOIN users u ON pi.invited_by_id = u.id
        WHERE pi.email = '$email_or_project'
        ORDER BY pi.created_at DESC;
        " 2>/dev/null || log_error "Database connection failed"
        
        echo -e "\n${YELLOW}👤 User Registration Status${NC}"
        psql -h localhost -U review_user -d review-platform -c "
        SELECT 
            email,
            role,
            is_verified,
            created_at,
            last_login,
            CASE 
                WHEN is_verified THEN '✅ Verified'
                ELSE '❌ Not Verified'
            END as verification_status
        FROM users 
        WHERE email = '$email_or_project';
        " 2>/dev/null || log_info "User not registered yet"
        
    else
        log_info "Analyzing invitations for project: $email_or_project"
        
        echo -e "\n${YELLOW}📧 Invitations for Project $email_or_project${NC}"
        psql -h localhost -U review_user -d review-platform -c "
        SELECT 
            pi.email,
            pi.status,
            pi.created_at,
            pi.expires_at,
            pi.accepted_at,
            u.email as invited_by,
            CASE 
                WHEN pi.expires_at < NOW() THEN '🕒 Expired'
                WHEN pi.status = 'accepted' THEN '✅ Accepted'
                WHEN pi.status = 'pending' THEN '⏳ Pending'
                ELSE '❓ ' || pi.status
            END as status_icon
        FROM project_invitations pi
        JOIN users u ON pi.invited_by_id = u.id
        WHERE pi.project_id = $email_or_project
        ORDER BY pi.created_at DESC;
        " 2>/dev/null || log_error "Database connection failed"
        
        echo -e "\n${YELLOW}👥 Current Project Members${NC}"
        psql -h localhost -U review_user -d review-platform -c "
        SELECT 
            u.email,
            pm.role,
            pm.added_at,
            u.last_login,
            CASE 
                WHEN u.last_login IS NOT NULL THEN '🟢 Active'
                ELSE '🔴 Never Logged In'
            END as activity_status
        FROM project_members pm
        JOIN users u ON pm.user_id = u.id
        WHERE pm.project_id = $email_or_project
        ORDER BY pm.added_at DESC;
        " 2>/dev/null || true
    fi
}

# NEW: Dojo Experiment Debugging
cmd_dojo() {
    local action=${1:-"stats"}
    log_section "Dojo Experimental System"
    
    case "$action" in
        "stats")
            echo -e "\n${YELLOW}📊 Dojo Statistics${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                COUNT(*) as total_dojo_decks,
                COUNT(DISTINCT company_id) as unique_companies,
                COUNT(*) FILTER (WHERE processing_status = 'completed') as processed,
                COUNT(*) FILTER (WHERE processing_status = 'pending') as pending,
                COUNT(*) FILTER (WHERE processing_status = 'failed') as failed,
                MAX(created_at) as latest_upload,
                MIN(created_at) as earliest_upload
            FROM pitch_decks WHERE data_source = 'dojo';
            " 2>/dev/null || log_error "Database connection failed"
            
            echo -e "\n${YELLOW}🏢 Top Dojo Companies${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                company_id,
                COUNT(*) as deck_count,
                COUNT(*) FILTER (WHERE processing_status = 'completed') as processed_count,
                STRING_AGG(DISTINCT ai_extracted_startup_name, ', ') as startup_names
            FROM pitch_decks 
            WHERE data_source = 'dojo'
            GROUP BY company_id
            ORDER BY deck_count DESC
            LIMIT 10;
            " 2>/dev/null || true
            ;;
            
        "experiments")
            echo -e "\n${YELLOW}🧪 Active Experiments${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                experiment_name,
                extraction_type, 
                array_length(string_to_array(pitch_deck_ids, ','), 1) as deck_count,
                text_model_used,
                created_at,
                CASE WHEN classification_results_json IS NOT NULL THEN '✅' ELSE '❌' END as classification,
                CASE WHEN company_name_results_json IS NOT NULL THEN '✅' ELSE '❌' END as company_names,
                CASE WHEN funding_amount_results_json IS NOT NULL THEN '✅' ELSE '❌' END as funding_amounts,
                CASE WHEN template_processing_results_json IS NOT NULL THEN '✅' ELSE '❌' END as template_processing
            FROM extraction_experiments 
            ORDER BY created_at DESC 
            LIMIT 15;
            " 2>/dev/null || log_error "Database connection failed"
            
            echo -e "\n${YELLOW}📈 Experiment Progress Summary${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                COUNT(*) as total_experiments,
                COUNT(*) FILTER (WHERE classification_results_json IS NOT NULL) as with_classification,
                COUNT(*) FILTER (WHERE company_name_results_json IS NOT NULL) as with_company_names,
                COUNT(*) FILTER (WHERE funding_amount_results_json IS NOT NULL) as with_funding_amounts,
                COUNT(*) FILTER (WHERE template_processing_results_json IS NOT NULL) as with_template_processing,
                ROUND(AVG(array_length(string_to_array(pitch_deck_ids, ','), 1)), 1) as avg_deck_count_per_experiment
            FROM extraction_experiments;
            " 2>/dev/null || true
            ;;
            
        "cache")
            echo -e "\n${YELLOW}💾 Visual Analysis Cache${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                vac.vision_model_used, 
                COUNT(*) as cached_analyses,
                MAX(vac.created_at) as latest_cache,
                COUNT(DISTINCT pd.company_id) as unique_companies
            FROM visual_analysis_cache vac
            JOIN pitch_decks pd ON vac.pitch_deck_id = pd.id
            WHERE pd.data_source = 'dojo'
            GROUP BY vac.vision_model_used
            ORDER BY cached_analyses DESC;
            " 2>/dev/null || log_error "Database connection failed"
            
            echo -e "\n${YELLOW}🔄 Cache vs Processing Status${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                pd.processing_status,
                COUNT(pd.id) as total_decks,
                COUNT(vac.id) as cached_analyses,
                ROUND(COUNT(vac.id)::DECIMAL / COUNT(pd.id) * 100, 1) as cache_percentage
            FROM pitch_decks pd
            LEFT JOIN visual_analysis_cache vac ON pd.id = vac.pitch_deck_id
            WHERE pd.data_source = 'dojo'
            GROUP BY pd.processing_status
            ORDER BY total_decks DESC;
            " 2>/dev/null || true
            ;;
            
        "projects")
            echo -e "\n${YELLOW}🏗️ Dojo Test Projects${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                p.company_id,
                p.project_name,
                p.is_active,
                COUNT(DISTINCT pd.id) as document_count,
                COUNT(DISTINCT pm.id) as member_count,
                COUNT(DISTINCT pi.id) as invitation_count,
                p.created_at
            FROM projects p
            LEFT JOIN project_documents pd ON p.id = pd.project_id
            LEFT JOIN project_members pm ON p.id = pm.project_id
            LEFT JOIN project_invitations pi ON p.id = pi.project_id
            WHERE p.is_test = true OR p.company_id ILIKE '%dojo%'
            GROUP BY p.id, p.company_id, p.project_name, p.is_active, p.created_at
            ORDER BY p.created_at DESC
            LIMIT 20;
            " 2>/dev/null || log_error "Database connection failed"
            ;;
            
        "cleanup")
            echo -e "\n${YELLOW}🧹 Cleanup Analysis${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                'Dojo Pitch Decks' as data_type,
                COUNT(*) as count,
                ROUND(AVG(EXTRACT(EPOCH FROM (NOW() - created_at))/86400), 1) as avg_age_days
            FROM pitch_decks WHERE data_source = 'dojo'
            UNION ALL
            SELECT 
                'Test Projects' as data_type,
                COUNT(*) as count,
                ROUND(AVG(EXTRACT(EPOCH FROM (NOW() - created_at))/86400), 1) as avg_age_days
            FROM projects WHERE is_test = true
            UNION ALL
            SELECT 
                'Extraction Experiments' as data_type,
                COUNT(*) as count,
                ROUND(AVG(EXTRACT(EPOCH FROM (NOW() - created_at))/86400), 1) as avg_age_days
            FROM extraction_experiments;
            " 2>/dev/null || true
            
            echo -e "\n${YELLOW}💾 Storage Impact${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                'Dojo Visual Cache' as cache_type,
                COUNT(*) as entries,
                ROUND(SUM(LENGTH(analysis_result_json))/1024.0/1024.0, 2) as size_mb
            FROM visual_analysis_cache vac
            JOIN pitch_decks pd ON vac.pitch_deck_id = pd.id
            WHERE pd.data_source = 'dojo'
            UNION ALL
            SELECT 
                'Extraction Results' as cache_type,
                COUNT(*) as entries,
                ROUND(SUM(LENGTH(results_json))/1024.0/1024.0, 2) as size_mb
            FROM extraction_experiments;
            " 2>/dev/null || true
            ;;
            
        *)
            log_error "Unknown dojo action: $action"
            echo "Available actions: stats, experiments, cache, projects, cleanup"
            exit 1
            ;;
    esac
}

# NEW: Healthcare Template Analysis
cmd_templates() {
    local action=${1:-"list"}
    log_section "Healthcare Template Analysis"
    
    case "$action" in
        "list")
            echo -e "\n${YELLOW}🏥 Available Templates${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                t.id,
                t.name, 
                s.display_name as sector, 
                t.is_active, 
                COALESCE(t.usage_count, 0) as usage_count,
                COUNT(DISTINCT tc.id) as chapters,
                COUNT(DISTINCT cq.id) as questions,
                t.created_at
            FROM analysis_templates t
            LEFT JOIN healthcare_sectors s ON t.healthcare_sector_id = s.id
            LEFT JOIN template_chapters tc ON t.id = tc.template_id
            LEFT JOIN chapter_questions cq ON tc.id = cq.chapter_id
            WHERE t.is_active = true
            GROUP BY t.id, t.name, s.display_name, t.is_active, t.usage_count, t.created_at
            ORDER BY t.usage_count DESC NULLS LAST, t.created_at DESC;
            " 2>/dev/null || log_error "Database connection failed"
            ;;
            
        "performance")
            echo -e "\n${YELLOW}📈 Template Performance${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                t.name,
                t.healthcare_sector_id,
                COUNT(tp.id) as usage_count,
                ROUND(AVG(tp.total_processing_time), 2) as avg_processing_time,
                ROUND(AVG(tp.average_confidence), 2) as avg_confidence,
                ROUND(AVG(tp.gp_rating), 1) as avg_gp_rating,
                COUNT(tp.gp_feedback) FILTER (WHERE tp.gp_feedback IS NOT NULL) as feedback_count
            FROM analysis_templates t
            LEFT JOIN template_performance tp ON t.id = tp.template_id
            WHERE t.is_active = true
            GROUP BY t.id, t.name, t.healthcare_sector_id
            HAVING COUNT(tp.id) > 0
            ORDER BY avg_gp_rating DESC NULLS LAST, usage_count DESC;
            " 2>/dev/null || log_warning "No performance data found"
            
            echo -e "\n${YELLOW}🎯 Template Usage by Sector${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                s.display_name as sector,
                COUNT(DISTINCT t.id) as available_templates,
                COUNT(tp.id) as total_usage,
                ROUND(AVG(tp.gp_rating), 1) as avg_rating
            FROM healthcare_sectors s
            LEFT JOIN analysis_templates t ON s.id = t.healthcare_sector_id AND t.is_active = true
            LEFT JOIN template_performance tp ON t.id = tp.template_id
            GROUP BY s.id, s.display_name
            HAVING COUNT(DISTINCT t.id) > 0
            ORDER BY total_usage DESC NULLS LAST;
            " 2>/dev/null || true
            ;;
            
        "sectors")
            echo -e "\n${YELLOW}🏥 Healthcare Sectors${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                s.id,
                s.display_name, 
                s.is_active,
                COUNT(DISTINCT sc.id) as classified_companies,
                COUNT(DISTINCT t.id) as available_templates,
                ROUND(s.confidence_threshold, 2) as confidence_threshold
            FROM healthcare_sectors s
            LEFT JOIN startup_classifications sc ON s.id = sc.primary_sector_id
            LEFT JOIN analysis_templates t ON s.id = t.healthcare_sector_id AND t.is_active = true
            WHERE s.is_active = true
            GROUP BY s.id, s.display_name, s.is_active, s.confidence_threshold
            ORDER BY classified_companies DESC NULLS LAST, available_templates DESC;
            " 2>/dev/null || log_error "Database connection failed"
            
            echo -e "\n${YELLOW}📊 Classification Accuracy${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                s.display_name as sector,
                COUNT(cp.id) as performance_records,
                COUNT(cp.id) FILTER (WHERE cp.was_accurate = true) as accurate_classifications,
                ROUND(COUNT(cp.id) FILTER (WHERE cp.was_accurate = true)::DECIMAL / COUNT(cp.id) * 100, 1) as accuracy_percentage,
                COUNT(cp.id) FILTER (WHERE cp.manual_correction_from IS NOT NULL) as manual_corrections
            FROM healthcare_sectors s
            LEFT JOIN startup_classifications sc ON s.id = sc.primary_sector_id
            LEFT JOIN classification_performance cp ON sc.id = cp.classification_id
            GROUP BY s.id, s.display_name
            HAVING COUNT(cp.id) > 0
            ORDER BY accuracy_percentage DESC NULLS LAST;
            " 2>/dev/null || log_warning "No classification performance data found"
            ;;
            
        "customizations")
            echo -e "\n${YELLOW}⚙️ GP Template Customizations${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                gtc.gp_email,
                t.name as base_template,
                gtc.customization_name,
                gtc.is_active,
                gtc.created_at,
                gtc.modified_at
            FROM gp_template_customizations gtc
            JOIN analysis_templates t ON gtc.base_template_id = t.id
            WHERE gtc.is_active = true
            ORDER BY gtc.modified_at DESC
            LIMIT 20;
            " 2>/dev/null || log_info "No template customizations found"
            ;;
            
        *)
            log_error "Unknown templates action: $action"
            echo "Available actions: list, performance, sectors, customizations"
            exit 1
            ;;
    esac
}

# NEW: Model and Prompt Configuration
cmd_models() {
    log_section "AI Model Configuration"
    
    echo -e "\n${YELLOW}🤖 Active Models${NC}"
    psql -h localhost -U review_user -d review-platform -c "
    SELECT 
        model_type,
        model_name,
        is_active,
        created_at,
        updated_at,
        CASE 
            WHEN is_active THEN '🟢 Active'
            ELSE '🔴 Inactive'
        END as status
    FROM model_configs 
    ORDER BY model_type, is_active DESC, updated_at DESC;
    " 2>/dev/null || log_error "Database connection failed"
    
    echo -e "\n${YELLOW}📊 Model Usage by Type${NC}"
    psql -h localhost -U review_user -d review-platform -c "
    SELECT 
        model_type,
        COUNT(*) as total_models,
        COUNT(*) FILTER (WHERE is_active = true) as active_models,
        MAX(updated_at) as last_updated
    FROM model_configs
    GROUP BY model_type
    ORDER BY total_models DESC;
    " 2>/dev/null || true
}

cmd_prompts() {
    local stage=${1:-"all"}
    log_section "Pipeline Prompt Analysis"
    
    if [[ "$stage" == "all" ]]; then
        echo -e "\n${YELLOW}📝 All Pipeline Prompts${NC}"
        psql -h localhost -U review_user -d review-platform -c "
        SELECT 
            stage_name,
            is_active,
            created_by,
            SUBSTRING(prompt_text, 1, 80) || '...' as prompt_preview,
            LENGTH(prompt_text) as prompt_length,
            created_at,
            updated_at,
            CASE 
                WHEN is_active THEN '🟢 Active'
                ELSE '🔴 Inactive'
            END as status
        FROM pipeline_prompts
        ORDER BY stage_name, is_active DESC, updated_at DESC;
        " 2>/dev/null || log_error "Database connection failed"
        
        echo -e "\n${YELLOW}📊 Prompt Statistics${NC}"
        psql -h localhost -U review_user -d review-platform -c "
        SELECT 
            COUNT(*) as total_prompts,
            COUNT(*) FILTER (WHERE is_active = true) as active_prompts,
            COUNT(DISTINCT stage_name) as unique_stages,
            ROUND(AVG(LENGTH(prompt_text)), 0) as avg_prompt_length,
            MAX(updated_at) as last_updated
        FROM pipeline_prompts;
        " 2>/dev/null || true
        
    else
        echo -e "\n${YELLOW}📝 Prompt for Stage: $stage${NC}"
        psql -h localhost -U review_user -d review-platform -c "
        SELECT 
            stage_name,
            is_active,
            created_by,
            LENGTH(prompt_text) as prompt_length,
            created_at,
            updated_at,
            prompt_text
        FROM pipeline_prompts 
        WHERE stage_name = '$stage'
        ORDER BY is_active DESC, updated_at DESC;
        " 2>/dev/null || log_error "No prompt found for stage: $stage"
    fi
}

cmd_all() {
    log_section "Comprehensive Debug Report"
    
    # Core system checks
    cmd_health
    cmd_env
    cmd_models
    
    # Database overview
    cmd_tables
    
    # Processing system
    cmd_queue
    
    # Project system
    cmd_orphans
    
    # Dojo experiments
    cmd_dojo stats
    
    # Template system
    cmd_templates list
    
    # Sample deck checks
    log_section "Sample Deck Checks"
    for deck_id in 140 143 144; do
        api_call "/deck/$deck_id/status" "Deck $deck_id status" || true
    done
    
    log_section "Debug Report Complete"
    echo -e "\n${GREEN}✅ Comprehensive debug report completed successfully${NC}"
    echo -e "${BLUE}💡 Use specific commands for detailed analysis of any area${NC}"
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
    # Processing & Queue Commands
    "processing")
        cmd_processing "$2"
        ;;
    "queue")
        cmd_queue
        ;;
    # Project & User Commands
    "project")
        cmd_project "$2"
        ;;
    "project-docs")
        cmd_project_docs "$2"
        ;;
    "user")
        cmd_user "$2"
        ;;
    "invitations")
        cmd_invitations "$2"
        ;;
    "deletion")
        cmd_deletion "$2"
        ;;
    "orphans")
        cmd_orphans
        ;;
    # Dojo Commands
    "dojo")
        cmd_dojo "$2"
        ;;
    # Template Commands
    "templates")
        cmd_templates "$2"
        ;;
    # Model & Prompt Commands
    "models")
        cmd_models
        ;;
    "prompts")
        cmd_prompts "$2"
        ;;
    # Utility Commands
    "all")
        cmd_all
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo ""
        echo "Available commands:"
        echo "System: health, env, tables, table, models, prompts"
        echo "Processing: processing, queue, deck, specialized"
        echo "Projects: project, project-docs, user, invitations, deletion, orphans"
        echo "Dojo: dojo [stats|experiments|cache|projects|cleanup]"
        echo "Templates: templates [list|performance|sectors|customizations]"
        echo "Utility: all, help"
        echo ""
        echo "Run '$0 help' for detailed usage information."
        exit 1
        ;;
esac