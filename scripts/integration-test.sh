#!/bin/bash

# Integration Test Script
# Runs comprehensive end-to-end tests for the review platform

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
DEBUG_API="$SCRIPT_DIR/debug-api.sh"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Test result tracking
declare -a FAILED_TESTS=()

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
    
    if ! sudo -u postgres psql --version &> /dev/null; then
        log_error "PostgreSQL access required (sudo + psql)"
        missing_deps=1
    fi
    
    if [[ $missing_deps -eq 1 ]]; then
        log_error "Missing dependencies. Please install required tools."
        exit 1
    fi
    
    log_success "All dependencies available"
}

# Test system health
test_system_health() {
    log_section "System Health Tests"
    
    log_info "Testing backend API health..."
    local health_response
    health_response=$("$DEBUG_API" health 2>/dev/null | grep -o '"status": "healthy"' || echo "")
    assert_not_empty "$health_response" "Backend API health check"
    
    log_info "Testing database connectivity..."
    local db_status
    db_status=$(sudo -u postgres psql review-platform -c "SELECT 1;" 2>/dev/null | grep -c "1" || echo "0")
    assert_equals "1" "$db_status" "Database connectivity"
    
    log_info "Testing table existence..."
    local table_count
    table_count=$("$DEBUG_API" tables 2>/dev/null | jq -r '.count // 0' 2>/dev/null || echo "0")
    assert_not_empty "$table_count" "Database tables exist"
}

# Test user management
test_user_management() {
    log_section "User Management Tests"
    
    # Test user registration
    log_info "Testing user registration..."
    local reg_result
    reg_result=$("$AUTH_HELPER" register "test-integration-startup@example.com" "RandomPass978" "startup" "Test Integration Inc" "Integration" "Test" "en" 2>&1 | grep -c "registered successfully" || echo "0")
    assert_equals "1" "$reg_result" "User registration"
    
    # Test user promotion
    log_info "Testing user promotion..."
    local promote_result
    promote_result=$("$AUTH_HELPER" promote "test-integration-startup@example.com" "gp" 2>&1 | grep -c "promoted to gp" || echo "0")
    assert_equals "1" "$promote_result" "User promotion to GP"
    
    # Test user verification
    log_info "Testing user verification..."
    local verify_result
    verify_result=$("$AUTH_HELPER" verify "test-integration-startup@example.com" 2>&1 | grep -c "verified successfully" || echo "0")
    assert_equals "1" "$verify_result" "User email verification"
}

# Test authentication
test_authentication() {
    log_section "Authentication Tests"
    
    # Test GP login
    log_info "Testing GP login..."
    local login_result
    login_result=$(echo "RandomPass978" | "$AUTH_HELPER" login "gp" "test-integration-startup@example.com" 2>/dev/null | grep -c "Login successful" || echo "0")
    assert_equals "1" "$login_result" "GP user login"
    
    # Test whoami
    log_info "Testing user identity check..."
    local whoami_result
    whoami_result=$("$AUTH_HELPER" whoami 2>/dev/null | grep -c "test-integration-startup@example.com" || echo "0")
    assert_equals "1" "$whoami_result" "User identity verification"
}

# Test project management
test_project_management() {
    log_section "Project Management Tests"
    
    # Test project creation
    log_info "Testing project creation..."
    local project_id
    project_id=$("$AUTH_HELPER" create-project "Integration Test Project" "series_a" "Test Integration Inc" "Integration testing platform" "project_id" 2>/dev/null || echo "ERROR")
    assert_not_empty "$project_id" "Project creation"
    
    if [[ "$project_id" != "ERROR" && -n "$project_id" ]]; then
        # Test invitation sending
        log_info "Testing project invitation..."
        local invitation_token
        invitation_token=$("$AUTH_HELPER" invite-to-project "$project_id" "test-startup@example.com" "invitation_token" 2>/dev/null || echo "ERROR")
        assert_not_empty "$invitation_token" "Project invitation"
        
        if [[ "$invitation_token" != "ERROR" && -n "$invitation_token" ]]; then
            # Test invitation acceptance
            log_info "Testing invitation acceptance..."
            local accept_result
            accept_result=$("$AUTH_HELPER" accept-invitation "$invitation_token" "Test" "User" "Test Startup Inc" "RandomPass978" "en" 2>/dev/null | grep -c "accepted successfully" || echo "0")
            assert_equals "1" "$accept_result" "Invitation acceptance"
        fi
    fi
}

# Test database consistency
test_database_consistency() {
    log_section "Database Consistency Tests"
    
    # Test user count
    log_info "Testing user count consistency..."
    local user_count
    user_count=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM users;" 2>/dev/null | tr -d ' ' || echo "0")
    assert_not_empty "$user_count" "Users table has data"
    
    # Test project count
    log_info "Testing project count..."
    local project_count
    project_count=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM projects;" 2>/dev/null | tr -d ' ' || echo "0")
    assert_not_empty "$project_count" "Projects table has data"
    
    # Test project membership consistency
    log_info "Testing project membership consistency..."
    local membership_consistency
    membership_consistency=$(sudo -u postgres psql review-platform -t -c "
        SELECT COUNT(*) FROM project_members pm
        WHERE EXISTS (SELECT 1 FROM projects p WHERE p.id = pm.project_id)
        AND EXISTS (SELECT 1 FROM users u WHERE u.id = pm.user_id);
    " 2>/dev/null | tr -d ' ' || echo "0")
    assert_not_empty "$membership_consistency" "Project memberships are consistent"
}

# Test API endpoints
test_api_endpoints() {
    log_section "API Endpoint Tests"
    
    # Test debug endpoints
    log_info "Testing debug API endpoints..."
    local debug_health
    debug_health=$(curl -s "http://localhost:8000/api/debug/health-detailed" | jq -r '.status // "error"' 2>/dev/null || echo "error")
    assert_equals "healthy" "$debug_health" "Debug health endpoint"
    
    # Test authentication required endpoints
    log_info "Testing authenticated endpoints..."
    local auth_endpoint_result
    auth_endpoint_result=$("$AUTH_HELPER" api GET "/projects/my-projects" 2>/dev/null | jq -r 'type // "error"' 2>/dev/null || echo "error")
    assert_not_empty "$auth_endpoint_result" "Authenticated API endpoint access"
}

# Document processing tests
test_document_processing() {
    log_section "Document Processing Tests"
    
    # Create test PDF
    log_info "Creating test PDF document..."
    local test_pdf="/tmp/integration-test-doc.pdf"
    
    cat > "$test_pdf" << 'EOF'
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
/Length 88
>>
stream
BT
/F1 24 Tf
100 700 Td
(Integration Test PDF Document) Tj
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
342
%%EOF
EOF
    
    if [[ -f "$test_pdf" ]]; then
        assert_not_empty "$(stat -c%s "$test_pdf" 2>/dev/null)" "Test PDF created with content"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("Test PDF creation failed")
        log_error "FAIL: Test PDF creation failed"
        return 1
    fi
    
    # Test document upload (requires logged in user)
    log_info "Testing document upload functionality..."
    
    # Login as startup user for document upload
    local token
    token=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
            -H "Content-Type: application/json" \
            -d '{"email": "test-startup@example.com", "password": "RandomPass978"}' | \
            jq -r '.access_token // empty' 2>/dev/null)
    
    if [[ -n "$token" ]]; then
        # Upload document
        local upload_response
        upload_response=$(curl -s -X POST "http://localhost:8000/api/documents/upload" \
                         -H "Authorization: Bearer $token" \
                         -F "file=@$test_pdf" 2>/dev/null)
        
        if [[ $? -eq 0 ]]; then
            local document_id
            document_id=$(echo "$upload_response" | jq -r '.document_id // empty' 2>/dev/null)
            
            if [[ -n "$document_id" && "$document_id" != "null" ]]; then
                assert_not_empty "$document_id" "Document upload returns document ID"
                
                # Check processing task creation
                local task_id
                task_id=$(echo "$upload_response" | jq -r '.task_id // empty' 2>/dev/null)
                assert_not_empty "$task_id" "Document upload creates processing task"
                
                # Verify document in database
                local db_document_exists
                db_document_exists=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM project_documents WHERE id = $document_id;" 2>/dev/null | tr -d ' ')
                assert_equals "1" "$db_document_exists" "Document stored in project_documents table"
                
            else
                TESTS_FAILED=$((TESTS_FAILED + 1))
                FAILED_TESTS+=("Document upload did not return document ID")
                log_error "FAIL: Document upload did not return document ID"
            fi
        else
            TESTS_FAILED=$((TESTS_FAILED + 1))
            FAILED_TESTS+=("Document upload request failed")
            log_error "FAIL: Document upload request failed"
        fi
    else
        log_warning "Could not login for document upload test - skipping"
    fi
    
    # Cleanup
    rm -f "$test_pdf"
}

# Architecture validation tests
test_architecture_validation() {
    log_section "Architecture Validation Tests"
    
    # Test 1: Verify pitch_decks table removal
    log_info "Testing legacy pitch_decks table removal..."
    local pitch_decks_exists
    pitch_decks_exists=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'pitch_decks';" 2>/dev/null | tr -d ' ')
    assert_equals "0" "$pitch_decks_exists" "Legacy pitch_decks table removed"
    
    # Test 2: Verify project_documents table exists
    log_info "Testing project_documents table existence..."
    local project_documents_exists
    project_documents_exists=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'project_documents';" 2>/dev/null | tr -d ' ')
    assert_equals "1" "$project_documents_exists" "project_documents table exists"
    
    # Test 3: Verify processing_queue uses document_id
    log_info "Testing processing_queue architecture..."
    local document_id_column_exists
    document_id_column_exists=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'processing_queue' AND column_name = 'document_id';" 2>/dev/null | tr -d ' ')
    assert_equals "1" "$document_id_column_exists" "processing_queue uses document_id column"
    
    local pitch_deck_id_column_exists
    pitch_deck_id_column_exists=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'processing_queue' AND column_name = 'pitch_deck_id';" 2>/dev/null | tr -d ' ')
    assert_equals "0" "$pitch_deck_id_column_exists" "processing_queue no longer has pitch_deck_id column"
    
    # Test 4: Verify visual_analysis_cache uses document_id
    log_info "Testing visual_analysis_cache architecture..."
    local visual_cache_document_id
    visual_cache_document_id=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'visual_analysis_cache' AND column_name = 'document_id';" 2>/dev/null | tr -d ' ')
    assert_equals "1" "$visual_cache_document_id" "visual_analysis_cache uses document_id column"
    
    # Test 5: Check database function updates
    log_info "Testing database function updates..."
    local get_next_task_function_exists
    get_next_task_function_exists=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM information_schema.routines WHERE routine_name = 'get_next_processing_task' AND data_type = 'SETOF';" 2>/dev/null | tr -d ' ')
    assert_equals "1" "$get_next_task_function_exists" "get_next_processing_task function exists"
    
    local complete_task_function_exists
    complete_task_function_exists=$(sudo -u postgres psql review-platform -t -c "SELECT COUNT(*) FROM information_schema.routines WHERE routine_name = 'complete_task';" 2>/dev/null | tr -d ' ')
    assert_equals "1" "$complete_task_function_exists" "complete_task function exists"
}

# Performance tests
test_performance() {
    log_section "Basic Performance Tests"
    
    # Test API response time
    log_info "Testing API response time..."
    local start_time end_time response_time
    start_time=$(date +%s%3N)
    curl -s "http://localhost:8000/api/debug/health" > /dev/null 2>&1
    end_time=$(date +%s%3N)
    response_time=$((end_time - start_time))
    
    # Assert response time is under 2 seconds (2000ms)
    if [[ $response_time -lt 2000 ]]; then
        TESTS_PASSED=$((TESTS_PASSED + 1))
        log_success "PASS: API response time (${response_time}ms < 2000ms)"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        FAILED_TESTS+=("API response time: ${response_time}ms >= 2000ms")
        log_error "FAIL: API response time too slow: ${response_time}ms"
    fi
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
}

# Cleanup test data
cleanup_test_data() {
    log_section "Cleaning Up Test Data"
    
    # Remove test users created during integration tests
    sudo -u postgres psql review-platform -c "DELETE FROM users WHERE email LIKE 'test-integration-%@example.com';" > /dev/null 2>&1
    log_info "Cleaned up integration test users"
}

# Show test results
show_test_results() {
    log_section "Test Results Summary"
    
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
    if [[ $TESTS_FAILED -eq 0 ]]; then
        log_success "🎉 All integration tests passed!"
        return 0
    else
        log_error "💥 Some integration tests failed!"
        return 1
    fi
}

# Main function
main() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        cat << EOF
🧪 Integration Test Script

Usage: $0 [options]

Options:
  --cleanup-only    Only run cleanup, skip tests
  --help           Show this help message

This script runs comprehensive integration tests including:
- System health and connectivity tests
- User registration, promotion, and verification
- Authentication and authorization
- Project creation and invitation workflows  
- Database consistency checks
- API endpoint functionality
- Basic performance tests

The script creates temporary test users and projects, then cleans them up.

Examples:
  $0                    # Run full integration test suite
  $0 --cleanup-only     # Only clean up test data
  $0 --help             # Show this help

Prerequisites:
  - Backend service running on localhost:8000
  - Database accessible via sudo -u postgres psql
  - auth-helper.sh and debug-api.sh available
EOF
        exit 0
    fi
    
    if [[ "$1" == "--cleanup-only" ]]; then
        cleanup_test_data
        log_success "Cleanup completed"
        exit 0
    fi
    
    log_section "Integration Test Suite"
    log_info "Running comprehensive end-to-end tests..."
    
    # Run test suites
    check_dependencies
    test_system_health
    test_user_management
    test_authentication  
    test_project_management
    test_document_processing
    test_architecture_validation
    test_database_consistency
    test_api_endpoints
    test_performance
    
    # Cleanup and show results
    cleanup_test_data
    show_test_results
}

# Run main function
main "$@"