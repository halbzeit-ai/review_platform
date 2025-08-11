#!/bin/bash

# Real Deck Processing Test Script
# Tests the complete processing pipeline with real pitch deck PDFs

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
TEST_PDFS_DIR="/mnt/CPU-GPU/test_pdfs"

# Test configuration
NUM_TESTS_TO_RUN=5  # How many PDFs to test (out of 30 available)
PROCESSING_TIMEOUT=300  # 5 minutes max wait for processing

# Test tracking
declare -a UPLOADED_DOCUMENTS=()
declare -a PROCESSING_RESULTS=()
TESTS_PASSED=0
TESTS_FAILED=0

# Check if test PDFs directory exists and has content
check_test_pdfs() {
    log_section "Checking Test PDF Collection"
    
    if [[ ! -d "$TEST_PDFS_DIR" ]]; then
        log_error "Test PDFs directory not found: $TEST_PDFS_DIR"
        exit 1
    fi
    
    local pdf_count
    pdf_count=$(find "$TEST_PDFS_DIR" -name "*.pdf" -type f | wc -l)
    
    if [[ $pdf_count -eq 0 ]]; then
        log_error "No PDF files found in $TEST_PDFS_DIR"
        exit 1
    fi
    
    log_success "Found $pdf_count PDF files for testing"
    
    if [[ $pdf_count -lt $NUM_TESTS_TO_RUN ]]; then
        log_warning "Only $pdf_count PDFs available, reducing test count from $NUM_TESTS_TO_RUN"
        NUM_TESTS_TO_RUN=$pdf_count
    fi
}

# Select random PDFs for testing
select_random_pdfs() {
    log_section "Selecting Random PDFs for Testing"
    
    local selected_pdfs=()
    readarray -t selected_pdfs < <(find "$TEST_PDFS_DIR" -name "*.pdf" -type f | shuf | head -n "$NUM_TESTS_TO_RUN")
    
    log_info "Selected $NUM_TESTS_TO_RUN PDFs for testing:"
    for pdf in "${selected_pdfs[@]}"; do
        local filename=$(basename "$pdf")
        echo "  - $filename"
    done
    
    echo "${selected_pdfs[@]}"
}

# Setup test user environment
setup_test_environment() {
    log_section "Setting Up Test Environment"
    
    # Login directly via API instead of interactive auth-helper
    local login_response
    login_response=$(curl -s -X POST "$BASE_URL/api/auth/login" \
                     -H "Content-Type: application/json" \
                     -d '{"email": "test-startup@example.com", "password": "RandomPass978"}')
    
    if [[ $? -ne 0 ]]; then
        log_error "Could not connect to backend API"
        exit 1
    fi
    
    local access_token
    access_token=$(echo "$login_response" | jq -r '.access_token // empty' 2>/dev/null)
    
    if [[ -z "$access_token" || "$access_token" == "null" ]]; then
        log_error "Could not login as test startup user"
        log_info "API response: $login_response"
        exit 1
    fi
    
    # Save token for use in upload function
    echo "$access_token" > /tmp/real-deck-test-token
    log_success "Test startup user logged in successfully"
}

# Upload and track a document
upload_document() {
    local pdf_path="$1"
    local filename=$(basename "$pdf_path")
    
    log_info "Uploading: $filename"
    
    # Get saved token
    local token
    if [[ ! -f "/tmp/real-deck-test-token" ]]; then
        log_error "No authentication token found"
        return 1
    fi
    token=$(cat /tmp/real-deck-test-token)
    
    # Upload document via API
    local upload_response
    upload_response=$(curl -s -X POST "$BASE_URL/api/documents/upload" \
                     -H "Authorization: Bearer $token" \
                     -F "file=@$pdf_path")
    
    if [[ $? -ne 0 ]]; then
        log_error "Upload request failed for $filename"
        return 1
    fi
    
    # Parse response
    local document_id
    document_id=$(echo "$upload_response" | jq -r '.document_id // empty' 2>/dev/null)
    
    local task_id
    task_id=$(echo "$upload_response" | jq -r '.task_id // empty' 2>/dev/null)
    
    if [[ -n "$document_id" && "$document_id" != "null" && -n "$task_id" && "$task_id" != "null" ]]; then
        UPLOADED_DOCUMENTS+=("$document_id:$task_id:$filename")
        log_success "Uploaded $filename → Document ID: $document_id, Task ID: $task_id"
        return 0
    else
        log_error "Failed to parse upload response for $filename"
        log_error "Response: $upload_response"
        return 1
    fi
}

# Monitor processing progress for a document
monitor_processing() {
    local document_id="$1"
    local filename="$2"
    local start_time=$(date +%s)
    
    log_info "Monitoring processing for $filename (Document ID: $document_id)..."
    
    while true; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [[ $elapsed -gt $PROCESSING_TIMEOUT ]]; then
            log_warning "Processing timeout reached for $filename"
            return 1
        fi
        
        # Check processing status via debug API
        local status_response
        status_response=$("$DEBUG_API" deck "$document_id" 2>/dev/null)
        
        if [[ $? -eq 0 ]]; then
            local processing_status
            processing_status=$(echo "$status_response" | jq -r '.processing_status // "unknown"' 2>/dev/null)
            
            case "$processing_status" in
                "completed")
                    log_success "Processing completed for $filename (${elapsed}s)"
                    return 0
                    ;;
                "failed")
                    log_error "Processing failed for $filename (${elapsed}s)"
                    return 1
                    ;;
                "processing"|"queued")
                    echo -n "."
                    sleep 10
                    ;;
                *)
                    echo -n "?"
                    sleep 5
                    ;;
            esac
        else
            echo -n "!"
            sleep 5
        fi
    done
}

# Validate processing results
validate_processing_results() {
    local document_id="$1"
    local filename="$2"
    
    log_info "Validating results for $filename..."
    
    # Get detailed status
    local status_response
    status_response=$("$DEBUG_API" deck "$document_id" 2>/dev/null)
    
    if [[ $? -ne 0 ]]; then
        log_error "Could not retrieve status for document $document_id"
        return 1
    fi
    
    # Check for visual analysis results
    local has_visual_analysis
    has_visual_analysis=$(echo "$status_response" | jq -r '.tables.visual_analysis_cache // 0' 2>/dev/null)
    
    # Check for processing queue completion
    local processing_status
    processing_status=$(echo "$status_response" | jq -r '.processing_status // "unknown"' 2>/dev/null)
    
    local validation_score=0
    local max_score=5
    
    # Score the results
    if [[ "$processing_status" == "completed" ]]; then
        ((validation_score++))
        log_success "✓ Processing completed successfully"
    else
        log_warning "✗ Processing status: $processing_status"
    fi
    
    if [[ "$has_visual_analysis" != "0" && "$has_visual_analysis" != "null" ]]; then
        ((validation_score++))
        log_success "✓ Visual analysis cached"
    else
        log_warning "✗ No visual analysis cache found"
    fi
    
    # Check database consistency
    local db_document_exists
    db_document_exists=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM project_documents WHERE id = $document_id;" 2>/dev/null | tr -d ' ')
    
    if [[ "$db_document_exists" == "1" ]]; then
        ((validation_score++))
        log_success "✓ Document exists in database"
    else
        log_warning "✗ Document not found in database"
    fi
    
    # Check processing task completion
    local task_completed
    task_completed=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM processing_queue WHERE document_id = $document_id AND status = 'completed';" 2>/dev/null | tr -d ' ')
    
    if [[ "$task_completed" == "1" ]]; then
        ((validation_score++))
        log_success "✓ Processing task marked as completed"
    else
        log_warning "✗ Processing task not completed in queue"
    fi
    
    # Check file storage
    local file_exists
    file_exists=$(echo "$status_response" | jq -r '.exists // false' 2>/dev/null)
    
    if [[ "$file_exists" == "true" ]]; then
        ((validation_score++))
        log_success "✓ File exists in storage"
    else
        log_warning "✗ File not found in storage"
    fi
    
    # Calculate percentage
    local percentage=$((validation_score * 100 / max_score))
    
    if [[ $percentage -ge 80 ]]; then
        log_success "Overall validation: ${percentage}% (${validation_score}/${max_score}) - PASS"
        TESTS_PASSED=$((TESTS_PASSED + 1))
        PROCESSING_RESULTS+=("$filename:PASS:${percentage}%")
        return 0
    else
        log_warning "Overall validation: ${percentage}% (${validation_score}/${max_score}) - FAIL"
        TESTS_FAILED=$((TESTS_FAILED + 1))
        PROCESSING_RESULTS+=("$filename:FAIL:${percentage}%")
        return 1
    fi
}

# Run complete processing test for selected PDFs
run_processing_tests() {
    log_section "Running Processing Tests on Real Pitch Decks"
    
    local selected_pdfs
    readarray -t selected_pdfs < <(select_random_pdfs)
    
    # Upload all selected documents
    log_info "Phase 1: Uploading documents..."
    for pdf_path in "${selected_pdfs[@]}"; do
        if ! upload_document "$pdf_path"; then
            log_warning "Skipping processing for failed upload"
            continue
        fi
        sleep 2  # Brief pause between uploads
    done
    
    echo ""
    log_success "Uploaded ${#UPLOADED_DOCUMENTS[@]} documents successfully"
    
    # Monitor and validate processing
    log_info "Phase 2: Monitoring processing..."
    for doc_info in "${UPLOADED_DOCUMENTS[@]}"; do
        IFS=':' read -r document_id task_id filename <<< "$doc_info"
        
        echo ""
        log_info "Processing: $filename"
        
        if monitor_processing "$document_id" "$filename"; then
            validate_processing_results "$document_id" "$filename"
        else
            log_error "Processing monitoring failed for $filename"
            TESTS_FAILED=$((TESTS_FAILED + 1))
            PROCESSING_RESULTS+=("$filename:TIMEOUT:0%")
        fi
    done
}

# Show comprehensive results
show_results() {
    log_section "Real Deck Processing Test Results"
    
    echo ""
    log_info "Summary:"
    echo "  📊 Total Documents: ${#UPLOADED_DOCUMENTS[@]}"
    echo "  ✅ Passed: $TESTS_PASSED"
    echo "  ❌ Failed: $TESTS_FAILED"
    
    if [[ ${#UPLOADED_DOCUMENTS[@]} -gt 0 ]]; then
        local success_rate=$((TESTS_PASSED * 100 / ${#UPLOADED_DOCUMENTS[@]}))
        echo "  📈 Success Rate: ${success_rate}%"
    fi
    
    echo ""
    log_info "Detailed Results:"
    for result in "${PROCESSING_RESULTS[@]}"; do
        IFS=':' read -r filename status score <<< "$result"
        
        local status_icon
        case "$status" in
            "PASS") status_icon="✅" ;;
            "FAIL") status_icon="❌" ;;
            "TIMEOUT") status_icon="⏱️" ;;
            *) status_icon="❓" ;;
        esac
        
        printf "  %s %-30s %s (%s)\\n" "$status_icon" "$filename" "$status" "$score"
    done
    
    echo ""
    if [[ $TESTS_FAILED -eq 0 && ${#UPLOADED_DOCUMENTS[@]} -gt 0 ]]; then
        log_success "🎉 All real pitch deck processing tests passed!"
        log_success "✅ Processing pipeline is working correctly with real documents"
        return 0
    else
        log_warning "⚠️  Some issues detected with real document processing"
        log_info "This may indicate pipeline issues that need investigation"
        return 1
    fi
}

# Main function
main() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        cat << EOF
🧪 Real Deck Processing Test Script

Usage: $0 [options]

Options:
  --num-tests N     Number of PDFs to test (default: 5)
  --timeout N       Processing timeout in seconds (default: 300)
  --help            Show this help message

This script tests the complete processing pipeline using real pitch deck PDFs:
- Randomly selects PDFs from the test collection
- Uploads them as startup user
- Monitors processing progress in real-time
- Validates all processing phases
- Provides comprehensive results analysis

Prerequisites:
  - Real pitch deck PDFs in /mnt/CPU-GPU/test_pdfs/
  - Backend service running on localhost:8000
  - Test startup user logged in
  - Database accessible

Examples:
  $0                    # Test 5 random PDFs
  $0 --num-tests 10     # Test 10 random PDFs
  $0 --timeout 600      # Use 10 minute timeout
EOF
        exit 0
    fi
    
    # Parse command line options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --num-tests)
                NUM_TESTS_TO_RUN="$2"
                shift 2
                ;;
            --timeout)
                PROCESSING_TIMEOUT="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    log_section "Real Pitch Deck Processing Test"
    log_info "Testing processing pipeline with real pitch deck PDFs..."
    log_info "Configuration: $NUM_TESTS_TO_RUN tests, ${PROCESSING_TIMEOUT}s timeout"
    
    # Run test phases
    check_test_pdfs
    setup_test_environment
    run_processing_tests
    show_results
}

# Run main function
main "$@"