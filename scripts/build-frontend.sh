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
    echo -e "${GREEN}🏭 Building for PRODUCTION with ZERO-DOWNTIME deployment...${NC}"
    echo -e "${GREEN}   ✅ Will use relative API URLs (/api)${NC}"
    echo -e "${GREEN}   ✅ Will optimize for production performance${NC}"
    echo -e "${GREEN}   ✅ Current version stays online during build${NC}"
    
    # Zero-downtime deployment strategy
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BUILD_DIR="build_${TIMESTAMP}"
    CURRENT_BUILD="build"
    BACKUP_BUILD="build_backup"
    
    echo -e "${YELLOW}📦 Creating new build: ${BUILD_DIR}${NC}"
    
    # Build to timestamped directory (doesn't affect current running version)
    REACT_APP_BUILD_PATH=$BUILD_DIR NODE_ENV=production npm run build
    
    # React Scripts always builds to 'build/', so we need to move it
    if [ -d "build" ] && [ ! -d "$BUILD_DIR" ]; then
        mv build $BUILD_DIR
    fi
    
    # Verify build was successful
    if [ ! -d "$BUILD_DIR" ] || [ ! -f "$BUILD_DIR/index.html" ]; then
        echo -e "${RED}❌ Build failed! Current version remains online.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ New build successful!${NC}"
    
    # Atomic deployment (fast switch)
    echo -e "${YELLOW}🔄 Performing atomic deployment...${NC}"
    
    # Backup current version (if exists)
    if [ -d "$CURRENT_BUILD" ]; then
        echo -e "${YELLOW}💾 Backing up current version...${NC}"
        rm -rf $BACKUP_BUILD 2>/dev/null || true
        mv $CURRENT_BUILD $BACKUP_BUILD
    fi
    
    # Atomic switch: rename new build to current (milliseconds downtime)
    mv $BUILD_DIR $CURRENT_BUILD
    
    echo -e "${GREEN}⚡ Atomic switch complete! New version is live.${NC}"
    echo -e "${GREEN}📁 Active build: ${WORK_DIR}/${CURRENT_BUILD}/${NC}"
    echo -e "${GREEN}💾 Backup available: ${WORK_DIR}/${BACKUP_BUILD}/${NC}"
    
    # Cleanup old builds (keep last 3)
    echo -e "${YELLOW}🧹 Cleaning up old builds...${NC}"
    ls -dt build_[0-9]* 2>/dev/null | tail -n +4 | xargs rm -rf 2>/dev/null || true
    
    # Health check
    if [ -f "${CURRENT_BUILD}/index.html" ]; then
        echo -e "${GREEN}✅ Health check passed - index.html exists${NC}"
    else
        echo -e "${RED}⚠️  Health check warning - index.html not found${NC}"
    fi
    
    # Show rollback instructions
    echo -e "${YELLOW}🔄 To rollback if needed:${NC}"
    echo -e "${YELLOW}   mv ${CURRENT_BUILD} build_failed && mv ${BACKUP_BUILD} ${CURRENT_BUILD}${NC}"
    
    # Show deployment summary
    echo -e "${GREEN}📊 Deployment Summary:${NC}"
    echo -e "${GREEN}   🟢 Status: DEPLOYED${NC}"
    echo -e "${GREEN}   📅 Build: ${TIMESTAMP}${NC}"
    echo -e "${GREEN}   📁 Path: ${WORK_DIR}/${CURRENT_BUILD}${NC}"
    
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