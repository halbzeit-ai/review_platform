#!/bin/bash

# Claude Development Helper Script
# This script provides common development tasks for Claude Code to use

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

case "$1" in
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
        sudo -u postgres psql review_dev -f "$2"
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✅ Migration completed successfully${NC}"
        else
            echo -e "${RED}❌ Migration failed${NC}"
            exit 1
        fi
        ;;
    
    migrate-check)
        echo -e "${YELLOW}Checking database schema...${NC}"
        sudo -u postgres psql review_dev -c "\d pitch_decks" | grep -E "(Column|zip_filename)" || echo "No zip_filename column found"
        ;;
    
    db-connect)
        echo -e "${YELLOW}Connecting to database as postgres user...${NC}"
        sudo -u postgres psql review_dev
        ;;
    
    query)
        if [ -z "$2" ]; then
            echo -e "${RED}❌ Please provide SQL query${NC}"
            echo "Usage: $0 query \"SELECT * FROM table_name;\""
            exit 1
        fi
        
        echo -e "${YELLOW}Running query...${NC}"
        sudo -u postgres psql review_dev -c "$2"
        ;;
    
    db-check)
        echo -e "${YELLOW}Testing database connection...${NC}"
        cd /opt/review-platform-dev/backend
        python -c "
from app.db.database import SessionLocal
from app.db.models import PitchDeck
from sqlalchemy import text
db = SessionLocal()
try:
    # Test basic connection
    result = db.execute(text('SELECT 1')).fetchone()
    print('✅ Database connection successful')
    
    # Check dojo files count
    dojo_count = db.query(PitchDeck).filter(PitchDeck.data_source == 'dojo').count()
    print(f'📁 Found {dojo_count} dojo files in database')
    
    # Check if zip_filename column exists
    try:
        result = db.execute(text(\"SELECT column_name FROM information_schema.columns WHERE table_name='pitch_decks' AND column_name='zip_filename'\")).fetchone()
        if result:
            print('✅ zip_filename column exists')
        else:
            print('❌ zip_filename column does not exist - migration needed')
    except Exception as e:
        print(f'⚠️  Could not check zip_filename column: {e}')
        
except Exception as e:
    print(f'❌ Database connection failed: {e}')
finally:
    db.close()
"
        ;;
    
    services)
        # Delegate to dev-services.sh
        if [ -f "/opt/review-platform-dev/dev-services.sh" ]; then
            /opt/review-platform-dev/dev-services.sh $2
        else
            echo -e "${RED}❌ dev-services.sh not found${NC}"
            exit 1
        fi
        ;;
    
    quick-test)
        echo -e "${YELLOW}Running quick development test...${NC}"
        
        # Check services
        echo -e "${BLUE}1. Checking services...${NC}"
        /opt/review-platform-dev/dev-services.sh status
        
        # Check database
        echo -e "${BLUE}2. Checking database...${NC}"
        $0 db-check
        
        # Check key endpoints
        echo -e "${BLUE}3. Testing key endpoints...${NC}"
        echo -n "Dojo files endpoint: "
        if curl -s http://localhost:5001/api/dojo/files > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Working${NC}"
        else
            echo -e "${RED}❌ Failed${NC}"
        fi
        
        echo -n "Dojo stats endpoint: "
        if curl -s http://localhost:5001/api/dojo/stats > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Working${NC}"
        else
            echo -e "${RED}❌ Failed${NC}"
        fi
        ;;
    
    git-status)
        echo -e "${YELLOW}Git status summary...${NC}"
        cd /opt/review-platform-dev
        echo -e "${BLUE}Current branch:${NC}"
        git branch --show-current
        echo -e "${BLUE}Uncommitted changes:${NC}"
        git status --porcelain | wc -l | xargs echo "Files changed:"
        echo -e "${BLUE}Recent commits:${NC}"
        git log --oneline -5
        ;;
    
    gpu-logs)
        GPU_LOG_PATH="/mnt/dev-shared/logs/gpu_processing.log"
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
                grep -E "(Using backend server|BACKEND_DEVELOPMENT|cache.*analysis)" "$GPU_LOG_PATH" | tail -10
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
        echo -e "${YELLOW}Debugging visual analysis caching issue...${NC}"
        
        echo -e "${BLUE}1. Checking backend cache endpoint logs...${NC}"
        grep -E "(cache-visual-analysis|GPU caching)" /opt/review-platform-dev/backend/backend.log | tail -5 || echo "No cache operations found in backend logs"
        
        echo -e "${BLUE}2. Checking GPU backend URL configuration...${NC}"
        GPU_LOG_PATH="/mnt/dev-shared/logs/gpu_processing.log"
        if [ -f "$GPU_LOG_PATH" ]; then
            grep -E "(Using backend server|BACKEND_DEVELOPMENT|ValueError.*BACKEND)" "$GPU_LOG_PATH" | tail -3 || echo "No backend URL info found"
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
        echo -e "${YELLOW}Visual analysis cache status...${NC}"
        $0 query "SELECT pitch_deck_id, vision_model_used, created_at FROM visual_analysis_cache ORDER BY created_at DESC LIMIT 10;" 
        ;;
    
    *)
        echo -e "${BLUE}Claude Development Helper${NC}"
        echo ""
        echo "Database Commands:"
        echo "  migrate <file>     - Run database migration with elevated privileges"
        echo "  query \"SQL\"        - Run SQL query on database"
        echo "  migrate-check      - Check if zip_filename column exists"
        echo "  db-connect         - Connect to database as postgres user"
        echo "  db-check          - Test database connection and show info"
        echo ""
        echo "Service Commands:"
        echo "  services <cmd>     - Run dev-services.sh commands (start|stop|restart|status|logs)"
        echo ""
        echo "Development Commands:"
        echo "  quick-test         - Run comprehensive development test"
        echo "  git-status         - Show git status summary"
        echo ""
        echo "GPU & Cache Debugging:"
        echo "  gpu-logs [tail]    - Follow GPU processing logs in real-time"
        echo "  gpu-logs errors    - Show recent GPU errors and warnings"
        echo "  gpu-logs backend   - Show GPU backend URL configuration"
        echo "  gpu-logs cache     - Show GPU caching operations"
        echo "  debug-cache        - Comprehensive cache debugging analysis"
        echo "  cache-check        - Check visual analysis cache database status"
        echo ""
        echo "Examples:"
        echo "  $0 migrate migrations/add_zip_filename_to_pitch_decks.sql"
        echo "  $0 services start"
        echo "  $0 gpu-logs tail"
        echo "  $0 debug-cache"
        echo "  $0 cache-check"
        ;;
esac