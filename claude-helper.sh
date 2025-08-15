#!/bin/bash

# Claude Environment-Aware Helper Script
# This script provides database operations, debugging, and cleanup tasks for Claude Code
# Works on both development and production environments with automatic detection

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Environment detection
detect_environment() {
    if [ -f "./scripts/detect-claude-environment.sh" ]; then
        ENVIRONMENT=$(./scripts/detect-claude-environment.sh | head -1)
    else
        # Fallback detection
        HOSTNAME=$(hostname)
        case "$HOSTNAME" in
            *"65.108.32.143"*|*"dev-cpu"*)
                ENVIRONMENT="dev_cpu"
                ;;
            *"135.181.63.224"*|*"prod-cpu"*)
                ENVIRONMENT="prod_cpu"
                ;;
            *"135.181.71.17"*|*"dev-gpu"*)
                ENVIRONMENT="dev_gpu"
                ;;
            *"135.181.63.133"*|*"prod-gpu"*)
                ENVIRONMENT="prod_gpu"
                ;;
            *)
                ENVIRONMENT="local"
                ;;
        esac
    fi
}

# Set environment-specific variables
set_environment_config() {
    detect_environment
    
    case "$ENVIRONMENT" in
        "dev_cpu"|"dev_gpu")
            DATABASE_NAME="review_dev"
            SHARED_FILESYSTEM="/mnt/dev-shared"
            ENV_DISPLAY="Development"
            ENV_COLOR="${CYAN}"
            ;;
        "prod_cpu"|"prod_gpu")
            DATABASE_NAME="review-platform"
            SHARED_FILESYSTEM="/mnt/CPU-GPU"
            ENV_DISPLAY="Production"
            ENV_COLOR="${RED}"
            ;;
        *)
            DATABASE_NAME="review_dev"
            SHARED_FILESYSTEM="/mnt/dev-shared"
            ENV_DISPLAY="Local/Unknown"
            ENV_COLOR="${YELLOW}"
            ;;
    esac
}

# Initialize environment
set_environment_config

# Display environment info
show_environment() {
    echo -e "${ENV_COLOR}═══════════════════════════════════════════════${NC}"
    echo -e "${ENV_COLOR}► Claude Helper - ${ENV_DISPLAY} Environment${NC}"
    echo -e "${ENV_COLOR}═══════════════════════════════════════════════${NC}"
    echo -e "${BLUE}Environment: ${ENV_COLOR}${ENVIRONMENT}${NC}"
    echo -e "${BLUE}Database: ${ENV_COLOR}${DATABASE_NAME}${NC}"
    echo -e "${BLUE}Shared FS: ${ENV_COLOR}${SHARED_FILESYSTEM}${NC}"
    if [ "$ENVIRONMENT" = "prod_cpu" ] || [ "$ENVIRONMENT" = "prod_gpu" ]; then
        echo -e "${RED}⚠️  PRODUCTION ENVIRONMENT - Use with caution${NC}"
    fi
    echo ""
}

case "$1" in
    env|environment)
        show_environment
        ;;
        
    migrate)
        show_environment
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
        sudo -u postgres psql "$DATABASE_NAME" -f "$2"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Migration completed successfully${NC}"
        else
            echo -e "${RED}❌ Migration failed${NC}"
            exit 1
        fi
        ;;
    
    migrate-check)
        show_environment
        echo -e "${YELLOW}Checking database schema...${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "\d project_documents" | grep -E "(Column|file_name)" || echo "No file_name column found"
        ;;
    
    db-connect)
        show_environment
        echo -e "${YELLOW}Connecting to database as postgres user...${NC}"
        sudo -u postgres psql "$DATABASE_NAME"
        ;;
    
    query)
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Please provide SQL query${NC}"
            echo "Usage: $0 query \"SELECT * FROM table_name;\""
            exit 1
        fi
        
        show_environment
        echo -e "${YELLOW}Running query...${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "$2"
        ;;
    
    db-check)
        show_environment
        echo -e "${YELLOW}Testing database connection...${NC}"
        
        # Test basic connection
        if sudo -u postgres psql "$DATABASE_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Database connection successful${NC}"
        else
            echo -e "${RED}❌ Database connection failed${NC}"
            exit 1
        fi
        
        # Check document counts
        DOC_COUNT=$(sudo -u postgres psql "$DATABASE_NAME" -t -c "SELECT COUNT(*) FROM project_documents;" 2>/dev/null | xargs)
        echo -e "${BLUE}📄 Found ${DOC_COUNT} documents in database${NC}"
        
        # Check dojo files if applicable
        DOJO_COUNT=$(sudo -u postgres psql "$DATABASE_NAME" -t -c "SELECT COUNT(*) FROM project_documents WHERE data_source = 'dojo';" 2>/dev/null | xargs)
        echo -e "${BLUE}🥋 Found ${DOJO_COUNT} dojo files in database${NC}"
        ;;
    
    services)
        show_environment
        # Delegate to appropriate service script based on environment
        if [ "$ENVIRONMENT" = "dev_cpu" ]; then
            if [ -f "./dev-services-improved.sh" ]; then
                ./dev-services-improved.sh $2
            else
                echo -e "${RED}❌ dev-services-improved.sh not found${NC}"
                exit 1
            fi
        else
            echo -e "${YELLOW}Service management on ${ENV_DISPLAY} environment:${NC}"
            echo -e "${BLUE}Use systemctl commands for production services:${NC}"
            echo "  sudo systemctl status review-platform.service"
            echo "  sudo systemctl restart review-platform.service"
            echo "  sudo systemctl status gpu-http-server.service"
        fi
        ;;
    
    quick-test)
        show_environment
        echo -e "${YELLOW}Running quick test for ${ENV_DISPLAY} environment...${NC}"
        
        # Check database
        echo -e "${BLUE}1. Checking database...${NC}"
        $0 db-check
        
        # Check key endpoints
        echo -e "${BLUE}2. Testing key endpoints...${NC}"
        echo -n "Health endpoint: "
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Working${NC}"
        else
            echo -e "${RED}❌ Failed${NC}"
        fi
        ;;
    
    git-status)
        show_environment
        echo -e "${YELLOW}Git status summary...${NC}"
        echo -e "${BLUE}Current branch:${NC}"
        git branch --show-current
        echo -e "${BLUE}Uncommitted changes:${NC}"
        git status --porcelain | wc -l | xargs echo "Files changed:"
        echo -e "${BLUE}Recent commits:${NC}"
        git log --oneline -5
        ;;
    
    gpu-logs)
        show_environment
        GPU_LOG_PATH="${SHARED_FILESYSTEM}/logs/gpu_http_server.log"
        if [ "$2" = "tail" ] || [ -z "$2" ]; then
            echo -e "${YELLOW}Following GPU processing logs...${NC}"
            echo -e "${BLUE}Log path: $GPU_LOG_PATH${NC}"
            echo -e "${BLUE}Press Ctrl+C to exit${NC}"
            tail -f "$GPU_LOG_PATH" 2>/dev/null || echo -e "${RED}❌ GPU log file not found. Is GPU service running?${NC}"
        elif [ "$2" = "errors" ]; then
            echo -e "${YELLOW}GPU processing errors and warnings...${NC}"
            if [ -f "$GPU_LOG_PATH" ]; then
                grep -E "(ERROR|WARNING|ValueError|Exception)" "$GPU_LOG_PATH" | tail -20
            else
                echo -e "${RED}❌ GPU log file not found${NC}"
            fi
        elif [ "$2" = "backend" ]; then
            echo -e "${YELLOW}GPU backend URL configuration...${NC}"
            if [ -f "$GPU_LOG_PATH" ]; then
                grep -E "(Using backend server|BACKEND_|cache.*analysis)" "$GPU_LOG_PATH" | tail -10
            else
                echo -e "${RED}❌ GPU log file not found${NC}"
            fi
        elif [ "$2" = "cache" ]; then
            echo -e "${YELLOW}GPU cache operations...${NC}"
            if [ -f "$GPU_LOG_PATH" ]; then
                grep -E "(cache.*analysis|Failed to cache|Successfully cached)" "$GPU_LOG_PATH" | tail -20
            else
                echo -e "${RED}❌ GPU log file not found${NC}"
            fi
        else
            echo -e "${YELLOW}Last 50 lines of GPU logs...${NC}"
            if [ -f "$GPU_LOG_PATH" ]; then
                tail -50 "$GPU_LOG_PATH"
            else
                echo -e "${RED}❌ GPU log file not found${NC}"
            fi
        fi
        ;;
    
    debug-cache)
        show_environment
        echo -e "${YELLOW}Debugging visual analysis caching issue...${NC}"
        
        echo -e "${BLUE}1. Checking backend cache endpoint logs...${NC}"
        BACKEND_LOG="${SHARED_FILESYSTEM}/logs/backend.log"
        if [ -f "$BACKEND_LOG" ]; then
            grep -E "(cache-visual-analysis|GPU caching)" "$BACKEND_LOG" | tail -5 || echo "No cache operations found in backend logs"
        else
            echo "Backend log file not found"
        fi
        
        echo -e "${BLUE}2. Checking GPU backend URL configuration...${NC}"
        GPU_LOG_PATH="${SHARED_FILESYSTEM}/logs/gpu_http_server.log"
        if [ -f "$GPU_LOG_PATH" ]; then
            grep -E "(Using backend server|BACKEND_|ValueError.*BACKEND)" "$GPU_LOG_PATH" | tail -3 || echo "No backend URL info found"
        else
            echo "GPU log file not found - GPU service may not be running"
        fi
        
        echo -e "${BLUE}3. Checking visual analysis cache database entries...${NC}"
        $0 query "SELECT COUNT(*) as cached_analyses, MAX(created_at) as latest_cache FROM visual_analysis_cache;"
        
        echo -e "${BLUE}4. Recent deck processing...${NC}"
        if [ -f "$GPU_LOG_PATH" ]; then
            grep -E "Processing deck.*with template" "$GPU_LOG_PATH" | tail -5 || echo "No recent deck processing found"
        fi
        ;;
    
    cache-check)
        show_environment
        echo -e "${YELLOW}Visual analysis cache status...${NC}"
        $0 query "SELECT document_id, vision_model_used, created_at FROM visual_analysis_cache ORDER BY created_at DESC LIMIT 10;" 
        ;;
    
    # ===============================
    # PROCESSING QUEUE COMMANDS
    # ===============================
    queue-status)
        show_environment
        echo -e "${YELLOW}📊 Processing Queue Status${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "
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
        show_environment
        LIMIT=${2:-10}
        echo -e "${YELLOW}📋 Recent Processing Queue Tasks (last $LIMIT)${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "
            SELECT 
                id,
                document_id,
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
        show_environment
        echo -e "${YELLOW}❌ Failed Processing Tasks${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "
            SELECT 
                id,
                document_id,
                task_type,
                last_error,
                retry_count,
                created_at,
                completed_at as failed_at
            FROM processing_queue 
            WHERE status = 'failed' 
            ORDER BY completed_at DESC 
            LIMIT 10;
        "
        ;;
    
    queue-document)
        show_environment
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Please provide document ID${NC}"
            echo "Usage: $0 queue-document <document_id>"
            exit 1
        fi
        
        echo -e "${YELLOW}🔍 Processing Queue for Document $2${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "
            SELECT 
                pq.id as task_id,
                pq.status,
                pq.task_type,
                pq.priority, 
                pq.created_at,
                pq.started_at,
                pq.completed_at,
                pq.last_error,
                pd.file_name,
                pd.processing_status as doc_status
            FROM processing_queue pq
            JOIN project_documents pd ON pq.document_id = pd.id
            WHERE pq.document_id = $2
            ORDER BY pq.created_at DESC;
        "
        ;;
    
    # ===============================
    # PROGRESS TRACKING DEBUGGING
    # ===============================
    progress-debug)
        show_environment
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Please provide document ID${NC}"
            echo "Usage: $0 progress-debug <document_id>"
            exit 1
        fi
        
        DOCUMENT_ID=$2
        echo -e "${YELLOW}🔍 Progress Debugging for Document $DOCUMENT_ID${NC}"
        
        echo -e "${BLUE}1. Document Status in Database:${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "
            SELECT 
                id, 
                file_name, 
                processing_status, 
                upload_date
            FROM project_documents 
            WHERE id = $DOCUMENT_ID;
        "
        
        echo -e "${BLUE}2. Processing Queue Status:${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "
            SELECT 
                id as task_id,
                status,
                progress_percentage,
                current_step,
                progress_message,
                created_at,
                started_at
            FROM processing_queue 
            WHERE document_id = $DOCUMENT_ID
            ORDER BY created_at DESC;
        "
        
        echo -e "${BLUE}3. Recent GPU Processing Logs:${NC}"
        GPU_LOG_PATH="${SHARED_FILESYSTEM}/logs/gpu_http_server.log"
        if [ -f "$GPU_LOG_PATH" ]; then
            grep "document.*$DOCUMENT_ID" "$GPU_LOG_PATH" | tail -10 || echo "No recent logs found for document $DOCUMENT_ID"
        else
            echo "GPU log file not found"
        fi
        ;;
    
    progress-test)
        show_environment
        echo -e "${YELLOW}🧪 Testing Progress API Endpoints${NC}"
        
        echo -e "${BLUE}1. Recent Documents:${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "
            SELECT id, file_name, processing_status, upload_date 
            FROM project_documents 
            ORDER BY upload_date DESC 
            LIMIT 5;
        "
        
        echo -e "${BLUE}2. Testing Progress Endpoint for Latest Document:${NC}"
        LATEST_DOC=$(sudo -u postgres psql "$DATABASE_NAME" -t -c "SELECT id FROM project_documents ORDER BY upload_date DESC LIMIT 1;" | xargs)
        
        if [ ! -z "$LATEST_DOC" ]; then
            echo "Testing: curl http://localhost:8000/api/documents/processing-progress/$LATEST_DOC"
            curl -s "http://localhost:8000/api/documents/processing-progress/$LATEST_DOC" | python3 -m json.tool 2>/dev/null || echo "API call failed or returned invalid JSON"
        else
            echo "No documents found in database"
        fi
        ;;
    
    # ===============================
    # TEMPLATE OVERRIDE DEBUGGING
    # ===============================
    template-debug)
        show_environment
        if [ -z "$2" ]; then
            echo -e "${YELLOW}🔍 Template Override System Status${NC}"
            
            echo -e "${BLUE}1. Template Configurations:${NC}"
            sudo -u postgres psql "$DATABASE_NAME" -c "
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
            sudo -u postgres psql "$DATABASE_NAME" -c "
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
            GPU_LOG_PATH="${SHARED_FILESYSTEM}/logs/gpu_http_server.log"
            if [ -f "$GPU_LOG_PATH" ]; then
                grep -E "(classified as|Template selection|Classification result stored)" "$GPU_LOG_PATH" | tail -10 || echo "No recent classification logs found"
            else
                echo "GPU log file not found"
            fi
            
        else
            USER_EMAIL=$2
            echo -e "${YELLOW}🔍 Template Configuration for User: $USER_EMAIL${NC}"
            
            sudo -u postgres psql "$DATABASE_NAME" -c "
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
        show_environment
        echo -e "${YELLOW}🧪 Testing Classification System${NC}"
        
        echo -e "${BLUE}1. Recent Classification Logs:${NC}"
        GPU_LOG_PATH="${SHARED_FILESYSTEM}/logs/gpu_http_server.log"
        if [ -f "$GPU_LOG_PATH" ]; then
            grep -E "(Startup classified as|confidence|Template selection)" "$GPU_LOG_PATH" | tail -10 || echo "No classification logs found"
        else
            echo "GPU log file not found"
        fi
        
        echo -e "${BLUE}2. Template Usage Analytics:${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "
            SELECT 
                'Completed Documents' as analysis_type,
                COUNT(*) as usage_count
            FROM project_documents pd
            WHERE pd.processing_status = 'completed'
                AND pd.upload_date > NOW() - INTERVAL '7 days'
            UNION ALL
            SELECT 
                'Processing Documents' as analysis_type,
                COUNT(*) as usage_count
            FROM project_documents pd
            WHERE pd.processing_status = 'processing';
        " 2>/dev/null || echo "Could not fetch document usage data"
        ;;
    
    # ===============================
    # ENHANCED LOGGING & MONITORING
    # ===============================
    logs)
        show_environment
        SERVICE=${2:-"all"}
        case "$SERVICE" in
            backend)
                echo -e "${YELLOW}📋 Backend Logs (following...)${NC}"
                tail -f "${SHARED_FILESYSTEM}/logs/backend.log"
                ;;
            gpu)
                echo -e "${YELLOW}📋 GPU Processing Logs (following...)${NC}"
                tail -f "${SHARED_FILESYSTEM}/logs/gpu_http_server.log"
                ;;
            queue)
                echo -e "${YELLOW}📋 Queue Processing Logs${NC}"
                BACKEND_LOG="${SHARED_FILESYSTEM}/logs/backend.log"
                if [ -f "$BACKEND_LOG" ]; then
                    grep -E "(queue_processor|processing_queue)" "$BACKEND_LOG" | tail -20
                else
                    echo "Backend log file not found"
                fi
                ;;
            classification)
                echo -e "${YELLOW}📋 Classification & Template Logs${NC}"
                GPU_LOG_PATH="${SHARED_FILESYSTEM}/logs/gpu_http_server.log"
                if [ -f "$GPU_LOG_PATH" ]; then
                    grep -E "(classified as|Template selection|override)" "$GPU_LOG_PATH" | tail -20
                else
                    echo "GPU log file not found"
                fi
                ;;
            progress)
                echo -e "${YELLOW}📋 Progress Tracking Logs${NC}"
                BACKEND_LOG="${SHARED_FILESYSTEM}/logs/backend.log"
                if [ -f "$BACKEND_LOG" ]; then
                    grep -E "(processing-progress|update-deck-results)" "$BACKEND_LOG" | tail -20
                else
                    echo "Backend log file not found"
                fi
                ;;
            all|*)
                echo -e "${YELLOW}📋 All Service Logs (following...)${NC}"
                echo -e "${BLUE}Backend: ${SHARED_FILESYSTEM}/logs/backend.log${NC}"
                echo -e "${BLUE}GPU: ${SHARED_FILESYSTEM}/logs/gpu_http_server.log${NC}"
                echo -e "${YELLOW}Press Ctrl+C to exit${NC}"
                tail -f "${SHARED_FILESYSTEM}/logs/"*.log
                ;;
        esac
        ;;
    
    errors)
        show_environment
        echo -e "${YELLOW}❌ Recent Errors Across All Services${NC}"
        
        echo -e "${BLUE}1. Backend Errors:${NC}"
        BACKEND_LOG="${SHARED_FILESYSTEM}/logs/backend.log"
        if [ -f "$BACKEND_LOG" ]; then
            grep -E "(ERROR|Exception|Failed)" "$BACKEND_LOG" | tail -5
        else
            echo "Backend log file not found"
        fi
        
        echo -e "${BLUE}2. GPU Processing Errors:${NC}"  
        GPU_LOG_PATH="${SHARED_FILESYSTEM}/logs/gpu_http_server.log"
        if [ -f "$GPU_LOG_PATH" ]; then
            grep -E "(ERROR|Exception|Failed)" "$GPU_LOG_PATH" | tail -5
        else
            echo "GPU log file not found"
        fi
        
        echo -e "${BLUE}3. Queue Processing Errors:${NC}"
        if [ -f "$BACKEND_LOG" ]; then
            grep -E "(queue.*error|queue.*failed)" "$BACKEND_LOG" | tail -5
        else
            echo "Backend log file not found"
        fi
        ;;
    
    # ===============================
    # SYSTEM HEALTH & MANAGEMENT
    # ===============================
    health)
        show_environment
        echo -e "${YELLOW}🏥 System Health Check${NC}"
        
        echo -e "${BLUE}1. Service Status:${NC}"
        if [ "$ENVIRONMENT" = "prod_cpu" ] || [ "$ENVIRONMENT" = "prod_gpu" ]; then
            echo "Backend Service:"
            sudo systemctl is-active review-platform.service >/dev/null 2>&1 && echo -e "${GREEN}✅ Running${NC}" || echo -e "${RED}❌ Not Running${NC}"
            echo "GPU Service:"
            sudo systemctl is-active gpu-http-server.service >/dev/null 2>&1 && echo -e "${GREEN}✅ Running${NC}" || echo -e "${RED}❌ Not Running${NC}"
        else
            echo "Development environment - check services manually"
        fi
        
        echo -e "${BLUE}2. Database Health:${NC}"
        $0 db-check
        
        echo -e "${BLUE}3. GPU Health & Connectivity:${NC}"
        $0 gpu-health
        
        echo -e "${BLUE}4. Processing Queue Health:${NC}"
        $0 queue-status
        
        echo -e "${BLUE}5. Recent System Errors:${NC}"
        $0 errors
        ;;
    
    gpu-health)
        show_environment
        echo -e "${YELLOW}🖥️ GPU Health Check${NC}"
        
        # 1. GPU Service Status (Environment-Aware)
        echo -e "${BLUE}1. GPU Service Status:${NC}"
        
        # Determine if we're running on GPU server or CPU server
        if [ "$ENVIRONMENT" = "prod_gpu" ]; then
            # We're ON the GPU server - can check systemd directly
            echo "Checking GPU service on local GPU server..."
            if sudo systemctl is-active gpu-http-server.service >/dev/null 2>&1; then
                echo -e "${GREEN}✅ GPU Service Running (Local Check)${NC}"
                # Get service uptime
                UPTIME=$(sudo systemctl show gpu-http-server.service --property=ActiveEnterTimestamp --value)
                echo "Service started: $UPTIME"
            else
                echo -e "${RED}❌ GPU Service Not Running (Local Check)${NC}"
                # Check if it failed
                if sudo systemctl is-failed gpu-http-server.service >/dev/null 2>&1; then
                    echo -e "${RED}Service Status: Failed${NC}"
                    echo "Recent logs:"
                    sudo journalctl -u gpu-http-server.service --no-pager -n 5
                fi
            fi
        elif [ "$ENVIRONMENT" = "dev_gpu" ]; then
            # We're ON the development GPU server - can check systemd directly
            echo "Checking GPU service on local development GPU server..."
            if pgrep -f "gpu.*server" > /dev/null; then
                echo -e "${GREEN}✅ GPU process detected (Local Check)${NC}"
            else
                echo -e "${RED}❌ No GPU process found (Local Check)${NC}"
            fi
        else
            # We're on CPU server - can only check HTTP endpoints, not systemd
            echo -e "${BLUE}Running from CPU server - GPU systemd service status cannot be checked remotely${NC}"
            echo -e "${BLUE}GPU health will be determined by HTTP endpoint connectivity and logs${NC}"
        fi
        
        # 2. GPU HTTP Endpoint Connectivity
        echo -e "${BLUE}2. GPU HTTP Endpoint Connectivity:${NC}"
        
        # Determine GPU server based on environment
        if [ "$ENVIRONMENT" = "prod_cpu" ] || [ "$ENVIRONMENT" = "prod_gpu" ]; then
            GPU_HOST="135.181.63.133"  # prod_gpu
        else
            GPU_HOST="135.181.71.17"   # dev_gpu
        fi
        
        GPU_URL="http://${GPU_HOST}:8001"
        echo "Testing GPU endpoint: $GPU_URL"
        
        # Test basic connectivity
        if curl -s --connect-timeout 5 "$GPU_URL/health" >/dev/null 2>&1; then
            echo -e "${GREEN}✅ GPU HTTP endpoint reachable${NC}"
            
            # Test specific endpoints
            echo "Testing GPU endpoints:"
            
            # Health endpoint
            HEALTH_RESPONSE=$(curl -s --connect-timeout 5 "$GPU_URL/health" 2>/dev/null)
            if [ $? -eq 0 ]; then
                echo -e "  Health endpoint: ${GREEN}✅ OK${NC}"
                echo "  Response: $HEALTH_RESPONSE"
            else
                echo -e "  Health endpoint: ${RED}❌ Failed${NC}"
            fi
            
            # Models endpoint
            if curl -s --connect-timeout 5 "$GPU_URL/api/models" >/dev/null 2>&1; then
                echo -e "  Models endpoint: ${GREEN}✅ OK${NC}"
            else
                echo -e "  Models endpoint: ${RED}❌ Failed${NC}"
            fi
            
            # Vision analysis endpoint
            if curl -s --connect-timeout 5 -X POST "$GPU_URL/analyze-images" -H "Content-Type: application/json" -d '{}' >/dev/null 2>&1; then
                echo -e "  Vision analysis: ${GREEN}✅ OK${NC}"
            else
                echo -e "  Vision analysis: ${RED}❌ Failed${NC}"
            fi
            
        else
            echo -e "${RED}❌ GPU HTTP endpoint unreachable${NC}"
            echo "Possible issues:"
            echo "  - GPU service not running"
            echo "  - Network connectivity issues"
            echo "  - Firewall blocking port 8001"
        fi
        
        # 3. GPU Log Analysis
        echo -e "${BLUE}3. GPU Log Analysis:${NC}"
        GPU_LOG_PATH="${SHARED_FILESYSTEM}/logs/gpu_http_server.log"
        if [ -f "$GPU_LOG_PATH" ]; then
            echo "GPU log file: $GPU_LOG_PATH"
            
            # Check log size and recent activity
            LOG_SIZE=$(stat -f%z "$GPU_LOG_PATH" 2>/dev/null || stat -c%s "$GPU_LOG_PATH" 2>/dev/null)
            if [ "$LOG_SIZE" ]; then
                echo "Log size: $(($LOG_SIZE / 1024)) KB"
            fi
            
            # Check for recent activity (last 5 minutes)
            RECENT_ACTIVITY=$(find "$GPU_LOG_PATH" -mmin -5 2>/dev/null)
            if [ "$RECENT_ACTIVITY" ]; then
                echo -e "${GREEN}✅ Recent GPU activity detected${NC}"
            else
                echo -e "${YELLOW}⚠️ No recent GPU activity (last 5 minutes)${NC}"
            fi
            
            # Check for recent errors
            RECENT_ERRORS=$(tail -50 "$GPU_LOG_PATH" | grep -E "(ERROR|Exception|Failed)" | wc -l)
            if [ "$RECENT_ERRORS" -gt 0 ]; then
                echo -e "${RED}⚠️ Found $RECENT_ERRORS recent errors in GPU logs${NC}"
                echo "Recent errors:"
                tail -50 "$GPU_LOG_PATH" | grep -E "(ERROR|Exception|Failed)" | tail -3
            else
                echo -e "${GREEN}✅ No recent errors in GPU logs${NC}"
            fi
            
            # Check for startup messages
            if grep -q "Starting GPU HTTP server" "$GPU_LOG_PATH"; then
                LAST_START=$(grep "Starting GPU HTTP server" "$GPU_LOG_PATH" | tail -1)
                echo "Last startup: $LAST_START"
            fi
            
        else
            echo -e "${RED}❌ GPU log file not found: $GPU_LOG_PATH${NC}"
            echo "This suggests GPU service has never started or logs are not being written"
        fi
        
        # 4. GPU Models Status
        echo -e "${BLUE}4. GPU Models Status:${NC}"
        if curl -s --connect-timeout 5 "$GPU_URL/api/models" >/dev/null 2>&1; then
            MODELS_RESPONSE=$(curl -s --connect-timeout 5 "$GPU_URL/api/models" 2>/dev/null)
            if [ $? -eq 0 ]; then
                echo "Available models:"
                echo "$MODELS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$MODELS_RESPONSE"
            fi
        else
            echo -e "${RED}❌ Cannot retrieve models status${NC}"
        fi
        
        # 5. Backend-GPU Communication
        echo -e "${BLUE}5. Backend-GPU Communication:${NC}"
        
        # Check if backend can reach GPU
        echo "Testing backend to GPU connectivity..."
        
        # Look for recent backend-GPU communication in logs
        BACKEND_LOG="${SHARED_FILESYSTEM}/logs/backend.log"
        if [ -f "$BACKEND_LOG" ]; then
            RECENT_GPU_CALLS=$(tail -100 "$BACKEND_LOG" | grep -E "(gpu.*8001|GPU.*processing|Failed to connect to GPU)" | wc -l)
            if [ "$RECENT_GPU_CALLS" -gt 0 ]; then
                echo -e "${GREEN}✅ Recent backend-GPU communication detected${NC}"
                echo "Recent GPU calls:"
                tail -100 "$BACKEND_LOG" | grep -E "(gpu.*8001|GPU.*processing)" | tail -2
                
                # Check for connection failures
                GPU_FAILURES=$(tail -100 "$BACKEND_LOG" | grep -E "(Failed to connect to GPU|GPU.*error)" | wc -l)
                if [ "$GPU_FAILURES" -gt 0 ]; then
                    echo -e "${RED}⚠️ Found $GPU_FAILURES recent GPU connection failures${NC}"
                fi
            else
                echo -e "${YELLOW}⚠️ No recent backend-GPU communication found${NC}"
            fi
        else
            echo -e "${RED}❌ Backend log file not found${NC}"
        fi
        
        # 6. GPU Health Summary
        echo -e "${BLUE}6. GPU Health Summary:${NC}"
        
        # Count issues (environment-aware)
        ISSUES=0
        
        # Only check systemd service if we're actually ON a GPU server
        if [ "$ENVIRONMENT" = "prod_gpu" ]; then
            if ! sudo systemctl is-active gpu-http-server.service >/dev/null 2>&1; then
                ISSUES=$((ISSUES + 1))
            fi
        elif [ "$ENVIRONMENT" = "dev_gpu" ]; then
            if ! pgrep -f "gpu.*server" > /dev/null; then
                ISSUES=$((ISSUES + 1))
            fi
        fi
        
        # Always check HTTP endpoint (works from any server)
        if ! curl -s --connect-timeout 5 "$GPU_URL/health" >/dev/null 2>&1; then
            ISSUES=$((ISSUES + 1))
        fi
        
        # Always check log file (shared filesystem)
        if [ ! -f "$GPU_LOG_PATH" ]; then
            ISSUES=$((ISSUES + 1))
        fi
        
        if [ "$ISSUES" -eq 0 ]; then
            echo -e "${GREEN}✅ GPU system appears healthy${NC}"
        else
            echo -e "${RED}⚠️ Found $ISSUES potential GPU issues${NC}"
            echo "Recommended actions:"
            
            # Environment-specific recommendations
            if [ "$ENVIRONMENT" = "prod_gpu" ]; then
                echo "  - Check: sudo systemctl status gpu-http-server.service"
                echo "  - Restart: sudo systemctl restart gpu-http-server.service"
                echo "  - Logs: sudo journalctl -u gpu-http-server.service -f"
            elif [ "$ENVIRONMENT" = "dev_gpu" ]; then
                echo "  - Check GPU process: pgrep -f 'gpu.*server'"
                echo "  - Restart GPU development service manually"
            elif [ "$ENVIRONMENT" = "prod_cpu" ]; then
                echo "  - SSH to GPU server (135.181.63.133) to check systemd service"
                echo "  - Or ask someone with GPU server access to check"
            elif [ "$ENVIRONMENT" = "dev_cpu" ]; then
                echo "  - SSH to development GPU server (135.181.71.17) to check service"
                echo "  - Or use development service management scripts"
            fi
            
            # Universal recommendations (work from any server)
            echo "  - Check GPU logs: tail -f $GPU_LOG_PATH"
            echo "  - Test manually: curl $GPU_URL/health"
        fi
        ;;
    
    restart-services)
        show_environment
        echo -e "${YELLOW}🔄 Restarting Services (Environment-Aware)${NC}"
        
        if [ "$ENVIRONMENT" = "prod_cpu" ]; then
            echo -e "${RED}⚠️  This will restart production CPU services${NC}"
            echo "Available actions from production CPU server:"
            echo "  - Backend service (review-platform.service)"
            echo "  - GPU service must be restarted from GPU server (135.181.63.133)"
            
            read -p "Restart backend service only? (type 'yes' to confirm): " confirm
            if [ "$confirm" = "yes" ]; then
                echo "Restarting backend service..."
                sudo systemctl restart review-platform.service
                echo -e "${GREEN}✅ Backend service restarted${NC}"
                echo -e "${BLUE}Note: GPU service on 135.181.63.133 was not restarted${NC}"
                sleep 2
                $0 health
            else
                echo "Cancelled"
            fi
            
        elif [ "$ENVIRONMENT" = "prod_gpu" ]; then
            echo -e "${RED}⚠️  This will restart production GPU service${NC}"
            echo "Available actions from production GPU server:"
            echo "  - GPU service (gpu-http-server.service)"
            echo "  - Backend service must be restarted from CPU server (135.181.63.224)"
            
            read -p "Restart GPU service only? (type 'yes' to confirm): " confirm
            if [ "$confirm" = "yes" ]; then
                echo "Restarting GPU service..."
                sudo systemctl restart gpu-http-server.service
                echo -e "${GREEN}✅ GPU service restarted${NC}"
                echo -e "${BLUE}Note: Backend service on 135.181.63.224 was not restarted${NC}"
                sleep 2
                $0 gpu-health
            else
                echo "Cancelled"
            fi
            
        elif [ "$ENVIRONMENT" = "dev_cpu" ]; then
            echo -e "${YELLOW}Development CPU environment detected${NC}"
            echo -e "${YELLOW}Use development service management scripts for development environment${NC}"
            echo "Try: ./dev-services-improved.sh restart"
            
        elif [ "$ENVIRONMENT" = "dev_gpu" ]; then
            echo -e "${YELLOW}Development GPU environment detected${NC}"
            echo -e "${YELLOW}Use development service management scripts for development environment${NC}"
            echo "GPU development services should be managed manually or via dev scripts"
            
        else
            echo -e "${YELLOW}Local environment detected${NC}"
            echo -e "${YELLOW}Use development service management scripts for local development${NC}"
            echo "Try: ./dev-services-improved.sh restart"
        fi
        ;;
    
    clear-failed-tasks)
        show_environment
        echo -e "${YELLOW}🧹 Clearing Failed Tasks${NC}"
        FAILED_COUNT=$(sudo -u postgres psql "$DATABASE_NAME" -t -c "SELECT COUNT(*) FROM processing_queue WHERE status = 'failed';" | xargs)
        echo "Found $FAILED_COUNT failed tasks"
        
        if [ "$FAILED_COUNT" -gt 0 ]; then
            echo "Do you want to delete these failed tasks? (y/N)"
            read -r response
            if [ "$response" = "y" ] || [ "$response" = "Y" ]; then
                sudo -u postgres psql "$DATABASE_NAME" -c "DELETE FROM processing_queue WHERE status = 'failed';"
                echo -e "${GREEN}✅ Failed tasks cleared${NC}"
            else
                echo "Cancelled"
            fi
        fi
        ;;
    
    verify-cleanup)
        show_environment
        echo -e "${YELLOW}🔍 Comprehensive Database Cleanup Verification${NC}"
        echo -e "${BLUE}This command verifies that all legacy data has been properly cleaned up${NC}"
        echo ""
        
        # Function to run database query
        run_query() {
            local query="$1"
            local description="$2"
            echo -e "${BLUE}Checking: $description${NC}"
            sudo -u postgres psql "$DATABASE_NAME" -c "$query"
            echo ""
        }
        
        # 1. Check extraction_experiments table
        echo -e "${YELLOW}1. Extraction Experiments Cleanup${NC}"
        run_query "SELECT COUNT(*) as total_extraction_experiments FROM extraction_experiments;" "Total extraction experiments"
        run_query "SELECT id, experiment_name, document_ids, created_at FROM extraction_experiments ORDER BY created_at DESC LIMIT 5;" "Recent extraction experiments (should be empty)"
        
        # 2. Check visual_analysis_cache for any legacy data
        echo -e "${YELLOW}2. Visual Analysis Cache Status${NC}"
        run_query "SELECT COUNT(*) as total_cached_analyses FROM visual_analysis_cache;" "Total cached visual analyses"
        run_query "SELECT document_id, vision_model_used, created_at FROM visual_analysis_cache ORDER BY created_at DESC LIMIT 5;" "Recent visual analyses"
        
        # 3. Check processing_queue for any stuck tasks
        echo -e "${YELLOW}3. Processing Queue Health${NC}"
        run_query "SELECT status, COUNT(*) as count FROM processing_queue GROUP BY status;" "Queue status breakdown"
        run_query "SELECT id, document_id, status, progress_percentage, current_step FROM processing_queue WHERE status IN ('processing', 'queued') ORDER BY created_at DESC LIMIT 5;" "Active/queued tasks"
        
        # 4. Check project_documents table consistency
        echo -e "${YELLOW}4. Project Documents Consistency${NC}"
        run_query "SELECT processing_status, COUNT(*) as count FROM project_documents GROUP BY processing_status;" "Document processing status breakdown"
        run_query "SELECT id, file_name, processing_status, upload_date FROM project_documents WHERE processing_status = 'processing' ORDER BY upload_date DESC LIMIT 5;" "Documents stuck in processing"
        
        # 5. Check for any orphaned data relationships
        echo -e "${YELLOW}5. Data Relationship Integrity${NC}"
        run_query "SELECT COUNT(*) as orphaned_visual_cache FROM visual_analysis_cache v LEFT JOIN project_documents pd ON v.document_id = pd.id WHERE pd.id IS NULL;" "Orphaned visual analysis cache entries"
        run_query "SELECT COUNT(*) as orphaned_queue_tasks FROM processing_queue pq LEFT JOIN project_documents pd ON pq.document_id = pd.id WHERE pd.id IS NULL;" "Orphaned processing queue tasks"
        
        # 6. Summary and recommendations
        echo -e "${YELLOW}6. Cleanup Verification Summary${NC}"
        echo -e "${GREEN}✅ Verification complete. Check the results above:${NC}"
        echo -e "${BLUE}  • extraction_experiments should be 0 rows${NC}"
        echo -e "${BLUE}  • No documents should be stuck in 'processing' status${NC}"
        echo -e "${BLUE}  • No orphaned cache or queue entries${NC}"
        echo -e "${BLUE}  • Processing queue should be healthy${NC}"
        ;;
    
    cleanup-extraction-data)
        show_environment
        
        # Extra warning for production
        if [ "$ENVIRONMENT" = "prod_cpu" ] || [ "$ENVIRONMENT" = "prod_gpu" ]; then
            echo -e "${RED}⚠️  PRODUCTION ENVIRONMENT DETECTED${NC}"
            echo -e "${RED}⚠️  This will permanently delete production data${NC}"
            echo ""
        fi
        
        echo -e "${YELLOW}🗑️ COMPREHENSIVE Extraction Data Cleanup${NC}"
        echo -e "${RED}⚠️  WARNING: This will permanently delete ALL extraction and analysis data${NC}"
        echo -e "${BLUE}This includes:${NC}"
        echo -e "${BLUE}  • extraction_experiments (extraction results, classification, company names, funding, dates)${NC}"
        echo -e "${BLUE}  • specialized_analysis_results (clinical, regulatory, scientific analysis)${NC}"
        echo -e "${BLUE}  • visual_analysis_cache (cached visual analysis results)${NC}"
        echo -e "${BLUE}  • question_analysis_results (template question analysis)${NC}"
        echo -e "${BLUE}  • chapter_analysis_results (template chapter analysis)${NC}"
        echo ""
        
        read -p "Are you sure you want to proceed? (type 'yes' to confirm): " confirm
        if [ "$confirm" != "yes" ]; then
            echo -e "${BLUE}Cleanup cancelled${NC}"
            exit 0
        fi
        
        echo -e "${YELLOW}Performing COMPREHENSIVE extraction data cleanup...${NC}"
        
        # 1. Show what will be deleted from each table
        echo -e "${BLUE}📊 Current data counts before cleanup:${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "
            SELECT 'extraction_experiments' as table_name, COUNT(*) as count FROM extraction_experiments
            UNION ALL
            SELECT 'specialized_analysis_results', COUNT(*) FROM specialized_analysis_results  
            UNION ALL
            SELECT 'visual_analysis_cache', COUNT(*) FROM visual_analysis_cache
            UNION ALL
            SELECT 'question_analysis_results', COUNT(*) FROM question_analysis_results
            UNION ALL
            SELECT 'chapter_analysis_results', COUNT(*) FROM chapter_analysis_results
            ORDER BY table_name;
        "
        
        echo ""
        echo -e "${YELLOW}🗑️ Starting comprehensive cleanup...${NC}"
        
        # 2. Delete from all extraction/analysis tables
        echo -e "${BLUE}Deleting extraction_experiments...${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "DELETE FROM extraction_experiments;"
        
        echo -e "${BLUE}Deleting specialized_analysis_results...${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "DELETE FROM specialized_analysis_results;"
        
        echo -e "${BLUE}Deleting visual_analysis_cache...${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "DELETE FROM visual_analysis_cache;"
        
        echo -e "${BLUE}Deleting question_analysis_results...${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "DELETE FROM question_analysis_results;"
        
        echo -e "${BLUE}Deleting chapter_analysis_results...${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "DELETE FROM chapter_analysis_results;"
        
        echo -e "${GREEN}✅ All extraction and analysis data deleted${NC}"
        
        # 3. Verify cleanup with counts
        echo ""
        echo -e "${YELLOW}📊 Verification - data counts after cleanup:${NC}"
        sudo -u postgres psql "$DATABASE_NAME" -c "
            SELECT 'extraction_experiments' as table_name, COUNT(*) as remaining_count FROM extraction_experiments
            UNION ALL
            SELECT 'specialized_analysis_results', COUNT(*) FROM specialized_analysis_results  
            UNION ALL
            SELECT 'visual_analysis_cache', COUNT(*) FROM visual_analysis_cache
            UNION ALL
            SELECT 'question_analysis_results', COUNT(*) FROM question_analysis_results
            UNION ALL
            SELECT 'chapter_analysis_results', COUNT(*) FROM chapter_analysis_results
            ORDER BY table_name;
        "
        
        # 4. Run comprehensive verification
        echo ""
        echo -e "${YELLOW}🔍 Running comprehensive system verification...${NC}"
        $0 verify-cleanup
        
        echo ""
        echo -e "${GREEN}✅ COMPREHENSIVE extraction data cleanup completed${NC}"
        echo -e "${GREEN}✅ All extraction results should now be removed from UI${NC}"
        ;;
    
    *)
        show_environment
        echo -e "${BLUE}Database Commands:${NC}"
        echo "  migrate <file>     - Run database migration with elevated privileges"
        echo "  query \"SQL\"        - Run SQL query on database"
        echo "  migrate-check      - Check database schema"
        echo "  db-connect         - Connect to database as postgres user"
        echo "  db-check          - Test database connection and show info"
        echo ""
        echo -e "${BLUE}Service Commands:${NC}"
        echo "  services <cmd>     - Manage services (environment-aware)"
        echo ""
        echo -e "${BLUE}Development Commands:${NC}"
        echo "  quick-test         - Run comprehensive environment test"
        echo "  git-status         - Show git status summary"
        echo ""
        echo -e "${BLUE}GPU & Cache Debugging:${NC}"
        echo "  gpu-health         - Comprehensive GPU health and connectivity check"
        echo "  gpu-logs [tail]    - Follow GPU processing logs in real-time"
        echo "  gpu-logs errors    - Show recent GPU errors and warnings"
        echo "  gpu-logs backend   - Show GPU backend URL configuration"
        echo "  gpu-logs cache     - Show GPU caching operations"
        echo "  debug-cache        - Comprehensive cache debugging analysis"
        echo "  cache-check        - Check visual analysis cache database status"
        echo ""
        echo -e "${BLUE}Processing Queue Commands:${NC}"
        echo "  queue-status           - Show processing queue status summary"
        echo "  queue-list [limit]     - List recent processing tasks (default: 10)"
        echo "  queue-errors           - Show failed processing tasks"
        echo "  queue-document <id>    - Show processing history for specific document"
        echo ""
        echo -e "${BLUE}Progress & Debugging:${NC}"
        echo "  progress-debug <id>    - Debug progress tracking for specific document"
        echo "  progress-test          - Test progress API endpoints"
        echo "  template-debug [email] - Debug template override system"
        echo "  classification-test    - Test classification system"
        echo ""
        echo -e "${BLUE}Enhanced Logging & Monitoring:${NC}"
        echo "  logs [service]         - Follow logs (backend|gpu|queue|classification|progress|all)"
        echo "  errors                 - Show recent errors across all services"
        echo "  health                 - Comprehensive system health check"
        echo ""
        echo -e "${BLUE}System Management:${NC}"
        echo "  restart-services       - Restart backend and GPU services (production)"
        echo "  clear-failed-tasks     - Clear failed processing tasks from queue"
        echo ""
        echo -e "${BLUE}Data Cleanup & Verification:${NC}"
        echo "  verify-cleanup     - Comprehensive verification that cleanup was successful"
        echo "  cleanup-extraction-data - DANGER: Permanently delete all extraction experiment data"
        echo ""
        echo -e "${BLUE}Environment:${NC}"
        echo "  env                - Show current environment details"
        echo ""
        echo -e "${BLUE}Examples:${NC}"
        echo "  $0 env"
        echo "  $0 health"
        echo "  $0 gpu-health"
        echo "  $0 queue-status"
        echo "  $0 progress-debug 5"
        echo "  $0 template-debug ramin@halbzeit.ai"
        echo "  $0 logs classification"
        echo "  $0 migrate migrations/add_column.sql"
        echo "  $0 services start"
        echo "  $0 gpu-logs tail"
        echo "  $0 debug-cache"
        echo "  $0 cache-check"
        echo "  $0 verify-cleanup"
        echo "  $0 cleanup-extraction-data"
        ;;
esac