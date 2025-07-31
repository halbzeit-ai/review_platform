#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

case "$1" in
    start)
        echo -e "${YELLOW}Starting development services...${NC}"
        
        # Stop existing processes
        echo -e "${BLUE}Stopping existing processes...${NC}"
        pkill -f uvicorn || true
        pkill -f "react-scripts" || true
        lsof -ti:5001 | xargs kill -9 2>/dev/null || true
        lsof -ti:3000 | xargs kill -9 2>/dev/null || true
        sleep 2
        
        # Start backend
        echo -e "${BLUE}Starting backend...${NC}"
        cd /opt/review-platform-dev/backend
        uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload > backend.log 2>&1 &
        BACKEND_PID=$!
        
        # Start frontend
        echo -e "${BLUE}Starting frontend...${NC}"
        cd /opt/review-platform-dev/frontend
        DANGEROUSLY_DISABLE_HOST_CHECK=true npm start > frontend.log 2>&1 &
        FRONTEND_PID=$!
        
        echo -e "${GREEN}✅ Backend started (PID: $BACKEND_PID) - http://localhost:5001${NC}"
        echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID) - http://localhost:3000${NC}"
        echo -e "${YELLOW}Waiting 5 seconds for services to initialize...${NC}"
        sleep 5
        ;;
    stop)
        echo -e "${YELLOW}Stopping development services...${NC}"
        pkill -f uvicorn && echo -e "${GREEN}✅ Backend stopped${NC}" || echo -e "${RED}❌ Backend not running${NC}"
        pkill -f "react-scripts" && echo -e "${GREEN}✅ Frontend stopped${NC}" || echo -e "${RED}❌ Frontend not running${NC}"
        lsof -ti:5001 | xargs kill -9 2>/dev/null || true
        lsof -ti:3000 | xargs kill -9 2>/dev/null || true
        ;;
    restart)
        echo -e "${YELLOW}Restarting development services...${NC}"
        $0 stop
        sleep 2
        $0 start
        ;;
    status)
        echo -e "${YELLOW}Checking service status...${NC}"
        echo -n "Backend (port 5001): "
        if curl -s http://localhost:5001/docs > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Running${NC}"
        else
            echo -e "${RED}❌ Not running${NC}"
        fi
        
        echo -n "Frontend (port 3000): "
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Running${NC}"
        else
            echo -e "${RED}❌ Not running${NC}"
        fi
        
        # Show process info
        echo -e "${BLUE}Active processes:${NC}"
        ps aux | grep -E "(uvicorn|react-scripts)" | grep -v grep || echo "No development processes found"
        ;;
    logs)
        case "$2" in
            backend|be)
                echo -e "${YELLOW}Backend logs (press Ctrl+C to exit):${NC}"
                tail -f /opt/review-platform-dev/backend/backend.log
                ;;
            frontend|fe)
                echo -e "${YELLOW}Frontend logs (press Ctrl+C to exit):${NC}"
                tail -f /opt/review-platform-dev/frontend/frontend.log
                ;;
            both|"")
                echo -e "${YELLOW}Both logs (press Ctrl+C to exit):${NC}"
                tail -f /opt/review-platform-dev/backend/backend.log /opt/review-platform-dev/frontend/frontend.log
                ;;
            *)
                echo "Usage: $0 logs [backend|frontend|both]"
                ;;
        esac
        ;;
    *)
        echo -e "${BLUE}Development Services Manager${NC}"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Commands:"
        echo "  start      - Start both frontend and backend services"
        echo "  stop       - Stop both services"
        echo "  restart    - Restart both services"
        echo "  status     - Check service health and show process info"
        echo "  logs       - Show logs (backend|frontend|both)"
        echo ""
        echo "Examples:"
        echo "  $0 start           # Start all services"
        echo "  $0 logs backend    # Show backend logs"
        echo "  $0 logs fe         # Show frontend logs (short form)"
        ;;
esac