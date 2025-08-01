#!/bin/bash
# Environment-aware frontend build script
# Builds frontend for the correct environment automatically

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_DIR="/opt/review-platform/frontend"
DEV_FRONTEND_DIR="/opt/review-platform-dev/frontend"

echo -e "${GREEN}🏗️  Environment-Aware Frontend Build${NC}"

# Detect environment
if [[ $PWD == *"review-platform-dev"* ]]; then
    ENVIRONMENT="development"
    WORK_DIR=$DEV_FRONTEND_DIR
elif [[ $PWD == *"review-platform"* ]] && [[ $PWD != *"review-platform-dev"* ]]; then
    ENVIRONMENT="production"
    WORK_DIR=$FRONTEND_DIR
else
    echo -e "${YELLOW}⚠️  Could not detect environment from path. Please specify:${NC}"
    echo "Usage: $0 [development|production]"
    ENVIRONMENT=${1:-development}
    WORK_DIR=${ENVIRONMENT/production/$FRONTEND_DIR}
    WORK_DIR=${WORK_DIR/development/$DEV_FRONTEND_DIR}
fi

echo -e "${GREEN}📍 Environment: ${ENVIRONMENT}${NC}"
echo -e "${GREEN}📁 Working directory: ${WORK_DIR}${NC}"

# Navigate to frontend directory
cd $WORK_DIR

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing dependencies...${NC}"
    npm install
fi

# Build based on environment
if [ "$ENVIRONMENT" = "production" ]; then
    echo -e "${GREEN}🏭 Building for PRODUCTION...${NC}"
    echo -e "${GREEN}   ✅ Will use relative API URLs (/api)${NC}"
    echo -e "${GREEN}   ✅ Will optimize for production performance${NC}"
    
    # Production build
    NODE_ENV=production npm run build
    
    echo -e "${GREEN}✅ Production build complete!${NC}"
    echo -e "${GREEN}📁 Built files in: ${WORK_DIR}/build/${NC}"
    echo -e "${GREEN}🚀 Deploy these files to your web server${NC}"
    
else
    echo -e "${YELLOW}🔧 Building for DEVELOPMENT...${NC}"
    echo -e "${YELLOW}   ✅ Will use development backend (65.108.32.143:8000)${NC}"
    echo -e "${YELLOW}   ✅ Will include debug information${NC}"
    
    # Development build (for testing)
    NODE_ENV=development npm run build
    
    echo -e "${GREEN}✅ Development build complete!${NC}"
    echo -e "${GREEN}📁 Built files in: ${WORK_DIR}/build/${NC}"
fi

# Show build size
if [ -d "build" ]; then
    BUILD_SIZE=$(du -sh build/ | cut -f1)
    echo -e "${GREEN}📊 Build size: ${BUILD_SIZE}${NC}"
fi

echo -e "${GREEN}🎉 Frontend build complete for ${ENVIRONMENT}!${NC}"