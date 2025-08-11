#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENVIRONMENT=$(${SCRIPT_DIR}/scripts/detect-claude-environment.sh | head -1)

# Environment-aware configuration
case "$ENVIRONMENT" in
    "dev_cpu")
        PROJECT_ROOT="/opt/review-platform"
        EXTERNAL_IP="65.108.32.143"
        BACKEND_LOG="/opt/review-platform/backend/backend.log"
        FRONTEND_LOG="/opt/review-platform/frontend/frontend.log"
        ;;
    "prod_cpu")
        PROJECT_ROOT="/opt/review-platform"
        EXTERNAL_IP="135.181.63.224"
        BACKEND_LOG="/opt/review-platform/backend/backend.log"
        FRONTEND_LOG="/opt/review-platform/frontend/frontend.log"
        ;;
    *)
        # Default/local setup
        PROJECT_ROOT="/opt/review-platform"
        EXTERNAL_IP="localhost"
        BACKEND_LOG="./backend.log"
        FRONTEND_LOG="./frontend.log"
        ;;
esac

# Common configuration
BACKEND_PORT=8000
FRONTEND_PORT=3000
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"

echo -e "${BLUE}🌍 Environment: ${ENVIRONMENT}${NC}"
echo -e "${BLUE}📁 Project root: ${PROJECT_ROOT}${NC}"
echo -e "${BLUE}🌐 External IP: ${EXTERNAL_IP}${NC}"

# Function to check if backend has auto-reload enabled
check_backend_reload() {
    ps aux | grep -E "uvicorn.*--reload" | grep -v grep > /dev/null
    return $?
}

# Function to get PID of process on specific port
get_port_pid() {
    lsof -ti:$1 2>/dev/null
}

case "$1" in
    start)
        echo -e "${YELLOW}Starting development services intelligently...${NC}"
        
        # Check backend
        BACKEND_PID=$(get_port_pid $BACKEND_PORT)
        if [ -n "$BACKEND_PID" ]; then
            if check_backend_reload; then
                echo -e "${GREEN}✅ Backend already running with auto-reload on port $BACKEND_PORT${NC}"
            else
                echo -e "${YELLOW}⚠️  Backend running without auto-reload. Restarting...${NC}"
                kill -9 $BACKEND_PID
                sleep 2
                cd "$BACKEND_DIR"
                nohup uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > $BACKEND_LOG 2>&1 &
                echo -e "${GREEN}✅ Backend restarted with auto-reload${NC}"
            fi
        else
            echo -e "${BLUE}Starting backend...${NC}"
            cd "$BACKEND_DIR"
            nohup uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > $BACKEND_LOG 2>&1 &
            echo -e "${GREEN}✅ Backend started with auto-reload on port $BACKEND_PORT${NC}"
        fi
        
        # Check frontend
        FRONTEND_PID=$(get_port_pid $FRONTEND_PORT)
        if [ -n "$FRONTEND_PID" ]; then
            echo -e "${GREEN}✅ Frontend already running on port $FRONTEND_PORT${NC}"
        else
            echo -e "${BLUE}Starting frontend...${NC}"
            cd "$FRONTEND_DIR"
            DANGEROUSLY_DISABLE_HOST_CHECK=true nohup npm start > $FRONTEND_LOG 2>&1 &
            echo -e "${GREEN}✅ Frontend started on port $FRONTEND_PORT${NC}"
        fi
        
        echo -e "${BLUE}Services available at:${NC}"
        echo -e "  Backend API: http://$EXTERNAL_IP:$BACKEND_PORT/docs"
        echo -e "  Frontend: http://$EXTERNAL_IP:$FRONTEND_PORT"
        ;;
        
    stop)
        echo -e "${YELLOW}Stopping development services...${NC}"
        
        # Stop backend by port
        BACKEND_PID=$(get_port_pid $BACKEND_PORT)
        if [ -n "$BACKEND_PID" ]; then
            kill -9 $BACKEND_PID && echo -e "${GREEN}✅ Backend stopped${NC}"
        else
            echo -e "${BLUE}ℹ️  Backend not running on port $BACKEND_PORT${NC}"
        fi
        
        # Stop frontend by port
        FRONTEND_PID=$(get_port_pid $FRONTEND_PORT)
        if [ -n "$FRONTEND_PID" ]; then
            kill -9 $FRONTEND_PID && echo -e "${GREEN}✅ Frontend stopped${NC}"
        else
            echo -e "${BLUE}ℹ️  Frontend not running on port $FRONTEND_PORT${NC}"
        fi
        ;;
        
    restart)
        if [ "$2" == "backend" ] || [ "$2" == "be" ]; then
            echo -e "${YELLOW}Restarting backend only...${NC}"
            BACKEND_PID=$(get_port_pid $BACKEND_PORT)
            if [ -n "$BACKEND_PID" ]; then
                kill -9 $BACKEND_PID
                sleep 2
            fi
            cd "$BACKEND_DIR"
            nohup uvicorn app.main:app --host 0.0.0.0 --port $BACKEND_PORT --reload > $BACKEND_LOG 2>&1 &
            echo -e "${GREEN}✅ Backend restarted with auto-reload${NC}"
        elif [ "$2" == "frontend" ] || [ "$2" == "fe" ]; then
            echo -e "${YELLOW}Restarting frontend only...${NC}"
            FRONTEND_PID=$(get_port_pid $FRONTEND_PORT)
            if [ -n "$FRONTEND_PID" ]; then
                kill -9 $FRONTEND_PID
                sleep 2
            fi
            cd "$FRONTEND_DIR"
            DANGEROUSLY_DISABLE_HOST_CHECK=true nohup npm start > $FRONTEND_LOG 2>&1 &
            echo -e "${GREEN}✅ Frontend restarted${NC}"
        else
            echo -e "${YELLOW}Restarting all services...${NC}"
            $0 stop
            sleep 2
            $0 start
        fi
        ;;
        
    status)
        echo -e "${YELLOW}Checking service status...${NC}"
        
        # Backend status
        echo -n "Backend (port $BACKEND_PORT): "
        BACKEND_PID=$(get_port_pid $BACKEND_PORT)
        if [ -n "$BACKEND_PID" ]; then
            if check_backend_reload; then
                echo -e "${GREEN}✅ Running with auto-reload (PID: $BACKEND_PID)${NC}"
            else
                echo -e "${YELLOW}⚠️  Running without auto-reload (PID: $BACKEND_PID)${NC}"
            fi
        else
            echo -e "${RED}❌ Not running${NC}"
        fi
        
        # Frontend status
        echo -n "Frontend (port $FRONTEND_PORT): "
        FRONTEND_PID=$(get_port_pid $FRONTEND_PORT)
        if [ -n "$FRONTEND_PID" ]; then
            echo -e "${GREEN}✅ Running (PID: $FRONTEND_PID)${NC}"
        else
            echo -e "${RED}❌ Not running${NC}"
        fi
        
        # Test endpoints
        echo -e "\n${BLUE}Endpoint health:${NC}"
        echo -n "  Backend API: "
        if curl -s http://$EXTERNAL_IP:$BACKEND_PORT/docs > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Responding${NC}"
        else
            echo -e "${RED}❌ Not responding${NC}"
        fi
        
        echo -n "  Frontend: "
        if curl -s http://$EXTERNAL_IP:$FRONTEND_PORT | grep -q "<title>"; then
            echo -e "${GREEN}✅ Responding${NC}"
        else
            echo -e "${RED}❌ Not responding${NC}"
        fi
        ;;
        
    logs)
        case "$2" in
            backend|be)
                echo -e "${YELLOW}Backend logs (press Ctrl+C to exit):${NC}"
                tail -f $BACKEND_LOG
                ;;
            frontend|fe)
                echo -e "${YELLOW}Frontend logs (press Ctrl+C to exit):${NC}"
                tail -f $FRONTEND_LOG
                ;;
            both|"")
                echo -e "${YELLOW}Both logs (press Ctrl+C to exit):${NC}"
                tail -f $BACKEND_LOG $FRONTEND_LOG
                ;;
            *)
                echo "Usage: $0 logs [backend|frontend|both]"
                ;;
        esac
        ;;
        
    reload-check)
        echo -e "${YELLOW}Checking auto-reload status...${NC}"
        if check_backend_reload; then
            echo -e "${GREEN}✅ Backend has auto-reload enabled${NC}"
            echo "  File changes will automatically restart the backend"
        else
            echo -e "${YELLOW}⚠️  Backend does not have auto-reload enabled${NC}"
            echo "  Run '$0 restart backend' to enable auto-reload"
        fi
        ;;
        
    *)
        echo -e "${BLUE}Improved Development Services Manager${NC}"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs|reload-check}"
        echo ""
        echo "Commands:"
        echo "  start            - Start services (smart - won't restart if already running correctly)"
        echo "  stop             - Stop services by port (precise targeting)"
        echo "  restart          - Restart all services"
        echo "  restart backend  - Restart only backend with auto-reload"
        echo "  restart frontend - Restart only frontend"
        echo "  status           - Check service health and auto-reload status"
        echo "  logs             - Show logs (backend|frontend|both)"
        echo "  reload-check     - Check if backend has auto-reload enabled"
        echo ""
        echo "Key Improvements:"
        echo "  ✓ Uses correct port 8000 for backend"
        echo "  ✓ Kills processes by port, not by name (precise)"
        echo "  ✓ Checks if backend has --reload flag"
        echo "  ✓ Won't restart services unnecessarily"
        echo "  ✓ Shows external IP for remote access"
        echo "  ✓ Can restart individual services"
        echo ""
        echo "Examples:"
        echo "  $0 start               # Smart start - only starts what's needed"
        echo "  $0 restart backend     # Restart just the backend"
        echo "  $0 logs be             # Show backend logs"
        echo "  $0 reload-check        # Verify auto-reload is enabled"
        ;;
esac