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
  processing [document_id]     - Processing queue analysis (optionally for specific document)
  queue                        - Processing queue health and statistics
  document <id>                - Get document status and processing info
  specialized <id>             - Get specialized analysis results for document

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
  $0 processing 143                   # Check document 143 processing details
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

cmd_document() {
    local document_id=$1
    if [[ -z "$document_id" ]]; then
        log_error "Please provide a document ID"
        echo "Usage: $0 document <document_id>"
        exit 1
    fi
    
    log_section "Document Status Check"
    api_call "/deck/$document_id/status" "Document $document_id processing status (using legacy endpoint)"
}

cmd_specialized() {
    local document_id=$1
    if [[ -z "$document_id" ]]; then
        log_error "Please provide a document ID"
        echo "Usage: $0 specialized <document_id>"
        exit 1
    fi
    
    log_section "Specialized Analysis Results"
    api_call "/deck/$document_id/specialized-analysis" "Specialized analysis for document $document_id (clinical_validation, regulatory_pathway, scientific_hypothesis)"
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
    local document_id=$1
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
    
    if [[ -n "$document_id" ]]; then
        echo -e "\n${YELLOW}🔍 Document $document_id Processing Details${NC}"
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
            pd.processing_status as document_status,
            CASE WHEN pq.last_error IS NOT NULL THEN SUBSTRING(pq.last_error, 1, 100) || '...' ELSE 'No errors' END as error_preview
        FROM processing_queue pq
        LEFT JOIN project_documents pd ON pq.document_id = pd.id
        WHERE pq.document_id = $document_id
        ORDER BY pq.created_at DESC;
        " 2>/dev/null || log_error "Failed to get document processing details"
        
        echo -e "\n${YELLOW}📊 Processing Steps for Document $document_id${NC}"
        psql -h localhost -U review_user -d review-platform -c "
        SELECT 
            pp.step_name,
            pp.step_status,
            pp.progress_percentage,
            pp.message,
            pp.created_at
        FROM processing_progress pp
        JOIN processing_queue pq ON pp.processing_queue_id = pq.id
        WHERE pq.document_id = $document_id
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
        LEFT JOIN project_documents pd ON pq.document_id = pd.id
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
    LEFT JOIN project_documents pd ON pq.document_id = pd.id
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
    LEFT JOIN processing_queue pq ON pd.id = pq.document_id
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
                COUNT(*) as total_dojo_documents,
                COUNT(DISTINCT p.company_id) as unique_companies,
                COUNT(*) FILTER (WHERE pd.processing_status = 'completed') as processed,
                COUNT(*) FILTER (WHERE pd.processing_status = 'pending') as pending,
                COUNT(*) FILTER (WHERE pd.processing_status = 'failed') as failed,
                MAX(pd.upload_date) as latest_upload,
                MIN(pd.upload_date) as earliest_upload
            FROM project_documents pd
            LEFT JOIN projects p ON pd.project_id = p.id
            WHERE p.is_test = true OR p.company_id ILIKE '%dojo%';
            " 2>/dev/null || log_error "Database connection failed"
            
            echo -e "\n${YELLOW}🏢 Top Dojo Companies${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                p.company_id,
                COUNT(*) as document_count,
                COUNT(*) FILTER (WHERE pd.processing_status = 'completed') as processed_count,
                STRING_AGG(DISTINCT p.project_name, ', ') as project_names
            FROM project_documents pd
            LEFT JOIN projects p ON pd.project_id = p.id
            WHERE p.is_test = true OR p.company_id ILIKE '%dojo%'
            GROUP BY p.company_id
            ORDER BY document_count DESC
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
                COUNT(DISTINCT p.company_id) as unique_companies
            FROM visual_analysis_cache vac
            LEFT JOIN project_documents pd ON vac.document_id = pd.id
            LEFT JOIN projects p ON pd.project_id = p.id
            WHERE p.is_test = true OR p.company_id ILIKE '%dojo%'
            GROUP BY vac.vision_model_used
            ORDER BY cached_analyses DESC;
            " 2>/dev/null || log_error "Database connection failed"
            
            echo -e "\n${YELLOW}🔄 Cache vs Processing Status${NC}"
            psql -h localhost -U review_user -d review-platform -c "
            SELECT 
                pd.processing_status,
                COUNT(pd.id) as total_documents,
                COUNT(vac.id) as cached_analyses,
                ROUND(COUNT(vac.id)::DECIMAL / COUNT(pd.id) * 100, 1) as cache_percentage
            FROM project_documents pd
            LEFT JOIN projects p ON pd.project_id = p.id
            LEFT JOIN visual_analysis_cache vac ON pd.id = vac.document_id
            WHERE p.is_test = true OR p.company_id ILIKE '%dojo%'
            GROUP BY pd.processing_status
            ORDER BY total_documents DESC;
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
                'Dojo Project Documents' as data_type,
                COUNT(*) as count,
                ROUND(AVG(EXTRACT(EPOCH FROM (NOW() - pd.upload_date))/86400), 1) as avg_age_days
            FROM project_documents pd
            LEFT JOIN projects p ON pd.project_id = p.id
            WHERE p.is_test = true OR p.company_id ILIKE '%dojo%'
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
            LEFT JOIN project_documents pd ON vac.document_id = pd.id
            LEFT JOIN projects p ON pd.project_id = p.id
            WHERE p.is_test = true OR p.company_id ILIKE '%dojo%'
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
    
    # Sample document checks
    log_section "Sample Document Checks"
    for document_id in 140 143 144; do
        api_call "/deck/$document_id/status" "Document $document_id status (using legacy endpoint)" || true
    done
    
    log_section "Debug Report Complete"
    echo -e "\n${GREEN}✅ Comprehensive debug report completed successfully${NC}"
    echo -e "${BLUE}💡 Use specific commands for detailed analysis of any area${NC}"
}

# Parse command line arguments

# ═══════════════════════════════════════════════════════════════════════════════
# DOCUMENT REPROCESSING COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

cmd_clean_results() {
    local document_id=$1
    
    if [ -z "$document_id" ]; then
        log_error "Document ID required"
        echo "Usage: $0 clean-results <document_id>"
        exit 1
    fi
    
    print_header "Cleaning Processing Results for Document $document_id"
    
    log_info "⚠️  WARNING: This will delete all processing results for document $document_id"
    echo "This includes:"
    echo "  - Visual analysis cache"
    echo "  - Extraction experiments"
    echo "  - Specialized analysis results"
    echo "  - Processing queue entries"
    echo ""
    read -p "Are you sure you want to continue? (y/N): " confirm
    
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        log_warning "Operation cancelled"
        exit 0
    fi
    
    # Clean visual analysis cache
    log_info "Cleaning visual analysis cache..."
    sudo -u postgres psql -d review-platform -c "DELETE FROM visual_analysis_cache WHERE document_id = $document_id;" 2>/dev/null
    
    # Clean extraction experiments
    log_info "Cleaning extraction experiments..."
    sudo -u postgres psql -d review-platform -c "DELETE FROM extraction_experiments WHERE document_ids LIKE '%$document_id%';" 2>/dev/null
    
    # Clean specialized analysis
    log_info "Cleaning specialized analysis results..."
    sudo -u postgres psql -d review-platform -c "DELETE FROM specialized_analysis_results WHERE document_id = $document_id;" 2>/dev/null
    
    # Clean processing queue
    log_info "Cleaning processing queue entries..."
    sudo -u postgres psql -d review-platform -c "DELETE FROM processing_queue WHERE document_id = $document_id;" 2>/dev/null
    
    # Clean slide feedback
    log_info "Cleaning slide feedback..."
    sudo -u postgres psql -d review-platform -c "DELETE FROM slide_feedback WHERE document_id = $document_id;" 2>/dev/null
    
    log_success "✅ All processing results cleaned for document $document_id"
}

cmd_reprocess() {
    local document_id=$1
    
    if [ -z "$document_id" ]; then
        log_error "Document ID required"
        echo "Usage: $0 reprocess <document_id>"
        exit 1
    fi
    
    print_header "Reprocessing Document $document_id"
    
    # Step 1: Get document info
    log_info "Step 1: Retrieving document information..."
    local doc_info=$(sudo -u postgres psql -d review-platform -t -c "
        SELECT pd.file_name, pd.file_path, pd.project_id, p.company_name
        FROM project_documents pd
        JOIN projects p ON pd.project_id = p.id
        WHERE pd.id = $document_id;
    " 2>/dev/null)
    
    if [ -z "$doc_info" ]; then
        log_error "Document $document_id not found"
        exit 1
    fi
    
    IFS='|' read -r file_name file_path project_id company_name <<< "$doc_info"
    file_name=$(echo "$file_name" | xargs)
    file_path=$(echo "$file_path" | xargs)
    project_id=$(echo "$project_id" | xargs)
    company_name=$(echo "$company_name" | xargs)
    
    echo "📄 File: $file_name"
    echo "📁 Path: $file_path"
    echo "🏢 Project: $project_id ($company_name)"
    echo ""
    
    # Step 2: Clean existing results
    log_info "Step 2: Cleaning existing results..."
    
    # Clean without prompting
    sudo -u postgres psql -d review-platform -c "DELETE FROM visual_analysis_cache WHERE document_id = $document_id;" 2>/dev/null
    sudo -u postgres psql -d review-platform -c "DELETE FROM extraction_experiments WHERE document_ids LIKE '%$document_id%';" 2>/dev/null
    sudo -u postgres psql -d review-platform -c "DELETE FROM specialized_analysis_results WHERE document_id = $document_id;" 2>/dev/null
    sudo -u postgres psql -d review-platform -c "DELETE FROM slide_feedback WHERE document_id = $document_id;" 2>/dev/null
    
    # Clean failed/pending processing queue entries
    sudo -u postgres psql -d review-platform -c "DELETE FROM processing_queue WHERE document_id = $document_id AND status != 'processing';" 2>/dev/null
    
    log_success "✅ Existing results cleaned"
    
    # Step 3: Trigger processing directly via GPU
    log_info "Step 3: Triggering 4-step processing workflow..."
    
    # Get GPU server URL
    local gpu_url="http://135.181.63.133:8001"
    local backend_url="http://135.181.63.224:8000"
    local shared_path="/mnt/CPU-GPU"
    
    # Phase 1: Visual Analysis
    log_info "📊 Phase 1/4: Visual Analysis..."
    local visual_response=$(curl -s -X POST "$gpu_url/api/run-visual-analysis-batch" \
        -H "Content-Type: application/json" \
        -d "{
            \"deck_ids\": [$document_id],
            \"file_paths\": [\"$shared_path/$file_path\"],
            \"vision_model\": \"gemma3:27b\"
        }")
    
    if echo "$visual_response" | grep -q '"success":true'; then
        log_success "✅ Visual analysis completed"
    else
        log_error "❌ Visual analysis failed"
        echo "$visual_response" | jq .
        exit 1
    fi
    
    # Phase 2: Data Extraction
    log_info "📊 Phase 2/4: Data Extraction..."
    local extraction_response=$(curl -s -X POST "$gpu_url/api/run-extraction-experiment" \
        -H "Content-Type: application/json" \
        -d "{
            \"deck_ids\": [$document_id],
            \"experiment_name\": \"reprocess_$document_id\",
            \"extraction_type\": \"all\",
            \"text_model\": \"qwen3:30b\",
            \"processing_options\": {
                \"do_classification\": true,
                \"extract_company_name\": true,
                \"extract_funding_amount\": true,
                \"extract_deck_date\": true
            }
        }")
    
    if echo "$extraction_response" | grep -q '"success":true'; then
        log_success "✅ Data extraction completed"
    else
        log_error "❌ Data extraction failed"
        echo "$extraction_response" | jq .
        exit 1
    fi
    
    # Phase 3: Template Processing
    log_info "📊 Phase 3/4: Template Processing..."
    local template_response=$(curl -s -X POST "$gpu_url/api/run-template-processing-only" \
        -H "Content-Type: application/json" \
        -d "{
            \"deck_ids\": [$document_id],
            \"template_id\": 5,
            \"processing_options\": {
                \"generate_thumbnails\": true,
                \"callback_url\": \"$backend_url/api/internal/update-deck-results\"
            }
        }")
    
    if echo "$template_response" | grep -q '"success":true'; then
        log_success "✅ Template processing completed"
    else
        log_error "❌ Template processing failed"
        echo "$template_response" | jq .
        exit 1
    fi
    
    # Phase 4: Specialized Analysis
    log_info "📊 Phase 4/4: Specialized Analysis..."
    local specialized_response=$(curl -s -X POST "$gpu_url/api/run-specialized-analysis-only" \
        -H "Content-Type: application/json" \
        -d "{
            \"deck_ids\": [$document_id],
            \"processing_options\": {
                \"generate_thumbnails\": false,
                \"callback_url\": \"$backend_url/api/internal/update-deck-results\"
            }
        }")
    
    if echo "$specialized_response" | grep -q '"success":true'; then
        log_success "✅ Specialized analysis completed"
    else
        log_error "❌ Specialized analysis failed"
        echo "$specialized_response" | jq .
        exit 1
    fi
    
    # Step 4: Update document status
    log_info "Step 4: Updating document status..."
    sudo -u postgres psql -d review-platform -c "
        UPDATE project_documents 
        SET processing_status = 'completed'
        WHERE id = $document_id;
    " 2>/dev/null
    
    sudo -u postgres psql -d review-platform -c "
        UPDATE processing_queue 
        SET status = 'completed', completed_at = NOW(), progress_percentage = 100
        WHERE document_id = $document_id AND status != 'completed';
    " 2>/dev/null
    
    log_success "✅ Document status updated"
    
    # Step 5: Verify results
    log_info "Step 5: Verifying results..."
    echo ""
    echo "📊 Results Summary:"
    
    # Check visual analysis
    local visual_count=$(sudo -u postgres psql -d review-platform -t -c "
        SELECT COUNT(*) FROM visual_analysis_cache WHERE document_id = $document_id;
    " 2>/dev/null | xargs)
    echo "  • Visual Analysis Cache: $visual_count entries"
    
    # Check extraction
    local extraction_count=$(sudo -u postgres psql -d review-platform -t -c "
        SELECT COUNT(*) FROM extraction_experiments WHERE document_ids LIKE '%$document_id%';
    " 2>/dev/null | xargs)
    echo "  • Extraction Experiments: $extraction_count entries"
    
    # Check template processing
    local template_results=$(sudo -u postgres psql -d review-platform -t -c "
        SELECT template_processing_results_json IS NOT NULL 
        FROM extraction_experiments 
        WHERE document_ids LIKE '%$document_id%' 
        ORDER BY created_at DESC LIMIT 1;
    " 2>/dev/null | xargs)
    if [ "$template_results" = "t" ]; then
        echo "  • Template Processing: ✅ Saved"
    else
        echo "  • Template Processing: ❌ Not saved"
    fi
    
    # Check specialized analysis
    local specialized_count=$(sudo -u postgres psql -d review-platform -t -c "
        SELECT COUNT(*) FROM specialized_analysis_results WHERE document_id = $document_id;
    " 2>/dev/null | xargs)
    echo "  • Specialized Analysis: $specialized_count results"
    
    # Check slide feedback
    local feedback_count=$(sudo -u postgres psql -d review-platform -t -c "
        SELECT COUNT(*) FROM slide_feedback WHERE document_id = $document_id;
    " 2>/dev/null | xargs)
    echo "  • Slide Feedback: $feedback_count slides"
    
    echo ""
    log_success "🎉 Document $document_id reprocessed successfully!"
    echo ""
    echo "View results at: https://halbzeit.ai/project/$project_id/results/$document_id"
}

case "${1:-help}" in
    "health")
        cmd_health
        ;;
    "document")
        cmd_document "$2"
        ;;
    "deck")
        # Legacy support - redirect to document command
        cmd_document "$2"
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
    "reprocess")
        cmd_reprocess "$2"
        ;;
    "clean-results")
        cmd_clean_results "$2"
        ;;
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
        echo "Processing: processing, queue, document, specialized"
        echo "Projects: project, project-docs, user, invitations, deletion, orphans"
        echo "Dojo: dojo [stats|experiments|cache|projects|cleanup]"
        echo "Templates: templates [list|performance|sectors|customizations]"
        echo "Reprocessing: reprocess <id>, clean-results <id>"
        echo "Utility: all, help"
        echo ""
        echo "Run '$0 help' for detailed usage information."
        exit 1
        ;;
esac