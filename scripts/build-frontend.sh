#!/bin/bash
# Fixed Environment-aware frontend build script
# Builds frontend for the correct environment automatically with proper zero-downtime deployment

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
FRONTEND_DIR="/opt/review-platform/frontend"
DEV_FRONTEND_DIR="/opt/review-platform-dev/frontend"
NGINX_SERVE_DIR="/var/www/html"

echo -e "${GREEN}🏗️  Fixed Environment-Aware Frontend Build${NC}"

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
    
    # Zero-downtime deployment strategy - FIXED VERSION
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    NEW_BUILD_DIR="build_${TIMESTAMP}"
    ACTIVE_LINK="build"
    BACKUP_DIR="build_backup"
    
    echo -e "${YELLOW}📦 Creating new build: ${NEW_BUILD_DIR}${NC}"
    
    # Clean up any existing 'build' directory that's not a symlink
    if [ -d "$ACTIVE_LINK" ] && [ ! -L "$ACTIVE_LINK" ]; then
        echo -e "${YELLOW}🔄 Converting existing build directory to symlink-based deployment...${NC}"
        if [ -d "$BACKUP_DIR" ]; then
            rm -rf "$BACKUP_DIR"
        fi
        mv "$ACTIVE_LINK" "$BACKUP_DIR"
        ln -sfn "$BACKUP_DIR" "$ACTIVE_LINK"
    fi
    
    # Build to temporary directory first (React always uses 'build')
    TEMP_BUILD="build_temp_${TIMESTAMP}"
    
    # React Scripts builds to 'build' directory, we need to work around this
    if [ -L "$ACTIVE_LINK" ]; then
        # Temporarily rename the symlink to avoid conflicts
        mv "$ACTIVE_LINK" "${ACTIVE_LINK}_temp"
    fi
    
    # Generate build information
    BUILD_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    BUILD_DESCRIPTION="AUTO_GENERATED"
    
    # Build (React creates 'build' directory) with build info
    REACT_APP_BUILD_TIMESTAMP="$BUILD_TIMESTAMP" \
    REACT_APP_BUILD_VERSION="production" \
    REACT_APP_GIT_COMMIT="$GIT_COMMIT" \
    REACT_APP_BUILD_DESCRIPTION="$BUILD_DESCRIPTION" \
    NODE_ENV=production npm run build
    
    # Move the new build to timestamped directory
    mv build "$NEW_BUILD_DIR"
    
    # Restore the active symlink
    if [ -L "${ACTIVE_LINK}_temp" ]; then
        mv "${ACTIVE_LINK}_temp" "$ACTIVE_LINK"
    fi
    
    # Verify build was successful
    if [ ! -d "$NEW_BUILD_DIR" ] || [ ! -f "$NEW_BUILD_DIR/index.html" ]; then
        echo -e "${RED}❌ Build failed! Current version remains online.${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ New build successful!${NC}"
    
    # Deploy to nginx directory with zero downtime
    echo -e "${YELLOW}🔄 Deploying to nginx directory with zero downtime...${NC}"
    
    # Copy new build to nginx directory
    echo -e "${YELLOW}📋 Copying build to nginx directory...${NC}"
    sudo cp -r "$NEW_BUILD_DIR" "${NGINX_SERVE_DIR}/build_${TIMESTAMP}"
    
    # Backup current nginx version properly
    if [ -L "${NGINX_SERVE_DIR}/build" ]; then
        CURRENT_TARGET=$(readlink "${NGINX_SERVE_DIR}/build")
        CURRENT_DIR=$(basename "$CURRENT_TARGET")
        if [ -d "$CURRENT_TARGET" ] && [ "$CURRENT_DIR" != "build_backup" ]; then
            echo -e "${YELLOW}💾 Creating backup of current nginx version...${NC}"
            if [ -d "${NGINX_SERVE_DIR}/build_backup" ]; then
                sudo rm -rf "${NGINX_SERVE_DIR}/build_backup"
            fi
            sudo cp -r "$CURRENT_TARGET" "${NGINX_SERVE_DIR}/build_backup"
        fi
    fi
    
    # Atomic switch: update nginx symlink (zero downtime)
    echo -e "${GREEN}⚡ Atomic nginx symlink switch...${NC}"
    sudo ln -sfn "${NGINX_SERVE_DIR}/build_${TIMESTAMP}" "${NGINX_SERVE_DIR}/build"
    
    # Also update local symlink for consistency
    ln -sfn "$NEW_BUILD_DIR" "$ACTIVE_LINK"
    
    echo -e "${GREEN}⚡ Atomic switch complete! New version is live.${NC}"
    echo -e "${GREEN}📁 Local build: ${WORK_DIR}/${ACTIVE_LINK} -> ${NEW_BUILD_DIR}${NC}"
    echo -e "${GREEN}🌐 Nginx build: ${NGINX_SERVE_DIR}/build -> build_${TIMESTAMP}${NC}"
    echo -e "${GREEN}💾 Backup available: ${NGINX_SERVE_DIR}/build_backup${NC}"
    
    # Cleanup old builds (keep last 3, but not backup or active)
    echo -e "${YELLOW}🧹 Cleaning up old builds...${NC}"
    find . -maxdepth 1 -name "build_[0-9]*" -type d | \
        grep -v "$NEW_BUILD_DIR" | \
        sort -r | \
        tail -n +4 | \
        xargs rm -rf 2>/dev/null || true
    
    # Comprehensive deployment verification
    echo -e "${YELLOW}🔍 Verifying deployment...${NC}"
    
    # Check local build
    if [ -f "${ACTIVE_LINK}/index.html" ]; then
        echo -e "${GREEN}✅ Local build - index.html exists${NC}"
    else
        echo -e "${RED}❌ Local build - index.html missing${NC}"
    fi
    
    # Check nginx build
    if [ -f "${NGINX_SERVE_DIR}/build/index.html" ]; then
        echo -e "${GREEN}✅ Nginx build - index.html exists${NC}"
    else
        echo -e "${RED}❌ Nginx build - index.html missing${NC}"
    fi
    
    # Extract main JS filename from index.html
    MAIN_JS_FILE=$(grep -o "static/js/main\.[a-f0-9]*\.js" "${NGINX_SERVE_DIR}/build/index.html" | head -1)
    if [ -n "$MAIN_JS_FILE" ]; then
        echo -e "${GREEN}✅ Main JS file identified: ${MAIN_JS_FILE}${NC}"
        
        # Test if main JS file is accessible via nginx
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost/${MAIN_JS_FILE}")
        if [ "$HTTP_CODE" = "200" ]; then
            echo -e "${GREEN}✅ Main JS file accessible via nginx (HTTP ${HTTP_CODE})${NC}"
        else
            echo -e "${RED}❌ Main JS file NOT accessible via nginx (HTTP ${HTTP_CODE})${NC}"
        fi
        
        # Test if index.html is accessible via nginx
        INDEX_HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost/")
        if [ "$INDEX_HTTP_CODE" = "200" ]; then
            echo -e "${GREEN}✅ Frontend accessible via nginx (HTTP ${INDEX_HTTP_CODE})${NC}"
        else
            echo -e "${RED}❌ Frontend NOT accessible via nginx (HTTP ${INDEX_HTTP_CODE})${NC}"
        fi
        
        # Check if the deployed version matches what we built
        DEPLOYED_JS=$(curl -s http://localhost/ | grep -o "static/js/main\.[a-f0-9]*\.js" | head -1)
        if [ "$DEPLOYED_JS" = "$MAIN_JS_FILE" ]; then
            echo -e "${GREEN}✅ Deployed version matches build${NC}"
        else
            echo -e "${RED}❌ Version mismatch - deployed: ${DEPLOYED_JS}, built: ${MAIN_JS_FILE}${NC}"
        fi
    else
        echo -e "${RED}❌ Could not identify main JS file in index.html${NC}"
    fi
    
    # Summary of verification
    echo -e "${CYAN}📋 Deployment Verification Summary:${NC}"
    echo -e "${GREEN}   Build timestamp: ${TIMESTAMP}${NC}"
    echo -e "${GREEN}   Main JS file: ${MAIN_JS_FILE}${NC}"
    echo -e "${GREEN}   Nginx serving from: ${NGINX_SERVE_DIR}/build${NC}"
    
    # Show rollback instructions
    echo -e "${YELLOW}🔄 To rollback if needed:${NC}"
    echo -e "${YELLOW}   sudo ln -sfn ${NGINX_SERVE_DIR}/build_backup ${NGINX_SERVE_DIR}/build${NC}"
    echo -e "${YELLOW}   ln -sfn ${BACKUP_DIR} ${ACTIVE_LINK}${NC}"
    
    # Show deployment summary
    echo -e "${GREEN}📊 Deployment Summary:${NC}"
    echo -e "${GREEN}   🟢 Status: DEPLOYED${NC}"
    echo -e "${GREEN}   📅 Build: ${TIMESTAMP}${NC}"
    echo -e "${GREEN}   📁 Path: ${WORK_DIR}/${ACTIVE_LINK}${NC}"
    echo -e "${GREEN}   🎯 Target: ${NEW_BUILD_DIR}${NC}"
    
else
    echo -e "${YELLOW}🔧 Building for DEVELOPMENT...${NC}"
    echo -e "${YELLOW}   ✅ Will use development backend (65.108.32.143:8000)${NC}"
    echo -e "${YELLOW}   ✅ Will include debug information${NC}"
    
    # Generate build information for development
    BUILD_TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
    BUILD_DESCRIPTION="DEVELOPMENT"
    
    # Development build (for testing)
    REACT_APP_BUILD_TIMESTAMP="$BUILD_TIMESTAMP" \
    REACT_APP_BUILD_VERSION="development" \
    REACT_APP_GIT_COMMIT="$GIT_COMMIT" \
    REACT_APP_BUILD_DESCRIPTION="$BUILD_DESCRIPTION" \
    NODE_ENV=development npm run build
    
    echo -e "${GREEN}✅ Development build complete!${NC}"
    echo -e "${GREEN}📁 Built files in: ${WORK_DIR}/build/${NC}"
fi

# Show build size
BUILD_TARGET=$ACTIVE_LINK
if [ ! -L "$BUILD_TARGET" ] && [ -d "$BUILD_TARGET" ]; then
    BUILD_SIZE=$(du -sh "$BUILD_TARGET" | cut -f1)
    echo -e "${GREEN}📊 Build size: ${BUILD_SIZE}${NC}"
elif [ -L "$BUILD_TARGET" ]; then
    TARGET_DIR=$(readlink "$BUILD_TARGET")
    if [ -d "$TARGET_DIR" ]; then
        BUILD_SIZE=$(du -sh "$TARGET_DIR" | cut -f1)
        echo -e "${GREEN}📊 Build size: ${BUILD_SIZE}${NC}"
    fi
fi

echo -e "${GREEN}🎉 Frontend build complete for ${ENVIRONMENT}!${NC}"