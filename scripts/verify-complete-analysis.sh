#!/bin/bash

# ═══════════════════════════════════════════════════════════════════════════════
# COMPREHENSIVE DOCUMENT ANALYSIS VERIFICATION SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m' 
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_section() { echo -e "\n${BLUE}═══════════════════════════════════════════════${NC}\n${BLUE}► $1${NC}\n${BLUE}═══════════════════════════════════════════════${NC}"; }

# Database connection function
db_query() {
    sudo -u postgres psql -d review-platform -t -c "$1" 2>/dev/null
}

# Main verification function
verify_document_analysis() {
    local document_id=$1
    local expected_phases=${2:-"all"}  # all, basic, template-only
    
    if [ -z "$document_id" ]; then
        log_error "Document ID required"
        echo "Usage: $0 <document_id> [expected_phases]"
        echo "  expected_phases: all (default), basic, template-only"
        exit 1
    fi
    
    log_section "Comprehensive Analysis Verification for Document $document_id"
    
    # ==============================================================================
    # PHASE 0: DOCUMENT EXISTENCE & INFO
    # ==============================================================================
    
    log_info "Phase 0: Document Information"
    
    local doc_info=$(db_query "
        SELECT pd.file_name, pd.file_path, pd.processing_status, pd.project_id, p.company_id
        FROM project_documents pd
        JOIN projects p ON pd.project_id = p.id
        WHERE pd.id = $document_id;
    ")
    
    if [ -z "$doc_info" ]; then
        log_error "Document $document_id not found in database"
        return 1
    fi
    
    IFS='|' read -r file_name file_path processing_status project_id company_id <<< "$doc_info"
    file_name=$(echo "$file_name" | xargs)
    file_path=$(echo "$file_path" | xargs)
    processing_status=$(echo "$processing_status" | xargs)
    project_id=$(echo "$project_id" | xargs)
    company_id=$(echo "$company_id" | xargs)
    
    echo "📄 File: $file_name"
    echo "📁 Path: $file_path"
    echo "📊 Status: $processing_status"
    echo "🏢 Project: $project_id ($company_id)"
    
    # ==============================================================================
    # PHASE 1: VISUAL ANALYSIS VERIFICATION
    # ==============================================================================
    
    log_info "Phase 1: Visual Analysis Verification"
    
    # Check visual analysis cache
    local visual_count=$(db_query "SELECT COUNT(*) FROM visual_analysis_cache WHERE document_id = $document_id;" | xargs)
    local visual_pages=$(db_query "
        SELECT COALESCE(json_array_length(analysis_result_json::json->'visual_analysis_results'), 0)
        FROM visual_analysis_cache 
        WHERE document_id = $document_id 
        ORDER BY created_at DESC 
        LIMIT 1;
    " | xargs)
    
    if [ "$visual_count" -gt 0 ] && [ "$visual_pages" -gt 0 ]; then
        log_success "Visual analysis complete: $visual_pages pages analyzed"
    else
        log_error "Visual analysis missing or incomplete (count: $visual_count, pages: $visual_pages)"
    fi
    
    # Check slide feedback
    local feedback_count=$(db_query "SELECT COUNT(*) FROM slide_feedback WHERE document_id = $document_id;" | xargs)
    local feedback_slides=$(db_query "SELECT COUNT(DISTINCT slide_number) FROM slide_feedback WHERE document_id = $document_id;" | xargs)
    
    if [ "$feedback_count" -gt 0 ]; then
        log_success "Slide feedback complete: $feedback_count feedback entries for $feedback_slides slides"
    else
        log_error "Slide feedback missing (expected detailed feedback for each slide)"
    fi
    
    # ==============================================================================
    # PHASE 2: EXTRACTION RESULTS VERIFICATION
    # ==============================================================================
    
    log_info "Phase 2: Data Extraction Verification"
    
    local extraction_count=$(db_query "SELECT COUNT(*) FROM extraction_experiments WHERE document_ids LIKE '%$document_id%';" | xargs)
    
    if [ "$extraction_count" -gt 0 ]; then
        # Check extraction completeness
        local extraction_data=$(db_query "
            SELECT 
                CASE WHEN results_json::json->'$document_id'->>'company_offering' != '' THEN '✅' ELSE '❌' END as offering,
                CASE WHEN results_json::json->'$document_id'->'classification' IS NOT NULL THEN '✅' ELSE '❌' END as classification,
                CASE WHEN results_json::json->'$document_id'->>'company_name' != '' THEN '✅' ELSE '❌' END as company_name,
                CASE WHEN results_json::json->'$document_id'->>'funding_amount' != '' THEN '✅' ELSE '❌' END as funding_amount,
                CASE WHEN results_json::json->'$document_id'->>'deck_date' != '' THEN '✅' ELSE '❌' END as deck_date
            FROM extraction_experiments 
            WHERE document_ids LIKE '%$document_id%' 
            ORDER BY created_at DESC 
            LIMIT 1;
        ")
        
        if [ -n "$extraction_data" ]; then
            IFS='|' read -r offering classification company_name funding_amount deck_date <<< "$extraction_data"
            echo "  • Company Offering: $(echo $offering | xargs)"
            echo "  • Classification: $(echo $classification | xargs)"  
            echo "  • Company Name: $(echo $company_name | xargs)"
            echo "  • Funding Amount: $(echo $funding_amount | xargs)"
            echo "  • Deck Date: $(echo $deck_date | xargs)"
            
            if [[ "$extraction_data" == *"❌"* ]]; then
                log_warning "Some extraction data missing"
            else
                log_success "All extraction data complete"
            fi
        fi
    else
        log_error "Extraction experiments missing"
    fi
    
    # ==============================================================================
    # PHASE 3: TEMPLATE PROCESSING VERIFICATION  
    # ==============================================================================
    
    if [[ "$expected_phases" == "all" || "$expected_phases" == "template-only" ]]; then
        log_info "Phase 3: Template Processing Verification"
        
        local template_status=$(db_query "
            SELECT 
                CASE WHEN template_processing_results_json IS NOT NULL THEN 'available' ELSE 'missing' END,
                template_processing_completed_at
            FROM extraction_experiments 
            WHERE document_ids LIKE '%$document_id%' 
            ORDER BY created_at DESC 
            LIMIT 1;
        ")
        
        if [[ "$template_status" == *"available"* ]]; then
            local completion_time=$(echo "$template_status" | cut -d'|' -f2 | xargs)
            log_success "Template processing complete (completed: $completion_time)"
            
            # Check template processing depth
            local chapter_count=$(db_query "
                SELECT json_object_keys(template_processing_results_json::json->'chapter_analysis') 
                FROM extraction_experiments 
                WHERE document_ids LIKE '%$document_id%' 
                ORDER BY created_at DESC 
                LIMIT 1;
            " | wc -l)
            
            if [ "$chapter_count" -gt 0 ]; then
                echo "  • Template chapters analyzed: $chapter_count"
            fi
        else
            log_error "Template processing results missing"
        fi
    fi
    
    # ==============================================================================
    # PHASE 4: SPECIALIZED ANALYSIS VERIFICATION
    # ==============================================================================
    
    if [ "$expected_phases" == "all" ]; then
        log_info "Phase 4: Specialized Analysis Verification"
        
        local specialized_count=$(db_query "SELECT COUNT(*) FROM specialized_analysis_results WHERE document_id = $document_id;" | xargs)
        local specialized_types=$(db_query "
            SELECT DISTINCT analysis_type 
            FROM specialized_analysis_results 
            WHERE document_id = $document_id;
        " | tr '\n' ', ' | sed 's/,$//')
        
        if [ "$specialized_count" -gt 0 ]; then
            log_success "Specialized analysis complete: $specialized_count results"
            echo "  • Analysis types: $specialized_types"
        else
            log_error "Specialized analysis missing (regulatory, clinical, scientific analysis expected)"
        fi
    fi
    
    # ==============================================================================
    # FRONTEND ACCESSIBILITY VERIFICATION
    # ==============================================================================
    
    log_info "Frontend Accessibility Check"
    
    # Check if results are accessible via API (using debug endpoint to avoid auth)
    local api_status=$(curl -s "http://localhost:8000/api/debug/deck/$document_id/status" | jq -r '.exists // "false"' 2>/dev/null)
    
    if [ "$api_status" == "true" ]; then
        log_success "Document accessible via API"
        echo "  • Results URL: https://halbzeit.ai/project/$project_id/results/$document_id"
    else
        log_warning "API accessibility check failed"
    fi
    
    # ==============================================================================
    # OVERALL ASSESSMENT
    # ==============================================================================
    
    log_section "Overall Assessment"
    
    # Count successes and failures
    local success_count=0
    local total_checks=0
    
    # Visual analysis + feedback (2 checks)
    if [ "$visual_count" -gt 0 ] && [ "$visual_pages" -gt 0 ]; then ((success_count++)); fi
    if [ "$feedback_count" -gt 0 ]; then ((success_count++)); fi
    total_checks=$((total_checks + 2))
    
    # Extraction (1 check)
    if [ "$extraction_count" -gt 0 ]; then ((success_count++)); fi
    total_checks=$((total_checks + 1))
    
    # Template processing (1 check if expected)
    if [[ "$expected_phases" == "all" || "$expected_phases" == "template-only" ]]; then
        if [[ "$template_status" == *"available"* ]]; then ((success_count++)); fi
        total_checks=$((total_checks + 1))
    fi
    
    # Specialized analysis (1 check if expected)
    if [ "$expected_phases" == "all" ]; then
        if [ "$specialized_count" -gt 0 ]; then ((success_count++)); fi
        total_checks=$((total_checks + 1))
    fi
    
    # API accessibility (1 check)
    if [ "$api_status" == "true" ]; then ((success_count++)); fi
    total_checks=$((total_checks + 1))
    
    local success_rate=$((success_count * 100 / total_checks))
    
    echo "📊 Analysis Completeness: $success_count/$total_checks checks passed ($success_rate%)"
    
    if [ $success_rate -eq 100 ]; then
        log_success "🎉 COMPREHENSIVE ANALYSIS COMPLETE - Startup will receive full coverage analysis!"
    elif [ $success_rate -ge 75 ]; then
        log_warning "⚠️  ANALYSIS MOSTLY COMPLETE - Some components missing, but core analysis available"
    elif [ $success_rate -ge 50 ]; then
        log_warning "⚠️  ANALYSIS PARTIALLY COMPLETE - Significant gaps in analysis coverage"
    else
        log_error "❌ ANALYSIS INCOMPLETE - Major processing failures, startup will not receive adequate analysis"
    fi
    
    # ==============================================================================
    # ACTIONABLE RECOMMENDATIONS
    # ==============================================================================
    
    if [ $success_rate -lt 100 ]; then
        log_section "Actionable Recommendations"
        
        if [ "$feedback_count" -eq 0 ]; then
            echo "• Slide feedback missing → Check slide_feedback table and GPU feedback generation"
        fi
        
        if [ "$specialized_count" -eq 0 ] && [ "$expected_phases" == "all" ]; then
            echo "• Specialized analysis missing → Check specialized_analysis_results table"
            echo "  → May need to run: ./scripts/debug-api.sh reprocess $document_id"
        fi
        
        if [[ "$template_status" == *"missing"* ]]; then
            echo "• Template processing missing → Check extraction_experiments.template_processing_results_json"
        fi
        
        echo ""
        echo "Quick fix command:"
        echo "  ./scripts/debug-api.sh reprocess $document_id"
    fi
    
    return $((100 - success_rate))  # Return error code based on success rate
}

# ==============================================================================
# BATCH VERIFICATION MODE
# ==============================================================================

verify_all_recent_documents() {
    local days=${1:-7}  # Default last 7 days
    
    log_section "Batch Verification: Documents from Last $days Days"
    
    local recent_docs=$(db_query "
        SELECT id, file_name 
        FROM project_documents 
        WHERE created_at >= NOW() - INTERVAL '$days days'
        ORDER BY created_at DESC;
    ")
    
    if [ -z "$recent_docs" ]; then
        log_warning "No documents found in the last $days days"
        return 0
    fi
    
    local total_docs=0
    local failed_docs=0
    
    while IFS='|' read -r doc_id file_name; do
        doc_id=$(echo "$doc_id" | xargs)
        file_name=$(echo "$file_name" | xargs)
        
        if [ -n "$doc_id" ]; then
            echo ""
            echo "🔍 Checking Document $doc_id: $file_name"
            
            verify_document_analysis "$doc_id" "all" > /tmp/verify_${doc_id}.log 2>&1
            local exit_code=$?
            
            if [ $exit_code -eq 0 ]; then
                log_success "Document $doc_id: COMPLETE"
            else
                log_error "Document $doc_id: INCOMPLETE ($exit_code% failure rate)"
                ((failed_docs++))
            fi
            
            ((total_docs++))
        fi
    done <<< "$recent_docs"
    
    echo ""
    log_section "Batch Summary"
    echo "📊 Total documents: $total_docs"
    echo "✅ Complete: $((total_docs - failed_docs))"
    echo "❌ Incomplete: $failed_docs"
    
    if [ $failed_docs -eq 0 ]; then
        log_success "🎉 All recent documents have comprehensive analysis!"
    else
        log_warning "⚠️  $failed_docs documents need attention"
    fi
}

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

case "${1:-help}" in
    [0-9]*)
        # Document ID provided
        verify_document_analysis "$1" "$2"
        ;;
    "batch")
        verify_all_recent_documents "$2"
        ;;
    "help"|"-h"|"--help")
        echo "🔍 COMPREHENSIVE DOCUMENT ANALYSIS VERIFICATION"
        echo ""
        echo "Usage:"
        echo "  $0 <document_id> [expected_phases]     - Verify specific document"
        echo "  $0 batch [days]                       - Verify all recent documents"
        echo "  $0 help                               - Show this help"
        echo ""
        echo "Examples:"
        echo "  $0 4                                  - Full verification for document 4"
        echo "  $0 4 template-only                    - Check only basic + template processing"
        echo "  $0 batch 3                           - Verify all documents from last 3 days"
        echo ""
        echo "Expected phases:"
        echo "  all (default) - Visual, extraction, template, specialized analysis"
        echo "  basic         - Visual and extraction only" 
        echo "  template-only - Visual, extraction, template processing"
        ;;
    *)
        log_error "Invalid command: $1"
        echo "Run '$0 help' for usage information"
        exit 1
        ;;
esac