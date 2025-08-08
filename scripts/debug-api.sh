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
  tables           - List all database tables
  table <name>     - Get table structure and info
  env              - Show environment configuration
  all              - Run all debug checks
  help             - Show this help

Examples:
  $0 health                    # Basic health check
  $0 deck 143                  # Check deck 143 status
  $0 table pitch_decks         # Get pitch_decks table info
  $0 tables                    # List all tables
  $0 all                       # Run comprehensive debug

Debug Endpoints Available:
  GET /api/debug/health-detailed
  GET /api/debug/deck/{id}/status
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

cmd_all() {
    log_section "Comprehensive Debug Report"
    
    cmd_health
    cmd_env
    cmd_tables
    
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
    "tables")
        cmd_tables
        ;;
    "table")
        cmd_table "$2"
        ;;
    "env")
        cmd_env
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