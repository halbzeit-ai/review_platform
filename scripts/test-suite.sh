#!/bin/bash

# Comprehensive Test Suite
# Orchestrates all testing scripts for complete system validation

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
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_DIR="/tmp/test-suite-logs-$TIMESTAMP"

# Test suite configuration
SUITE_CONFIG=(
    "pre_validation|Pre-Test Validation|pre-test-validation.sh|required"
    "seed_data|Test Data Seeding|seed-test-data.sh|optional" 
    "integration|Integration Tests|integration-test.sh|required"
    "document_processing|Document Processing Tests|document-processing-test.sh|required"
    "workflow|End-to-End Workflow|auth-helper.sh workflow-test|optional"
)

# Results tracking
declare -A SUITE_RESULTS=()
declare -a EXECUTED_TESTS=()
TOTAL_SUITES=0
PASSED_SUITES=0
FAILED_SUITES=0

# Create log directory
create_log_directory() {
    mkdir -p "$LOG_DIR"
    log_info "Test logs will be saved to: $LOG_DIR"
}

# Execute test suite
execute_suite() {
    local suite_id="$1"
    local suite_name="$2"
    local suite_script="$3"
    local suite_type="$4"
    
    log_section "Running: $suite_name"
    
    local log_file="$LOG_DIR/${suite_id}.log"
    local start_time end_time duration
    start_time=$(date +%s)
    
    TOTAL_SUITES=$((TOTAL_SUITES + 1))
    EXECUTED_TESTS+=("$suite_name")
    
    # Execute the test suite
    local exit_code=0
    if [[ "$suite_script" == *" "* ]]; then
        # Handle commands with arguments (e.g., "auth-helper.sh workflow-test")
        eval "$SCRIPT_DIR/$suite_script" > "$log_file" 2>&1 || exit_code=$?
    else
        # Handle simple script execution
        "$SCRIPT_DIR/$suite_script" > "$log_file" 2>&1 || exit_code=$?
    fi
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    
    # Record results
    if [[ $exit_code -eq 0 ]]; then
        PASSED_SUITES=$((PASSED_SUITES + 1))
        SUITE_RESULTS["$suite_id"]="PASS|${duration}s"
        log_success "$suite_name completed successfully (${duration}s)"
    else
        FAILED_SUITES=$((FAILED_SUITES + 1))
        SUITE_RESULTS["$suite_id"]="FAIL|${duration}s|exit_code_$exit_code"
        log_error "$suite_name failed (${duration}s, exit code: $exit_code)"
        
        # Show last few lines of log for immediate feedback
        echo ""
        log_warning "Last 5 lines from $suite_name log:"
        tail -5 "$log_file" 2>/dev/null || echo "No log output available"
        echo ""
        
        # For required suites, ask if we should continue
        if [[ "$suite_type" == "required" ]]; then
            log_warning "This is a required test suite that failed."
            read -p "Continue with remaining tests? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Test suite execution stopped by user"
                return 1
            fi
        fi
    fi
    
    return $exit_code
}

# Show comprehensive results
show_comprehensive_results() {
    log_section "Test Suite Results"
    
    echo ""
    log_info "Execution Summary:"
    echo "  📊 Total Suites: $TOTAL_SUITES"
    echo "  ✅ Passed: $PASSED_SUITES" 
    echo "  ❌ Failed: $FAILED_SUITES"
    
    if [[ $TOTAL_SUITES -gt 0 ]]; then
        local success_rate
        success_rate=$((PASSED_SUITES * 100 / TOTAL_SUITES))
        echo "  📈 Success Rate: ${success_rate}%"
    fi
    
    echo ""
    log_info "Detailed Results:"
    
    for suite_config in "${SUITE_CONFIG[@]}"; do
        IFS='|' read -r suite_id suite_name suite_script suite_type <<< "$suite_config"
        
        local result="${SUITE_RESULTS[$suite_id]:-SKIP|0s}"
        IFS='|' read -r status duration extra <<< "$result"
        
        local status_icon
        case "$status" in
            "PASS") status_icon="✅" ;;
            "FAIL") status_icon="❌" ;;
            "SKIP") status_icon="⏭️" ;;
            *) status_icon="❓" ;;
        esac
        
        printf "  %s %-25s %s (%s)\n" "$status_icon" "$suite_name" "$status" "$duration"
        
        if [[ "$status" == "FAIL" && -n "$extra" ]]; then
            echo "    └─ $extra"
        fi
    done
    
    echo ""
    log_info "Log Files:"
    for executed_test in "${EXECUTED_TESTS[@]}"; do
        local suite_id
        for suite_config in "${SUITE_CONFIG[@]}"; do
            IFS='|' read -r s_id s_name s_script s_type <<< "$suite_config"
            if [[ "$s_name" == "$executed_test" ]]; then
                suite_id="$s_id"
                break
            fi
        done
        
        if [[ -f "$LOG_DIR/${suite_id}.log" ]]; then
            echo "  📄 $executed_test: $LOG_DIR/${suite_id}.log"
        fi
    done
    
    echo ""
    if [[ $FAILED_SUITES -eq 0 ]]; then
        log_success "🎉 All test suites passed!"
        log_info "System is fully validated and ready for production use"
        return 0
    else
        if [[ $FAILED_SUITES -eq 1 && $PASSED_SUITES -gt 2 ]]; then
            log_warning "⚠️  Minor issues detected, but system is mostly functional"
            log_info "Consider reviewing the failed test and fixing issues"
        else
            log_error "💥 Multiple test suites failed"
            log_error "System requires attention before production use"
        fi
        return 1
    fi
}

# Generate test report
generate_test_report() {
    local report_file="$LOG_DIR/test-suite-report.md"
    
    cat > "$report_file" << EOF
# Test Suite Report

**Generated**: $(date)  
**Duration**: Total execution time across all suites  
**Environment**: $(./scripts/detect-claude-environment.sh 2>/dev/null || echo "Unknown")

## Summary

- **Total Suites**: $TOTAL_SUITES
- **Passed**: $PASSED_SUITES
- **Failed**: $FAILED_SUITES
- **Success Rate**: $((PASSED_SUITES * 100 / TOTAL_SUITES))%

## Detailed Results

| Test Suite | Status | Duration | Notes |
|------------|--------|----------|-------|
EOF

    for suite_config in "${SUITE_CONFIG[@]}"; do
        IFS='|' read -r suite_id suite_name suite_script suite_type <<< "$suite_config"
        
        local result="${SUITE_RESULTS[$suite_id]:-SKIP|0s}"
        IFS='|' read -r status duration extra <<< "$result"
        
        echo "| $suite_name | $status | $duration | $extra |" >> "$report_file"
    done
    
    cat >> "$report_file" << EOF

## Log Files

EOF
    
    for executed_test in "${EXECUTED_TESTS[@]}"; do
        echo "- [$executed_test Log](./${executed_test}.log)" >> "$report_file"
    done
    
    cat >> "$report_file" << EOF

## System Information

- **Backend Status**: $(curl -s http://localhost:8000/api/debug/health | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
- **Database**: $(sudo -u postgres psql review-platform -c 'SELECT version();' 2>/dev/null | head -3 | tail -1 | tr -d ' ' || echo "unknown")
- **Test Environment**: $LOG_DIR

## Recommendations

EOF

    if [[ $FAILED_SUITES -eq 0 ]]; then
        echo "✅ All tests passed! System is ready for production use." >> "$report_file"
    else
        echo "⚠️ Issues detected. Review failed test logs and fix issues before production deployment." >> "$report_file"
    fi
    
    log_success "Test report generated: $report_file"
}

# Cleanup function
cleanup_on_exit() {
    local exit_code=$?
    
    if [[ $exit_code -ne 0 && -d "$LOG_DIR" ]]; then
        log_warning "Test suite interrupted. Logs available at: $LOG_DIR"
    fi
    
    exit $exit_code
}

# Main function
main() {
    if [[ "$1" == "--help" || "$1" == "-h" ]]; then
        cat << EOF
🧪 Comprehensive Test Suite

Usage: $0 [options]

Options:
  --quick          Skip optional tests, run only required suites
  --report-only    Generate report from existing logs
  --clean          Remove all test logs and data
  --help           Show this help message

This script orchestrates all testing infrastructure:

REQUIRED SUITES:
  ✓ Pre-Test Validation      - System readiness checks
  ✓ Integration Tests        - End-to-end functionality tests  
  ✓ Document Processing Tests - Document upload and processing pipeline validation

OPTIONAL SUITES:
  ✓ Test Data Seeding       - Create comprehensive test environment
  ✓ Workflow Tests          - Complete user journey validation

The suite creates detailed logs for each test and generates a comprehensive
report with recommendations.

Examples:
  $0                       # Run full test suite
  $0 --quick               # Run only required tests
  $0 --clean               # Clean up all test data
  $0 --help                # Show this help

Output:
  - Individual test logs: /tmp/test-suite-logs-TIMESTAMP/
  - Comprehensive report: test-suite-report.md
  - Real-time console output with colored status indicators

Exit codes:
  0 = All tests passed
  1 = Some tests failed (check logs)
  2 = Critical system issues
EOF
        exit 0
    fi
    
    # Handle special options
    case "$1" in
        "--clean")
            log_section "Cleaning Test Data"
            log_warning "This will remove all test logs and data!"
            read -p "Are you sure? (y/N): " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                rm -rf /tmp/test-suite-logs-* 2>/dev/null || true
                "$SCRIPT_DIR/seed-test-data.sh" --clean 2>/dev/null || true
                "$SCRIPT_DIR/integration-test.sh" --cleanup-only 2>/dev/null || true
                log_success "Test data cleaned up"
            else
                log_info "Cleanup cancelled"
            fi
            exit 0
            ;;
        "--report-only")
            log_info "Report generation from existing logs not yet implemented"
            exit 1
            ;;
    esac
    
    # Set up exit trap
    trap cleanup_on_exit EXIT INT TERM
    
    log_section "Comprehensive Test Suite"
    log_info "Starting complete system validation..."
    
    create_log_directory
    
    # Determine which suites to run
    local run_optional=true
    if [[ "$1" == "--quick" ]]; then
        run_optional=false
        log_info "Quick mode: Running only required test suites"
    fi
    
    # Execute test suites
    local continue_execution=true
    for suite_config in "${SUITE_CONFIG[@]}"; do
        if [[ "$continue_execution" != true ]]; then
            break
        fi
        
        IFS='|' read -r suite_id suite_name suite_script suite_type <<< "$suite_config"
        
        # Skip optional suites in quick mode
        if [[ "$suite_type" == "optional" && "$run_optional" != true ]]; then
            log_info "Skipping optional suite: $suite_name"
            SUITE_RESULTS["$suite_id"]="SKIP|0s"
            continue
        fi
        
        # Check if script exists
        local script_path="$SCRIPT_DIR/$suite_script"
        if [[ "$suite_script" == *" "* ]]; then
            script_path="$SCRIPT_DIR/$(echo "$suite_script" | cut -d' ' -f1)"
        fi
        
        if [[ ! -f "$script_path" ]]; then
            log_error "Test script not found: $script_path"
            SUITE_RESULTS["$suite_id"]="FAIL|0s|script_not_found"
            FAILED_SUITES=$((FAILED_SUITES + 1))
            continue
        fi
        
        # Execute the suite
        if ! execute_suite "$suite_id" "$suite_name" "$suite_script" "$suite_type"; then
            if [[ "$suite_type" == "required" ]]; then
                continue_execution=false
            fi
        fi
    done
    
    # Generate results and report
    show_comprehensive_results
    generate_test_report
    
    # Final status
    echo ""
    if [[ $FAILED_SUITES -eq 0 ]]; then
        log_success "🎊 Complete test suite passed!"
        log_info "Your system is fully validated and production-ready"
    else
        log_warning "⚠️  Test suite completed with issues"
        log_info "Review the detailed results and logs above"
    fi
    
    log_info "Full report and logs: $LOG_DIR"
    
    # Return appropriate exit code
    [[ $FAILED_SUITES -eq 0 ]]
}

# Run main function
main "$@"