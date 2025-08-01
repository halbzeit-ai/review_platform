#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

case "$1" in
    start)
        echo -e "${YELLOW}Starting frontend only (backend already running on port 8000)...${NC}"
        
        # Stop existing frontend processes only
        echo -e "${BLUE}Stopping existing frontend processes...${NC}"
        pkill -f "react-scripts" || true
        lsof -ti:3000 | xargs kill -9 2>/dev/null || true
        sleep 2
        
        # Start frontend
        echo -e "${BLUE}Starting frontend...${NC}"
        cd /opt/review-platform-dev/frontend
        DANGEROUSLY_DISABLE_HOST_CHECK=true npm start > frontend.log 2>&1 &
        FRONTEND_PID=$!
        
        echo -e "${GREEN}✅ Frontend started (PID: $FRONTEND_PID) - http://65.108.32.143:3000${NC}"
        echo -e "${BLUE}Backend already running on port 8000${NC}"
        echo -e "${YELLOW}Waiting 5 seconds for frontend to initialize...${NC}"
        sleep 5
        ;;
    stop)
        echo -e "${YELLOW}Stopping frontend only...${NC}"
        pkill -f "react-scripts" && echo -e "${GREEN}✅ Frontend stopped${NC}" || echo -e "${RED}❌ Frontend not running${NC}"
        lsof -ti:3000 | xargs kill -9 2>/dev/null || true
        ;;
    status)
        echo -e "${YELLOW}Checking service status...${NC}"
        echo -n "Backend (port 8000): "
        if curl -s http://65.108.32.143:8000/docs > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Running${NC}"
        else
            echo -e "${RED}❌ Not running${NC}"
        fi
        
        echo -n "Frontend (port 3000): "
        if curl -s http://65.108.32.143:3000 > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Running${NC}"
        else
            echo -e "${RED}❌ Not running${NC}"
        fi
        
        # Show process info
        echo -e "${BLUE}Active processes:${NC}"
        ps aux | grep -E "(uvicorn|react-scripts)" | grep -v grep || echo "No development processes found"
        ;;
    clean)
        echo -e "${YELLOW}Cleaning up duplicate backend processes...${NC}"
        # Kill the duplicate backend on port 5001 (but keep port 8000)
        lsof -ti:5001 | xargs kill -9 2>/dev/null && echo -e "${GREEN}✅ Duplicate backend on port 5001 stopped${NC}" || echo -e "${BLUE}No duplicate backend found${NC}"
        ;;
    *)
        echo -e "${BLUE}Frontend-Only Development Manager${NC}"
        echo ""
        echo "Usage: $0 {start|stop|status|clean}"
        echo ""
        echo "Commands:"
        echo "  start      - Start frontend only (assumes backend on port 8000)"
        echo "  stop       - Stop frontend only"
        echo "  status     - Check service health"
        echo "  clean      - Remove duplicate backend processes"
        echo ""
        echo "Note: This script assumes the main backend is already running on port 8000"
        ;;
esac