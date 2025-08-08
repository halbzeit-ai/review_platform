#!/bin/bash

# Progress Bar Debugging Script
# Comprehensive debugging for deck processing progress tracking

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Configuration
SHARED_LOGS="/mnt/CPU-GPU/logs"
DEBUG_API="http://localhost:8000/api/debug"

# Helper functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_section() { echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}\n${CYAN}► $1${NC}\n${CYAN}═══════════════════════════════════════════════${NC}"; }

# Function to check recent deck processing
check_recent_processing() {
    log_section "Recent Deck Processing Activity"
    
    log_info "Checking backend logs for recent deck uploads/processing..."
    if [ -f "$SHARED_LOGS/backend.log" ]; then
        echo -e "${YELLOW}📋 Recent deck uploads (last 50 lines):${NC}"
        tail -50 "$SHARED_LOGS/backend.log" | grep -i "deck\|upload\|process" | tail -10 || echo "No recent deck activity found"
    else
        log_error "Backend log not found at $SHARED_LOGS/backend.log"
    fi
    
    log_info "Checking GPU processing logs..."
    if [ -f "$SHARED_LOGS/gpu_http_server.log" ]; then
        echo -e "${YELLOW}📋 Recent GPU processing (last 50 lines):${NC}"
        tail -50 "$SHARED_LOGS/gpu_http_server.log" | grep -i "deck\|process\|stage" | tail -10 || echo "No recent GPU processing found"
    else
        log_error "GPU log not found at $SHARED_LOGS/gpu_http_server.log"
    fi
}

# Function to test database connectivity from backend
test_database_connection() {
    log_section "Database Connection Testing"
    
    log_info "Testing database tables and deck data..."
    curl -s "$DEBUG_API/database/tables" | python3 -m json.tool 2>/dev/null | head -20 || log_error "Failed to fetch database tables"
    
    log_info "Checking pitch_decks table structure..."
    curl -s "$DEBUG_API/database/table/pitch_decks/info" | python3 -m json.tool 2>/dev/null | head -30 || log_error "Failed to fetch pitch_decks info"
}

# Function to check specific deck processing status
check_deck_status() {
    local deck_id=${1:-""}
    
    if [ -z "$deck_id" ]; then
        log_info "Finding recent deck IDs from database..."
        # Try to get recent deck IDs
        RECENT_DECKS=$(curl -s "$DEBUG_API/database/table/pitch_decks/info" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    records = data.get('recent_records', [])
    if isinstance(records, list):
        for record in records[:3]:
            if isinstance(record, dict) and 'id' in record:
                print(record['id'])
except:
    pass
" 2>/dev/null)
        
        if [ -n "$RECENT_DECKS" ]; then
            log_info "Testing recent decks: $(echo $RECENT_DECKS | tr '\n' ' ')"
            for deck_id in $RECENT_DECKS; do
                test_single_deck "$deck_id"
            done
        else
            log_warning "No recent deck IDs found, testing common IDs..."
            for test_id in 140 143 144 150; do
                test_single_deck "$test_id"
            done
        fi
    else
        test_single_deck "$deck_id"
    fi
}

# Function to test a single deck's status
test_single_deck() {
    local deck_id=$1
    
    log_section "Deck $deck_id Processing Status"
    
    # Check deck status via debug API
    log_info "Fetching deck $deck_id status from debug API..."
    DECK_STATUS=$(curl -s "$DEBUG_API/deck/$deck_id/status" 2>/dev/null)
    
    if echo "$DECK_STATUS" | grep -q "not found"; then
        log_warning "Deck $deck_id not found in database"
        return
    fi
    
    echo "$DECK_STATUS" | python3 -m json.tool 2>/dev/null || echo "$DECK_STATUS"
    
    # Check logs for this specific deck
    log_info "Searching logs for deck $deck_id activity..."
    
    if [ -f "$SHARED_LOGS/backend.log" ]; then
        echo -e "${YELLOW}🔍 Backend log entries for deck $deck_id:${NC}"
        grep -i "deck.*$deck_id\|$deck_id.*deck" "$SHARED_LOGS/backend.log" | tail -5 || echo "No backend log entries found"
    fi
    
    if [ -f "$SHARED_LOGS/gpu_http_server.log" ]; then
        echo -e "${YELLOW}🔍 GPU processing entries for deck $deck_id:${NC}"
        grep -i "deck.*$deck_id\|$deck_id.*deck" "$SHARED_LOGS/gpu_http_server.log" | tail -5 || echo "No GPU log entries found"
    fi
}

# Function to check GPU server connectivity
check_gpu_connectivity() {
    log_section "GPU Server Communication"
    
    log_info "Checking backend to GPU communication..."
    
    # Look for GPU communication errors in backend logs
    if [ -f "$SHARED_LOGS/backend.log" ]; then
        echo -e "${YELLOW}🔍 GPU communication errors in backend log:${NC}"
        grep -i "gpu\|connection.*error\|timeout" "$SHARED_LOGS/backend.log" | tail -10 || echo "No GPU communication errors found"
    fi
    
    # Check if GPU server is responsive (from backend perspective)
    log_info "Checking recent GPU HTTP server activity..."
    if [ -f "$SHARED_LOGS/gpu_http_server.log" ]; then
        echo -e "${YELLOW}📋 Recent GPU HTTP server activity:${NC}"
        tail -20 "$SHARED_LOGS/gpu_http_server.log" | grep -i "request\|response\|error" || echo "No recent GPU HTTP activity found"
    fi
}

# Function to check processing queue status
check_processing_queue() {
    log_section "Processing Queue Analysis"
    
    log_info "Analyzing processing queue from logs..."
    
    # Look for queue-related activity
    if [ -f "$SHARED_LOGS/backend.log" ]; then
        echo -e "${YELLOW}🔍 Queue-related activity in backend:${NC}"
        grep -i "queue\|task\|job\|worker" "$SHARED_LOGS/backend.log" | tail -10 || echo "No queue activity found"
    fi
    
    if [ -f "$SHARED_LOGS/gpu_http_server.log" ]; then
        echo -e "${YELLOW}🔍 Processing tasks in GPU server:${NC}"
        grep -i "processing\|task\|queue\|start\|complete" "$SHARED_LOGS/gpu_http_server.log" | tail -10 || echo "No processing tasks found"
    fi
}

# Function to check progress callback functionality
check_progress_callbacks() {
    log_section "Progress Callback Analysis"
    
    log_info "Checking progress update mechanisms..."
    
    # Look for progress updates in backend logs
    if [ -f "$SHARED_LOGS/backend.log" ]; then
        echo -e "${YELLOW}🔍 Progress updates in backend log:${NC}"
        grep -i "progress\|callback\|update.*status\|stage" "$SHARED_LOGS/backend.log" | tail -10 || echo "No progress updates found"
    fi
    
    # Look for progress updates sent from GPU
    if [ -f "$SHARED_LOGS/gpu_http_server.log" ]; then
        echo -e "${YELLOW}🔍 Progress updates from GPU server:${NC}"
        grep -i "progress\|callback\|status.*update\|stage" "$SHARED_LOGS/gpu_http_server.log" | tail -10 || echo "No GPU progress updates found"
    fi
}

# Function to check model lookup issues
check_model_lookups() {
    log_section "Model Lookup Analysis"
    
    log_info "Checking for model/database lookup issues..."
    
    # Look for database/model errors
    if [ -f "$SHARED_LOGS/gpu_http_server.log" ]; then
        echo -e "${YELLOW}🔍 Database/model lookup errors:${NC}"
        grep -i "database\|model.*error\|connection.*failed\|auth.*failed" "$SHARED_LOGS/gpu_http_server.log" | tail -10 || echo "No database lookup errors found"
    fi
    
    if [ -f "$SHARED_LOGS/backend.log" ]; then
        echo -e "${YELLOW}🔍 Backend model/database errors:${NC}"
        grep -i "model.*error\|database.*error\|sql.*error" "$SHARED_LOGS/backend.log" | tail -10 || echo "No model/database errors found"
    fi
}

# Main function
main() {
    log_section "Progress Bar Debugging - Production Environment"
    
    case "${1:-all}" in
        "recent")
            check_recent_processing
            ;;
        "database") 
            test_database_connection
            ;;
        "deck")
            check_deck_status "$2"
            ;;
        "gpu")
            check_gpu_connectivity
            ;;
        "queue")
            check_processing_queue
            ;;
        "callbacks")
            check_progress_callbacks
            ;;
        "models")
            check_model_lookups
            ;;
        "all"|*)
            echo -e "${MAGENTA}🔍 Running comprehensive progress bar debugging...${NC}"
            check_recent_processing
            test_database_connection  
            check_deck_status
            check_gpu_connectivity
            check_processing_queue
            check_progress_callbacks
            check_model_lookups
            ;;
    esac
    
    log_section "Debugging Complete"
    
    echo -e "${CYAN}💡 Next Steps:${NC}"
    echo -e "${YELLOW}   • Check specific deck: $0 deck <deck_id>${NC}"
    echo -e "${YELLOW}   • Monitor live: tail -f $SHARED_LOGS/*.log${NC}"
    echo -e "${YELLOW}   • Test deck upload to trigger processing${NC}"
}

# Show help
if [ "$1" = "help" ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
    cat << EOF
🔧 Progress Bar Debugging Script

Usage: $0 [command] [options]

Commands:
  all              - Run comprehensive debugging (default)
  recent           - Check recent processing activity
  database         - Test database connectivity
  deck [id]        - Check specific deck status
  gpu              - Check GPU server communication
  queue            - Analyze processing queue
  callbacks        - Check progress callback functionality  
  models           - Check model lookup issues
  help             - Show this help

Examples:
  $0                    # Run all checks
  $0 deck 143          # Check specific deck
  $0 recent            # Check recent activity only
  $0 gpu               # Check GPU communication only

EOF
    exit 0
fi

# Run main function
main "$@"