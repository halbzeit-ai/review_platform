#!/bin/bash

# Document Processing Test Script
# Comprehensive testing of document upload, processing pipeline, and architecture validation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Helper functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_section() { echo -e "\n${CYAN}${BOLD}═══════════════════════════════════════════════${NC}\n${CYAN}${BOLD}► $1${NC}\n${CYAN}${BOLD}═══════════════════════════════════════════════${NC}"; }

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTH_HELPER="$SCRIPT_DIR/auth-helper.sh"
DEBUG_API="$SCRIPT_DIR/debug-api.sh"
BASE_URL="http://localhost:8000"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Test result tracking
declare -a FAILED_TESTS=()
declare -a CREATED_DOCUMENTS=()

# Test assertion functions
assert_equals() {
    local expected="$1"
    local actual="$2" 
    local test_name="$3"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    if [[ "$expected" == "$actual" ]]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_success "PASS: $test_name"
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("$test_name: expected '$expected', got '$actual'")
        log_error "FAIL: $test_name - Expected: '$expected', Got: '$actual'"
        return 1
    fi
}

assert_not_empty() {
    local value="$1"
    local test_name="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    if [[ -n "$value" && "$value" != "null" && "$value" != "ERROR" ]]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_success "PASS: $test_name"
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("$test_name: value was empty or null")
        log_error "FAIL: $test_name - Value was empty or null: '$value'"
        return 1
    fi
}

assert_http_success() {
    local http_code="$1"
    local test_name="$2"
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    
    if [[ "$http_code" == "200" || "$http_code" == "201" ]]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_success "PASS: $test_name"
        return 0
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("$test_name: HTTP $http_code")
        log_error "FAIL: $test_name - HTTP $http_code"
        return 1
    fi
}

# Check dependencies
check_dependencies() {
    log_section "Checking Dependencies"
    
    local missing_deps=0
    
    if [[ ! -f "$AUTH_HELPER" ]]; then
        log_error "Auth helper script not found: $AUTH_HELPER"
        missing_deps=1
    fi
    
    if [[ ! -f "$DEBUG_API" ]]; then
        log_error "Debug API script not found: $DEBUG_API"
        missing_deps=1
    fi
    
    for cmd in jq curl sudo; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "$cmd is required but not installed"
            missing_deps=1
        fi
    done
    
    if [[ $missing_deps -eq 1 ]]; then
        log_error "Missing dependencies. Please install required tools."
        exit 1
    fi
    
    log_success "All dependencies available"
}

# Setup test environment
setup_test_environment() {
    log_section "Setting Up Test Environment"
    
    # Ensure we have test users available
    log_info "Checking if test startup user exists and is logged in..."
    
    # Try to login as test startup user
    if ! echo "RandomPass978" | "$AUTH_HELPER" login startup test-startup@example.com 2>/dev/null; then
        log_warning "Test startup user not available or login failed"
        log_info "Please run the workflow-test first to create test environment"
        return 1
    fi
    
    log_success "Test environment ready"
}

# Test document creation
test_document_creation() {
    log_section "Document Creation Tests"
    
    # Test PDF creation
    log_info "Testing PDF document creation..."
    local test_pdf="/tmp/processing-test-doc.pdf"
    
    if "$AUTH_HELPER" create-test-pdf "$test_pdf" "Document Processing Test Content - $(date)" >/dev/null 2>&1; then
        assert_equals "true" "$(test -f "$test_pdf" && echo true)" "PDF document created"
        
        # Check file size
        local file_size
        file_size=$(stat -c%s "$test_pdf" 2>/dev/null || stat -f%z "$test_pdf" 2>/dev/null)
        assert_not_empty "$file_size" "PDF file has content"
        
        if [[ "$file_size" -gt 400 ]]; then
            log_success "PDF file size appropriate: $file_size bytes"
        else
            log_warning "PDF file size seems small: $file_size bytes"
        fi
    else
        log_error "Failed to create test PDF"
        return 1
    fi
}

# Test document upload
test_document_upload() {
    log_section "Document Upload Tests"
    
    local test_pdf="/tmp/processing-test-doc.pdf"
    
    # Test document upload
    log_info "Testing document upload..."
    local upload_response
    upload_response=$("$AUTH_HELPER" upload-document "$test_pdf" 2>&1)
    
    if [[ $? -eq 0 ]]; then
        log_success "Document upload succeeded"
        
        # Extract document ID from response
        local document_id
        document_id=$(echo "$upload_response" | grep "Document ID:" | cut -d: -f2 | tr -d ' ')
        
        if assert_not_empty "$document_id" "Document ID returned"; then
            CREATED_DOCUMENTS+=("$document_id")
            log_info "Created document ID: $document_id"
            
            # Test API response format
            local task_id
            task_id=$(echo "$upload_response" | grep "Task ID:" | cut -d: -f2 | tr -d ' ')
            assert_not_empty "$task_id" "Task ID returned"
            
            local file_path
            file_path=$(echo "$upload_response" | grep "File Path:" | cut -d: -f2- | tr -d ' ')
            assert_not_empty "$file_path" "File path returned"
        fi
    else
        log_error "Document upload failed"
        echo "$upload_response"
        return 1
    fi
}

# Test processing pipeline
test_processing_pipeline() {
    log_section "Processing Pipeline Tests"
    
    if [[ ${#CREATED_DOCUMENTS[@]} -eq 0 ]]; then
        log_error "No documents created for processing tests"
        return 1
    fi
    
    local document_id="${CREATED_DOCUMENTS[0]}"
    log_info "Testing processing pipeline for document $document_id"
    
    # Check initial processing status
    log_info "Checking initial processing status..."
    local status_response
    status_response=$("$DEBUG_API" deck "$document_id" 2>/dev/null | jq -r '.processing_status // "unknown"' 2>/dev/null)
    
    if [[ "$status_response" != "unknown" ]]; then
        log_success "Processing status available: $status_response"
        
        # Wait for processing to start
        log_info "Waiting 10 seconds for processing to start..."
        sleep 10
        
        # Check processing queue
        log_info "Checking processing queue..."
        local queue_status
        queue_status=$(sudo -u postgres psql review-platform -t -c "SELECT status FROM processing_queue WHERE document_id = $document_id ORDER BY created_at DESC LIMIT 1;" 2>/dev/null | tr -d ' ')
        
        if [[ -n "$queue_status" ]]; then
            log_success "Processing queue entry found: $queue_status"
            assert_not_empty "$queue_status" "Processing queue has task"
            
            # Check for valid status
            case "$queue_status" in
                "queued"|"processing"|"completed"|"failed")
                    log_success "Valid processing status: $queue_status"
                    ;;
                *)
                    log_warning "Unexpected processing status: $queue_status"
                    ;;
            esac
        else
            log_warning "No processing queue entry found"
        fi
    else
        log_warning "Processing status unavailable"
    fi
}

# Test architecture validation (pitch_deck_id elimination)
test_architecture_validation() {
    log_section "Architecture Validation Tests"
    
    # Test 1: Verify processing_queue uses document_id instead of pitch_deck_id
    log_info "Testing processing_queue table structure..."
    
    # Check if pitch_deck_id column exists (should NOT exist)
    local pitch_deck_column_exists
    pitch_deck_column_exists=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'processing_queue' AND column_name = 'pitch_deck_id';" 2>/dev/null | tr -d ' ')
    
    assert_equals "0" "$pitch_deck_column_exists" "pitch_deck_id column removed from processing_queue"
    
    # Check if document_id column exists (should exist)
    local document_id_column_exists
    document_id_column_exists=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'processing_queue' AND column_name = 'document_id';" 2>/dev/null | tr -d ' ')
    
    assert_equals "1" "$document_id_column_exists" "document_id column exists in processing_queue"
    
    # Test 2: Verify visual_analysis_cache uses document_id
    log_info "Testing visual_analysis_cache table structure..."
    
    local visual_cache_document_id_exists
    visual_cache_document_id_exists=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'visual_analysis_cache' AND column_name = 'document_id';" 2>/dev/null | tr -d ' ')
    
    assert_equals "1" "$visual_cache_document_id_exists" "document_id column exists in visual_analysis_cache"
    
    # Test 3: Check that pitch_decks table doesn't exist
    log_info "Verifying pitch_decks table removal..."
    
    local pitch_decks_table_exists
    pitch_decks_table_exists=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'pitch_decks';" 2>/dev/null | tr -d ' ')
    
    assert_equals "0" "$pitch_decks_table_exists" "pitch_decks table has been removed"
    
    # Test 4: Verify project_documents table exists and is used
    log_info "Testing project_documents table..."
    
    local project_documents_exists
    project_documents_exists=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'project_documents';" 2>/dev/null | tr -d ' ')
    
    assert_equals "1" "$project_documents_exists" "project_documents table exists"
    
    # Check that we have recent document uploads
    local recent_docs_count
    recent_docs_count=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM project_documents WHERE upload_date >= CURRENT_DATE;" 2>/dev/null | tr -d ' ')
    
    if [[ "$recent_docs_count" -gt 0 ]]; then
        log_success "Recent documents found in project_documents table: $recent_docs_count"
    else
        log_warning "No recent documents in project_documents table"
    fi
}

# Test database consistency
test_database_consistency() {
    log_section "Database Consistency Tests"
    
    # Test foreign key relationships
    log_info "Testing foreign key relationships..."
    
    # Check project_documents to projects relationship
    local orphaned_documents
    orphaned_documents=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM project_documents pd LEFT JOIN projects p ON pd.project_id = p.id WHERE p.id IS NULL;" 2>/dev/null | tr -d ' ')
    
    assert_equals "0" "$orphaned_documents" "No orphaned project documents"
    
    # Check processing_queue to project_documents relationship
    local orphaned_tasks
    orphaned_tasks=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM processing_queue pq LEFT JOIN project_documents pd ON pq.document_id = pd.id WHERE pd.id IS NULL;" 2>/dev/null | tr -d ' ')
    
    assert_equals "0" "$orphaned_tasks" "No orphaned processing tasks"
    
    # Check visual_analysis_cache to project_documents relationship
    local orphaned_cache
    orphaned_cache=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM visual_analysis_cache vac LEFT JOIN project_documents pd ON vac.document_id = pd.id WHERE pd.id IS NULL;" 2>/dev/null | tr -d ' ')
    
    assert_equals "0" "$orphaned_cache" "No orphaned visual analysis cache entries"
}

# Test API endpoints
test_api_endpoints() {
    log_section "API Endpoint Tests"
    
    # Test debug endpoints for document processing
    log_info "Testing debug API endpoints..."
    
    if [[ ${#CREATED_DOCUMENTS[@]} -gt 0 ]]; then
        local document_id="${CREATED_DOCUMENTS[0]}"
        
        # Test deck status endpoint
        local deck_status_response
        deck_status_response=$(curl -s "$BASE_URL/api/debug/deck/$document_id/status" 2>/dev/null)
        
        if [[ $? -eq 0 ]]; then
            local status_has_document_id
            status_has_document_id=$(echo "$deck_status_response" | jq -r '.document_id // empty' 2>/dev/null)
            
            if [[ -n "$status_has_document_id" ]]; then
                assert_equals "$document_id" "$status_has_document_id" "Debug API returns correct document_id"
            else
                log_warning "Debug API doesn't return document_id field"
            fi
        else
            log_warning "Debug API deck status endpoint not accessible"
        fi
    fi
    
    # Test database debug endpoints
    local tables_response
    tables_response=$(curl -s "$BASE_URL/api/debug/database/tables" 2>/dev/null)
    
    if [[ $? -eq 0 ]]; then
        local table_count
        table_count=$(echo "$tables_response" | jq -r '.count // 0' 2>/dev/null)
        
        if [[ "$table_count" -gt 20 ]]; then
            log_success "Database debug endpoint working - $table_count tables"
        else
            log_warning "Unexpected table count: $table_count"
        fi
    else
        log_warning "Database debug endpoint not accessible"
    fi
}

# Cleanup test data
cleanup_test_data() {
    log_section "Cleaning Up Test Data"
    
    # Clean up test files
    rm -f /tmp/processing-test-doc.pdf /tmp/auth-helper-test-doc.pdf
    
    # Note: We don't clean up database entries as they're useful for ongoing testing
    # In a production environment, these would be cleaned up
    
    log_info "Cleaned up temporary test files"
    log_info "Database test data preserved for analysis"
}

# Show comprehensive test results
show_test_results() {
    log_section "Document Processing Test Results"
    
    echo ""
    log_info "Total Tests: $TESTS_TOTAL"
    log_success "Passed: $TESTS_PASSED"
    
    if [[ $TESTS_FAILED -gt 0 ]]; then
        log_error "Failed: $TESTS_FAILED"
        echo ""
        log_error "Failed Tests:"
        for failed_test in "${FAILED_TESTS[@]}"; do
            echo "  - $failed_test"
        done
        echo ""
    fi
    
    local success_rate
    if [[ $TESTS_TOTAL -gt 0 ]]; then
        success_rate=$((TESTS_PASSED * 100 / TESTS_TOTAL))
        log_info "Success Rate: ${success_rate}%"
    fi
    
    echo ""
    if [[ ${#CREATED_DOCUMENTS[@]} -gt 0 ]]; then
        log_info "Created Documents:"
        for doc_id in "${CREATED_DOCUMENTS[@]}"; do
            echo "  - Document ID: $doc_id"
        done
        echo ""
    fi
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        log_success "🎉 All document processing tests passed!"
        log_success "✅ Architecture migration to project_documents is complete and functional"
        return 0
    else
        log_error "💥 Some document processing tests failed!"
        log_error "❌ Please review the failed tests and fix issues"
        return 1
    fi
}

# Main function
main() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        cat << EOF
🧪 Document Processing Test Script

Usage: $0 [options]

Options:
  --cleanup-only    Only run cleanup, skip tests
  --help           Show this help message

This script runs comprehensive document processing tests including:
- Document creation and PDF generation
- Document upload functionality
- Processing pipeline validation
- Architecture validation (pitch_decks → project_documents migration)
- Database consistency checks
- API endpoint functionality

The script creates test documents and validates the complete processing pipeline.

Examples:
  $0                    # Run full document processing test suite
  $0 --cleanup-only     # Only clean up test data
  $0 --help             # Show this help

Prerequisites:
  - Backend service running on localhost:8000
  - Database accessible via sudo -u postgres psql
  - auth-helper.sh and debug-api.sh available
  - Test startup user logged in (run workflow-test first)
EOF
        exit 0
    fi
    
    if [[ "$1" == "--cleanup-only" ]]; then
        cleanup_test_data
        log_success "Cleanup completed"
        exit 0
    fi
    
    log_section "Document Processing Test Suite"
    log_info "Running comprehensive document processing and architecture validation tests..."
    
    # Run test suites
    check_dependencies
    setup_test_environment
    test_document_creation
    test_document_upload
    test_processing_pipeline
    test_architecture_validation
    test_database_consistency
    test_api_endpoints
    
    # Cleanup and show results
    cleanup_test_data
    show_test_results
}

# Run main function
main "$@"