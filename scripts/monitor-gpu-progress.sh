#!/bin/bash

# GPU Progress Monitor - Real-time monitoring of GPU processing progress
# Author: Claude

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

# Function to get current GPU processing status
get_gpu_status() {
    local last_entries=$(tail -n 100 /mnt/CPU-GPU/logs/gpu_http_server.log)
    
    # Extract current document being processed
    local current_doc=$(echo "$last_entries" | grep -o "document [0-9]*" | tail -1 | cut -d' ' -f2)
    local current_deck=$(echo "$last_entries" | grep -o "deck [0-9]*" | tail -1 | cut -d' ' -f2)
    
    # Extract page progress
    local page_progress=$(echo "$last_entries" | grep -o "Analyzing page [0-9]*/[0-9]*" | tail -1)
    local slide_progress=$(echo "$last_entries" | grep -o "slide [0-9]*" | tail -1)
    
    # Extract current phase
    local phase=""
    if echo "$last_entries" | grep -q "Visual analysis"; then
        phase="Visual Analysis"
    elif echo "$last_entries" | grep -q "Generating feedback"; then
        phase="Slide Feedback"
    elif echo "$last_entries" | grep -q "extraction"; then
        phase="Data Extraction"
    elif echo "$last_entries" | grep -q "template"; then
        phase="Template Processing"
    elif echo "$last_entries" | grep -q "specialized"; then
        phase="Specialized Analysis"
    fi
    
    # Extract model being used
    local model=$(echo "$last_entries" | grep -o "model: [a-z0-9:]*" | tail -1 | cut -d' ' -f2)
    
    echo -e "${BOLD}GPU Processing Status:${NC}"
    [ -n "$current_doc" ] && echo -e "  Document: ${GREEN}$current_doc${NC}"
    [ -n "$current_deck" ] && echo -e "  Deck: ${GREEN}$current_deck${NC}"
    [ -n "$phase" ] && echo -e "  Phase: ${YELLOW}$phase${NC}"
    [ -n "$page_progress" ] && echo -e "  Progress: ${CYAN}$page_progress${NC}"
    [ -n "$slide_progress" ] && echo -e "  Current: ${CYAN}$slide_progress${NC}"
    [ -n "$model" ] && echo -e "  Model: ${BLUE}$model${NC}"
}

# Function to check GPU utilization
check_gpu_util() {
    if command -v nvidia-smi &> /dev/null; then
        local gpu_util=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits | head -1)
        local mem_util=$(nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits | head -1)
        echo -e "\n${BOLD}GPU Utilization:${NC}"
        echo -e "  Compute: ${GREEN}${gpu_util}%${NC}"
        echo -e "  Memory: ${CYAN}${mem_util}${NC}"
    fi
}

# Function to check document completion in database
check_completion() {
    echo -e "\n${BOLD}Document Completion Status:${NC}"
    for doc_id in 5 6 7; do
        local status=$(sudo -u postgres psql -d review-platform -t -A -c "
            SELECT 
                CASE 
                    WHEN EXISTS(SELECT 1 FROM visual_analysis_cache WHERE document_id = $doc_id) THEN '✅ Visual'
                    ELSE '⏳ Visual'
                END || ' | ' ||
                CASE 
                    WHEN EXISTS(SELECT 1 FROM slide_feedback WHERE document_id = $doc_id) THEN '✅ Feedback'
                    ELSE '⏳ Feedback'
                END || ' | ' ||
                CASE 
                    WHEN EXISTS(SELECT 1 FROM extraction_experiments WHERE document_ids::text LIKE '%$doc_id%') THEN '✅ Extraction'
                    ELSE '⏳ Extraction'
                END || ' | ' ||
                CASE 
                    WHEN EXISTS(SELECT 1 FROM specialized_analysis_results WHERE document_id = $doc_id) THEN '✅ Specialized'
                    ELSE '⏳ Specialized'
                END
        ")
        
        local filename=$(sudo -u postgres psql -d review-platform -t -A -c "
            SELECT LEFT(file_name, 25) FROM project_documents WHERE id = $doc_id
        ")
        
        echo -e "  Doc $doc_id (${filename}): $status"
    done
}

# Main monitoring loop
monitor_loop() {
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}     GPU Processing Monitor${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}\n"
    
    while true; do
        clear
        echo -e "${CYAN}GPU Processing Monitor - $(date '+%Y-%m-%d %H:%M:%S')${NC}"
        echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
        
        get_gpu_status
        check_gpu_util
        check_completion
        
        echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}Refreshing in 5 seconds...${NC}"
        sleep 5
    done
}

# Handle command line arguments
case "${1:-}" in
    status)
        get_gpu_status
        check_completion
        ;;
    monitor)
        monitor_loop
        ;;
    *)
        echo -e "${CYAN}GPU Progress Monitor${NC}"
        echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
        echo "Usage: $0 [status|monitor]"
        echo ""
        echo "  status  - Show current GPU processing status"
        echo "  monitor - Real-time monitoring (updates every 5s)"
        exit 0
        ;;
esac