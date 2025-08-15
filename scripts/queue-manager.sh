#!/bin/bash

# Queue Manager - Comprehensive queue monitoring and management tool
# Author: Claude
# Purpose: Provide real-time insights and management for the processing queue

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Database connection
DB_NAME="review-platform"
DB_USER="postgres"

# Function to execute SQL queries
execute_sql() {
    sudo -u $DB_USER psql -d $DB_NAME -t -A -c "$1"
}

# Function to execute SQL with table format
execute_sql_table() {
    sudo -u $DB_USER psql -d $DB_NAME -c "$1"
}

# Function to show queue status
show_status() {
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}► Queue Status Overview${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    
    # Overall statistics
    local pending=$(execute_sql "SELECT COUNT(*) FROM processing_queue WHERE status = 'pending'")
    local processing=$(execute_sql "SELECT COUNT(*) FROM processing_queue WHERE status = 'processing'")
    local completed=$(execute_sql "SELECT COUNT(*) FROM processing_queue WHERE status = 'completed'")
    local failed=$(execute_sql "SELECT COUNT(*) FROM processing_queue WHERE status = 'failed'")
    
    echo -e "${BOLD}Queue Statistics:${NC}"
    echo -e "  ${GREEN}✓ Completed:${NC} $completed"
    echo -e "  ${BLUE}⟳ Processing:${NC} $processing"
    echo -e "  ${YELLOW}⏳ Pending:${NC} $pending"
    echo -e "  ${RED}✗ Failed:${NC} $failed"
    echo
    
    # Active tasks
    echo -e "${BOLD}Active Tasks:${NC}"
    execute_sql_table "
        SELECT 
            id,
            document_id,
            status,
            current_step,
            progress_percentage || '%' as progress,
            EXTRACT(EPOCH FROM (NOW() - started_at))/60 as minutes_running
        FROM processing_queue 
        WHERE status IN ('processing', 'pending')
        ORDER BY status DESC, created_at ASC
        LIMIT 10
    "
}

# Function to monitor queue in real-time
monitor_queue() {
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}► Real-time Queue Monitor${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop monitoring${NC}\n"
    
    while true; do
        clear
        echo -e "${CYAN}Queue Monitor - $(date '+%Y-%m-%d %H:%M:%S')${NC}"
        echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
        
        # Show current processing
        local processing_count=$(execute_sql "SELECT COUNT(*) FROM processing_queue WHERE status = 'processing'")
        if [ "$processing_count" -gt 0 ]; then
            echo -e "${GREEN}▶ Currently Processing:${NC}"
            execute_sql_table "
                SELECT 
                    document_id,
                    current_step,
                    progress_percentage || '%' as progress,
                    progress_message,
                    ROUND(EXTRACT(EPOCH FROM (NOW() - started_at))/60, 1) || ' min' as duration
                FROM processing_queue 
                WHERE status = 'processing'
            "
        else
            echo -e "${YELLOW}No tasks currently processing${NC}"
        fi
        
        echo
        
        # Show pending queue
        local pending_count=$(execute_sql "SELECT COUNT(*) FROM processing_queue WHERE status = 'pending'")
        echo -e "${BLUE}⏳ Pending Tasks: ${pending_count}${NC}"
        
        if [ "$pending_count" -gt 0 ]; then
            execute_sql_table "
                SELECT 
                    id,
                    document_id,
                    priority,
                    ROUND(EXTRACT(EPOCH FROM (NOW() - created_at))/60, 1) || ' min' as waiting_time
                FROM processing_queue 
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at ASC
                LIMIT 5
            "
        fi
        
        echo
        
        # Check if queue processor is active
        local last_activity=$(execute_sql "
            SELECT EXTRACT(EPOCH FROM (NOW() - MAX(started_at)))/60 
            FROM processing_queue 
            WHERE started_at IS NOT NULL
        ")
        
        if [ -z "$last_activity" ] || [ "$last_activity" = "" ]; then
            echo -e "${RED}⚠️  WARNING: No queue activity detected${NC}"
        elif (( $(echo "$last_activity > 5" | bc -l) )); then
            echo -e "${YELLOW}⚠️  WARNING: No activity for ${last_activity} minutes${NC}"
        else
            echo -e "${GREEN}✓ Queue processor active${NC}"
        fi
        
        sleep 2
    done
}

# Function to check queue processor health
check_health() {
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}► Queue Processor Health Check${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    
    # Check if backend is running
    if pgrep -f "uvicorn.*app.main:app" > /dev/null; then
        echo -e "${GREEN}✓ Backend service running${NC}"
        
        # Check for auto-reload
        if pgrep -f "uvicorn.*--reload" > /dev/null; then
            echo -e "${GREEN}✓ Auto-reload enabled${NC}"
        else
            echo -e "${YELLOW}⚠️  Auto-reload disabled${NC}"
        fi
    else
        echo -e "${RED}✗ Backend service not running${NC}"
        return 1
    fi
    
    # Check last queue activity
    local last_started=$(execute_sql "
        SELECT TO_CHAR(MAX(started_at), 'YYYY-MM-DD HH24:MI:SS')
        FROM processing_queue 
        WHERE started_at IS NOT NULL
    ")
    
    local last_completed=$(execute_sql "
        SELECT TO_CHAR(MAX(completed_at), 'YYYY-MM-DD HH24:MI:SS')
        FROM processing_queue 
        WHERE completed_at IS NOT NULL
    ")
    
    echo -e "\n${BOLD}Queue Activity:${NC}"
    echo -e "  Last task started: ${last_started:-Never}"
    echo -e "  Last task completed: ${last_completed:-Never}"
    
    # Check for stuck tasks
    local stuck_count=$(execute_sql "
        SELECT COUNT(*) 
        FROM processing_queue 
        WHERE status = 'processing' 
        AND started_at < NOW() - INTERVAL '30 minutes'
    ")
    
    if [ "$stuck_count" -gt 0 ]; then
        echo -e "\n${RED}⚠️  WARNING: $stuck_count tasks stuck in processing > 30 minutes${NC}"
        execute_sql_table "
            SELECT id, document_id, current_step, 
                   ROUND(EXTRACT(EPOCH FROM (NOW() - started_at))/60) || ' min' as stuck_duration
            FROM processing_queue 
            WHERE status = 'processing' 
            AND started_at < NOW() - INTERVAL '30 minutes'
        "
    fi
    
    # Check backend logs for queue processor
    echo -e "\n${BOLD}Recent Queue Processor Activity:${NC}"
    tail -n 100 /mnt/CPU-GPU/logs/backend.log | grep -i "queue" | tail -5 || echo "  No recent activity"
}

# Function to retry failed tasks
retry_failed() {
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}► Retrying Failed Tasks${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    
    local failed_count=$(execute_sql "SELECT COUNT(*) FROM processing_queue WHERE status = 'failed'")
    
    if [ "$failed_count" -eq 0 ]; then
        echo -e "${GREEN}No failed tasks to retry${NC}"
        return
    fi
    
    echo -e "${YELLOW}Found $failed_count failed tasks${NC}"
    execute_sql_table "
        SELECT id, document_id, current_step, error_message
        FROM processing_queue 
        WHERE status = 'failed'
        LIMIT 10
    "
    
    read -p "Retry all failed tasks? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        execute_sql "
            UPDATE processing_queue 
            SET status = 'pending', 
                retry_count = retry_count + 1,
                error_message = NULL,
                started_at = NULL,
                completed_at = NULL
            WHERE status = 'failed'
        "
        echo -e "${GREEN}✓ Reset $failed_count failed tasks to pending${NC}"
    fi
}

# Function to force process a specific document
force_process() {
    local doc_id=$1
    if [ -z "$doc_id" ]; then
        read -p "Enter document ID to process: " doc_id
    fi
    
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}► Force Processing Document $doc_id${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    
    # Check if document exists
    local doc_exists=$(execute_sql "SELECT COUNT(*) FROM project_documents WHERE id = $doc_id")
    if [ "$doc_exists" -eq 0 ]; then
        echo -e "${RED}Document $doc_id not found${NC}"
        return 1
    fi
    
    # Get document info
    local doc_info=$(execute_sql "
        SELECT pd.file_name || ' (Project: ' || p.company_id || ')'
        FROM project_documents pd
        JOIN projects p ON pd.project_id = p.id
        WHERE pd.id = $doc_id
    ")
    echo -e "Document: $doc_info"
    
    # Check existing queue entry
    local existing=$(execute_sql "SELECT COUNT(*) FROM processing_queue WHERE document_id = $doc_id")
    if [ "$existing" -gt 0 ]; then
        echo -e "${YELLOW}Removing existing queue entry${NC}"
        execute_sql "DELETE FROM processing_queue WHERE document_id = $doc_id"
    fi
    
    # Add to queue with high priority
    execute_sql "
        INSERT INTO processing_queue (
            document_id, task_type, status, priority, file_path, 
            progress_percentage, current_step, progress_message, 
            created_at, retry_count, company_id
        )
        SELECT 
            pd.id, 'pdf_analysis', 'pending', 10, pd.file_path,
            0, 'visual_analysis', 'Force processed via queue manager',
            NOW(), 0, p.company_id
        FROM project_documents pd
        JOIN projects p ON pd.project_id = p.id
        WHERE pd.id = $doc_id
    "
    
    echo -e "${GREEN}✓ Added document $doc_id to queue with high priority${NC}"
}

# Function to clear stuck tasks
clear_stuck() {
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}► Clearing Stuck Tasks${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    
    local stuck_count=$(execute_sql "
        SELECT COUNT(*) 
        FROM processing_queue 
        WHERE status = 'processing' 
        AND started_at < NOW() - INTERVAL '30 minutes'
    ")
    
    if [ "$stuck_count" -eq 0 ]; then
        echo -e "${GREEN}No stuck tasks found${NC}"
        return
    fi
    
    echo -e "${YELLOW}Found $stuck_count stuck tasks:${NC}"
    execute_sql_table "
        SELECT id, document_id, current_step, 
               ROUND(EXTRACT(EPOCH FROM (NOW() - started_at))/60) || ' min' as stuck_duration
        FROM processing_queue 
        WHERE status = 'processing' 
        AND started_at < NOW() - INTERVAL '30 minutes'
    "
    
    read -p "Reset stuck tasks to pending? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        execute_sql "
            UPDATE processing_queue 
            SET status = 'pending', 
                started_at = NULL,
                progress_message = 'Reset from stuck state'
            WHERE status = 'processing' 
            AND started_at < NOW() - INTERVAL '30 minutes'
        "
        echo -e "${GREEN}✓ Reset $stuck_count stuck tasks${NC}"
    fi
}

# Function to show detailed logs
show_logs() {
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}► Queue Processor Logs${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    
    echo -e "${BOLD}Last 20 queue-related log entries:${NC}"
    tail -n 200 /mnt/CPU-GPU/logs/backend.log | grep -i "queue\|processing_queue\|task" | tail -20
}

# Function to restart backend with queue processor
restart_backend() {
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}► Restarting Backend with Queue Processor${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    
    # Use the existing reliable script
    /opt/review-platform/dev-services-improved.sh restart backend
    
    sleep 3
    
    # Check if queue processor initialized
    if tail -n 50 /mnt/CPU-GPU/logs/backend.log | grep -q "Queue processor initialized"; then
        echo -e "${GREEN}✓ Queue processor initialized${NC}"
        
        # Check for actual activity
        echo -e "${YELLOW}Waiting for queue processor to start checking tasks...${NC}"
        sleep 5
        
        if tail -n 100 /mnt/CPU-GPU/logs/backend.log | grep -q "Starting queue processor background task"; then
            echo -e "${GREEN}✓ Queue processor background task started${NC}"
        else
            echo -e "${YELLOW}⚠️  Queue processor may not be actively checking tasks${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Queue processor may not have initialized${NC}"
    fi
}

# Function to trigger queue processing
trigger_processing() {
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}► Triggering Queue Processing${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    
    local pending_count=$(execute_sql "SELECT COUNT(*) FROM processing_queue WHERE status = 'pending'")
    
    if [ "$pending_count" -eq 0 ]; then
        echo -e "${GREEN}No pending tasks to process${NC}"
        return
    fi
    
    echo -e "${YELLOW}Found $pending_count pending tasks${NC}"
    
    # Check if backend is running
    if ! pgrep -f "uvicorn.*app.main:app" > /dev/null; then
        echo -e "${RED}Backend not running. Starting it...${NC}"
        restart_backend
    fi
    
    # Force a queue check by updating a pending task's timestamp
    execute_sql "
        UPDATE processing_queue 
        SET created_at = NOW() 
        WHERE status = 'pending' 
        AND id = (SELECT id FROM processing_queue WHERE status = 'pending' ORDER BY created_at ASC LIMIT 1)
    "
    
    echo -e "${GREEN}✓ Triggered queue processing${NC}"
    echo -e "${YELLOW}Monitoring for activity...${NC}"
    
    # Monitor for 10 seconds
    for i in {1..10}; do
        if tail -n 10 /mnt/CPU-GPU/logs/backend.log | grep -q "Checking for processing tasks\|Processing task"; then
            echo -e "${GREEN}✓ Queue processor is active!${NC}"
            return 0
        fi
        sleep 1
        echo -n "."
    done
    
    echo -e "\n${RED}⚠️  No queue activity detected. May need to restart backend.${NC}"
}

# Main menu
show_menu() {
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${CYAN}     Queue Manager - Main Menu${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
    echo -e "${BOLD}1)${NC} Show Status        - Current queue overview"
    echo -e "${BOLD}2)${NC} Monitor Queue      - Real-time monitoring"
    echo -e "${BOLD}3)${NC} Health Check       - Queue processor health"
    echo -e "${BOLD}4)${NC} Retry Failed       - Retry all failed tasks"
    echo -e "${BOLD}5)${NC} Force Process      - Add document to queue"
    echo -e "${BOLD}6)${NC} Clear Stuck        - Reset stuck tasks"
    echo -e "${BOLD}7)${NC} Show Logs          - Recent queue logs"
    echo -e "${BOLD}8)${NC} Restart Backend    - Restart with queue processor"
    echo -e "${BOLD}9)${NC} Trigger Processing - Force queue check"
    echo -e "${BOLD}0)${NC} Exit"
    echo -e "${CYAN}═══════════════════════════════════════════════${NC}"
}

# Handle command line arguments
case "${1:-}" in
    status)
        show_status
        ;;
    monitor)
        monitor_queue
        ;;
    health)
        check_health
        ;;
    retry)
        retry_failed
        ;;
    process)
        force_process "$2"
        ;;
    stuck)
        clear_stuck
        ;;
    logs)
        show_logs
        ;;
    restart)
        restart_backend
        ;;
    trigger)
        trigger_processing
        ;;
    *)
        if [ -n "${1:-}" ] && [ "$1" != "menu" ]; then
            echo -e "${RED}Unknown command: $1${NC}"
            echo "Usage: $0 [status|monitor|health|retry|process|stuck|logs|restart|trigger|menu]"
            exit 1
        fi
        
        # Interactive menu
        while true; do
            show_menu
            read -p "Select option: " choice
            case $choice in
                1) show_status; read -p "Press Enter to continue..." ;;
                2) monitor_queue ;;
                3) check_health; read -p "Press Enter to continue..." ;;
                4) retry_failed; read -p "Press Enter to continue..." ;;
                5) force_process; read -p "Press Enter to continue..." ;;
                6) clear_stuck; read -p "Press Enter to continue..." ;;
                7) show_logs; read -p "Press Enter to continue..." ;;
                8) restart_backend; read -p "Press Enter to continue..." ;;
                9) trigger_processing; read -p "Press Enter to continue..." ;;
                0) echo "Exiting..."; exit 0 ;;
                *) echo -e "${RED}Invalid option${NC}" ;;
            esac
        done
        ;;
esac