#!/bin/bash

# Enhanced Claude Development Helper Script
# Enhanced version with processing queue, progress tracking, and template override debugging

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Environment detection
ENVIRONMENT="production"  # Assume production since we're on prod server
if [[ "$PWD" == *"review-platform-dev"* ]]; then
    ENVIRONMENT="development"
fi

# Set database name based on environment
if [ "$ENVIRONMENT" = "development" ]; then
    DB_NAME="review_dev"
    SHARED_LOGS="/mnt/dev-shared/logs"
else
    DB_NAME="review-platform"
    SHARED_LOGS="/mnt/CPU-GPU/logs"
fi

echo -e "${CYAN}🔧 Enhanced Claude Dev Helper - Environment: $ENVIRONMENT${NC}"

case "$1" in
    # ===============================
    # PROCESSING QUEUE COMMANDS
    # ===============================
    queue-status)
        echo -e "${YELLOW}📊 Processing Queue Status${NC}"
        sudo -u postgres psql $DB_NAME -c "
            SELECT 
                status,
                COUNT(*) as count,
                MIN(created_at) as oldest,
                MAX(created_at) as newest
            FROM processing_queue 
            GROUP BY status 
            ORDER BY 
                CASE status 
                    WHEN 'processing' THEN 1 
                    WHEN 'queued' THEN 2 
                    WHEN 'completed' THEN 3 
                    WHEN 'failed' THEN 4 
                END;
        "
        ;;
    
    queue-list)
        LIMIT=${2:-10}
        echo -e "${YELLOW}📋 Recent Processing Queue Tasks (last $LIMIT)${NC}"
        sudo -u postgres psql $DB_NAME -c "
            SELECT 
                id,
                pitch_deck_id,
                status,
                task_type,
                priority,
                created_at,
                started_at,
                completed_at,
                CASE 
                    WHEN completed_at IS NOT NULL AND started_at IS NOT NULL 
                    THEN EXTRACT(EPOCH FROM (completed_at - started_at))::INTEGER 
                    ELSE NULL 
                END as duration_seconds
            FROM processing_queue 
            ORDER BY created_at DESC 
            LIMIT $LIMIT;
        "
        ;;
    
    queue-errors)
        echo -e "${YELLOW}❌ Failed Processing Tasks${NC}"
        sudo -u postgres psql $DB_NAME -c "
            SELECT 
                id,
                pitch_deck_id,
                task_type,
                error_message,
                retry_count,
                created_at,
                failed_at
            FROM processing_queue 
            WHERE status = 'failed' 
            ORDER BY failed_at DESC 
            LIMIT 10;
        "
        ;;
    
    queue-deck)
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Please provide deck ID${NC}"
            echo "Usage: $0 queue-deck <deck_id>"
            exit 1
        fi
        
        echo -e "${YELLOW}🔍 Processing Queue for Deck $2${NC}"
        sudo -u postgres psql $DB_NAME -c "
            SELECT 
                pq.id as task_id,
                pq.status,
                pq.task_type,
                pq.priority, 
                pq.created_at,
                pq.started_at,
                pq.completed_at,
                pq.error_message,
                pd.file_name,
                pd.processing_status as deck_status
            FROM processing_queue pq
            JOIN pitch_decks pd ON pq.pitch_deck_id = pd.id
            WHERE pq.pitch_deck_id = $2
            ORDER BY pq.created_at DESC;
        "
        ;;
    
    # ===============================
    # PROGRESS TRACKING DEBUGGING
    # ===============================
    progress-debug)
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Please provide deck ID${NC}"
            echo "Usage: $0 progress-debug <deck_id>"
            exit 1
        fi
        
        DECK_ID=$2
        echo -e "${YELLOW}🔍 Progress Debugging for Deck $DECK_ID${NC}"
        
        echo -e "${BLUE}1. Deck Status in Database:${NC}"
        sudo -u postgres psql $DB_NAME -c "
            SELECT 
                id, 
                file_name, 
                processing_status, 
                created_at,
                updated_at
            FROM pitch_decks 
            WHERE id = $DECK_ID;
        "
        
        echo -e "${BLUE}2. Processing Queue Tasks:${NC}"
        $0 queue-deck $DECK_ID
        
        echo -e "${BLUE}3. Recent Progress API Calls:${NC}"
        grep -E "processing-progress/$DECK_ID" $SHARED_LOGS/backend.log | tail -5 || echo "No progress API calls found"
        
        echo -e "${BLUE}4. GPU Processing Logs for this Deck:${NC}"
        grep -E "deck.*$DECK_ID|pitch_deck_id.*$DECK_ID" $SHARED_LOGS/gpu_http_server.log | tail -10 || echo "No GPU processing logs found for this deck"
        ;;
    
    progress-test)
        echo -e "${YELLOW}🧪 Testing Progress API Endpoints${NC}"
        
        echo -e "${BLUE}1. Recent Decks:${NC}"
        sudo -u postgres psql $DB_NAME -c "
            SELECT id, file_name, processing_status, created_at 
            FROM pitch_decks 
            ORDER BY created_at DESC 
            LIMIT 5;
        "
        
        echo -e "${BLUE}2. Testing Progress Endpoint for Latest Deck:${NC}"
        LATEST_DECK=$(sudo -u postgres psql $DB_NAME -t -c "SELECT id FROM pitch_decks ORDER BY created_at DESC LIMIT 1;" | xargs)
        
        if [ ! -z "$LATEST_DECK" ]; then
            echo "Testing: curl http://localhost:8000/api/robust/documents/processing-progress/$LATEST_DECK"
            curl -s "http://localhost:8000/api/robust/documents/processing-progress/$LATEST_DECK" | python3 -m json.tool 2>/dev/null || echo "API call failed or returned invalid JSON"
        else
            echo "No decks found in database"
        fi
        ;;
    
    # ===============================
    # TEMPLATE OVERRIDE DEBUGGING
    # ===============================
    template-debug)
        if [ -z "$2" ]; then
            echo -e "${YELLOW}🔍 Template Override System Status${NC}"
            
            echo -e "${BLUE}1. Template Configurations:${NC}"
            sudo -u postgres psql $DB_NAME -c "
                SELECT 
                    tc.user_id,
                    u.email,
                    tc.use_single_template,
                    tc.selected_template_id,
                    at.name as template_name,
                    tc.created_at,
                    tc.updated_at
                FROM template_configurations tc
                JOIN users u ON tc.user_id = u.id
                LEFT JOIN analysis_templates at ON tc.selected_template_id = at.id
                ORDER BY tc.updated_at DESC;
            " 2>/dev/null || echo "Template configurations table not found - may need migration"
            
            echo -e "${BLUE}2. Available Templates:${NC}"
            sudo -u postgres psql $DB_NAME -c "
                SELECT 
                    id,
                    name,
                    healthcare_sector_id,
                    is_active,
                    (SELECT COUNT(*) FROM template_chapters WHERE template_id = at.id) as chapter_count
                FROM analysis_templates at
                WHERE is_active = true
                ORDER BY id;
            " 2>/dev/null || echo "Analysis templates table not found"
            
            echo -e "${BLUE}3. Recent Classification Results:${NC}"
            grep -E "(classified as|Template selection|Classification result stored)" $SHARED_LOGS/gpu_http_server.log | tail -10 || echo "No recent classification logs found"
            
        else
            USER_EMAIL=$2
            echo -e "${YELLOW}🔍 Template Configuration for User: $USER_EMAIL${NC}"
            
            sudo -u postgres psql $DB_NAME -c "
                SELECT 
                    tc.use_single_template,
                    tc.selected_template_id,
                    at.name as template_name,
                    tc.created_at,
                    tc.updated_at
                FROM template_configurations tc
                JOIN users u ON tc.user_id = u.id
                LEFT JOIN analysis_templates at ON tc.selected_template_id = at.id
                WHERE u.email = '$USER_EMAIL';
            "
        fi
        ;;
    
    classification-test)
        echo -e "${YELLOW}🧪 Testing Classification System${NC}"
        
        echo -e "${BLUE}1. Recent Classification Logs:${NC}"
        grep -E "(Startup classified as|confidence|Template selection)" $SHARED_LOGS/gpu_http_server.log | tail -10 || echo "No classification logs found"
        
        echo -e "${BLUE}2. Template Usage Analytics:${NC}"
        sudo -u postgres psql $DB_NAME -c "
            SELECT 
                'Standard Seven-Chapter Review' as analysis_type,
                COUNT(*) as usage_count
            FROM pitch_decks pd
            WHERE pd.processing_status = 'completed'
                AND pd.created_at > NOW() - INTERVAL '7 days'
            UNION ALL
            SELECT 
                'Other Templates' as analysis_type,
                0 as usage_count;
        " 2>/dev/null || echo "Could not fetch template usage data"
        ;;
    
    # ===============================
    # ENHANCED LOGGING & MONITORING
    # ===============================
    logs)
        SERVICE=${2:-"all"}
        case "$SERVICE" in
            backend)
                echo -e "${YELLOW}📋 Backend Logs (following...)${NC}"
                tail -f $SHARED_LOGS/backend.log
                ;;
            gpu)
                echo -e "${YELLOW}📋 GPU Processing Logs (following...)${NC}"
                tail -f $SHARED_LOGS/gpu_http_server.log
                ;;
            queue)
                echo -e "${YELLOW}📋 Queue Processing Logs${NC}"
                grep -E "(queue_processor|processing_queue)" $SHARED_LOGS/backend.log | tail -20
                ;;
            classification)
                echo -e "${YELLOW}📋 Classification & Template Logs${NC}"
                grep -E "(classified as|Template selection|override)" $SHARED_LOGS/gpu_http_server.log | tail -20
                ;;
            progress)
                echo -e "${YELLOW}📋 Progress Tracking Logs${NC}"
                grep -E "(processing-progress|update-deck-results)" $SHARED_LOGS/backend.log | tail -20
                ;;
            all|*)
                echo -e "${YELLOW}📋 All Service Logs (following...)${NC}"
                echo -e "${BLUE}Backend: $SHARED_LOGS/backend.log${NC}"
                echo -e "${BLUE}GPU: $SHARED_LOGS/gpu_http_server.log${NC}"
                echo -e "${PURPLE}Press Ctrl+C to exit${NC}"
                tail -f $SHARED_LOGS/*.log
                ;;
        esac
        ;;
    
    errors)
        echo -e "${YELLOW}❌ Recent Errors Across All Services${NC}"
        
        echo -e "${BLUE}1. Backend Errors:${NC}"
        grep -E "(ERROR|Exception|Failed)" $SHARED_LOGS/backend.log | tail -5
        
        echo -e "${BLUE}2. GPU Processing Errors:${NC}"  
        grep -E "(ERROR|Exception|Failed)" $SHARED_LOGS/gpu_http_server.log | tail -5
        
        echo -e "${BLUE}3. Queue Processing Errors:${NC}"
        grep -E "(queue.*error|queue.*failed)" $SHARED_LOGS/backend.log | tail -5
        ;;
    
    # ===============================
    # SYSTEM HEALTH & DIAGNOSTICS
    # ===============================
    health)
        echo -e "${YELLOW}🏥 System Health Check${NC}"
        
        echo -e "${BLUE}1. Service Status:${NC}"
        if [ "$ENVIRONMENT" = "production" ]; then
            echo "Backend Service:"
            sudo systemctl is-active review-platform.service && echo -e "${GREEN}✅ Running${NC}" || echo -e "${RED}❌ Not Running${NC}"
            echo "GPU Service:"
            sudo systemctl is-active gpu-http-server.service && echo -e "${GREEN}✅ Running${NC}" || echo -e "${RED}❌ Not Running${NC}"
        else
            echo "Development environment - check manually with dev-services.sh"
        fi
        
        echo -e "${BLUE}2. Database Connection:${NC}"
        sudo -u postgres psql $DB_NAME -c "SELECT 1 as connection_test;" > /dev/null && echo -e "${GREEN}✅ Database OK${NC}" || echo -e "${RED}❌ Database Failed${NC}"
        
        echo -e "${BLUE}3. Queue Processor:${NC}"
        grep "Starting queue processor" $SHARED_LOGS/backend.log | tail -1 && echo -e "${GREEN}✅ Queue Processor Started${NC}" || echo -e "${RED}❌ No Queue Processor Found${NC}"
        
        echo -e "${BLUE}4. Recent Activity:${NC}"
        echo -n "Tasks processed in last hour: "
        sudo -u postgres psql $DB_NAME -t -c "SELECT COUNT(*) FROM processing_queue WHERE completed_at > NOW() - INTERVAL '1 hour';" | xargs
        echo -n "Failed tasks in last hour: "
        sudo -u postgres psql $DB_NAME -t -c "SELECT COUNT(*) FROM processing_queue WHERE status = 'failed' AND created_at > NOW() - INTERVAL '1 hour';" | xargs
        ;;
    
    # ===============================
    # QUICK FIXES & UTILITIES
    # ===============================
    restart-services)
        if [ "$ENVIRONMENT" = "production" ]; then
            echo -e "${YELLOW}🔄 Restarting Production Services${NC}"
            sudo systemctl restart review-platform.service
            sudo systemctl restart gpu-http-server.service
            echo -e "${GREEN}✅ Services Restarted${NC}"
        else
            echo -e "${YELLOW}🔄 Use dev-services.sh restart for development${NC}"
        fi
        ;;
    
    clear-failed-tasks)
        echo -e "${YELLOW}🧹 Clearing Failed Tasks${NC}"
        FAILED_COUNT=$(sudo -u postgres psql $DB_NAME -t -c "SELECT COUNT(*) FROM processing_queue WHERE status = 'failed';" | xargs)
        echo "Found $FAILED_COUNT failed tasks"
        
        if [ "$FAILED_COUNT" -gt 0 ]; then
            echo "Do you want to delete these failed tasks? (y/N)"
            read -r response
            if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
                sudo -u postgres psql $DB_NAME -c "DELETE FROM processing_queue WHERE status = 'failed';"
                echo -e "${GREEN}✅ Failed tasks cleared${NC}"
            else
                echo "Cancelled"
            fi
        fi
        ;;
    
    # ===============================
    # LEGACY COMMANDS (from original script)
    # ===============================
    migrate)
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Please provide migration file path${NC}"
            echo "Usage: $0 migrate migrations/filename.sql"
            exit 1
        fi
        
        if [ ! -f "$2" ]; then
            echo -e "${RED}❌ Migration file not found: $2${NC}"
            exit 1
        fi
        
        echo -e "${YELLOW}Running migration: $2${NC}"
        sudo -u postgres psql $DB_NAME -f "$2"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Migration completed successfully${NC}"
        else
            echo -e "${RED}❌ Migration failed${NC}"
            exit 1
        fi
        ;;
    
    query)
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Please provide SQL query${NC}"
            echo "Usage: $0 query \"SELECT * FROM table_name;\""
            exit 1
        fi
        
        echo -e "${YELLOW}Running query...${NC}"
        sudo -u postgres psql $DB_NAME -c "$2"
        ;;
    
    *)
        echo -e "${CYAN}🔧 Enhanced Claude Development Helper${NC}"
        echo ""
        echo -e "${PURPLE}PROCESSING QUEUE COMMANDS:${NC}"
        echo "  queue-status           - Show processing queue status summary"
        echo "  queue-list [limit]     - List recent processing tasks (default: 10)"
        echo "  queue-errors           - Show failed processing tasks"
        echo "  queue-deck <id>        - Show processing history for specific deck"
        echo ""
        echo -e "${PURPLE}PROGRESS & DEBUGGING:${NC}"
        echo "  progress-debug <id>    - Debug progress tracking for specific deck"
        echo "  progress-test          - Test progress API endpoints"
        echo "  template-debug [email] - Debug template override system"
        echo "  classification-test    - Test classification system"
        echo ""
        echo -e "${PURPLE}LOGGING & MONITORING:${NC}"
        echo "  logs [service]         - Follow logs (backend|gpu|queue|classification|progress|all)"
        echo "  errors                 - Show recent errors across all services"
        echo "  health                 - Comprehensive system health check"
        echo ""
        echo -e "${PURPLE}SYSTEM MANAGEMENT:${NC}"
        echo "  restart-services       - Restart backend and GPU services (production)"
        echo "  clear-failed-tasks     - Clear failed processing tasks from queue"
        echo ""
        echo -e "${PURPLE}DATABASE COMMANDS:${NC}"
        echo "  migrate <file>         - Run database migration"
        echo "  query \"SQL\"            - Run SQL query on database"
        echo ""
        echo -e "${PURPLE}EXAMPLES:${NC}"
        echo "  $0 queue-status"
        echo "  $0 progress-debug 136"
        echo "  $0 template-debug ramin@halbzeit.ai"
        echo "  $0 logs classification"
        echo "  $0 health"
        echo ""
        echo -e "${CYAN}Environment: $ENVIRONMENT | Database: $DB_NAME | Logs: $SHARED_LOGS${NC}"
        ;;
esac