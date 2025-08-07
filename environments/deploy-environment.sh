#!/bin/bash
# Centralized Environment Deployment Script
# Deploys environment configurations to all components

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
HISTORY_DIR="$SCRIPT_DIR/history"
MAX_BACKUPS=10

# Component paths (relative to project root)
BACKEND_PATH="backend"
FRONTEND_PATH="frontend" 
GPU_PATH="gpu_processing"

# Function to show usage
show_usage() {
    echo -e "${BLUE}Centralized Environment Deployment${NC}"
    echo ""
    echo "Usage: $0 <environment> [options]"
    echo ""
    echo "Environments:"
    echo "  development    Deploy development configuration"
    echo "  production     Deploy production configuration"
    echo "  status         Show current environment status"
    echo ""
    echo "Options:"
    echo "  --dry-run      Show what would be deployed without making changes"
    echo "  --component    Deploy only specific component (backend|frontend|gpu)"
    echo ""
    echo "Examples:"
    echo "  $0 production                    # Deploy full production environment"
    echo "  $0 development --dry-run         # Preview development deployment"
    echo "  $0 production --component backend # Deploy only backend production config"
}

# Function to validate environment
validate_environment() {
    local env=$1
    local env_files=(
        ".env.backend.$env"
        ".env.frontend.$env" 
        ".env.gpu.$env"
    )
    
    echo -e "${YELLOW}🔍 Validating environment: $env${NC}"
    
    for file in "${env_files[@]}"; do
        if [[ ! -f "$SCRIPT_DIR/$file" ]]; then
            echo -e "${RED}❌ Missing: $file${NC}"
            return 1
        else
            echo -e "${GREEN}✅ Found: $file${NC}"
        fi
    done
    
    return 0
}

# Function to cleanup old backups
cleanup_old_backups() {
    local component=$1
    local backup_pattern="$HISTORY_DIR/$component.env.backup.*"
    
    # Count existing backups
    local backup_count=$(ls -1 $backup_pattern 2>/dev/null | wc -l)
    
    if [[ $backup_count -gt $MAX_BACKUPS ]]; then
        # Remove oldest backups, keep only MAX_BACKUPS
        ls -1t $backup_pattern 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | xargs rm -f
        echo -e "${YELLOW}  🧹 Cleaned up old backups (kept last $MAX_BACKUPS)${NC}"
    fi
}

# Function to deploy component configuration
deploy_component() {
    local component=$1
    local environment=$2
    local dry_run=$3
    
    local source_file="$SCRIPT_DIR/.env.$component.$environment"
    local target_dir=""
    local target_file=""
    
    # Determine target paths
    case $component in
        "backend")
            target_dir="$PROJECT_ROOT/$BACKEND_PATH"
            target_file="$target_dir/.env"
            ;;
        "frontend")
            target_dir="$PROJECT_ROOT/$FRONTEND_PATH"
            target_file="$target_dir/.env.$environment"
            ;;
        "gpu")
            target_dir="$PROJECT_ROOT/$GPU_PATH"
            target_file="$target_dir/.env"
            ;;
        *)
            echo -e "${RED}❌ Unknown component: $component${NC}"
            return 1
            ;;
    esac
    
    # Check if source exists
    if [[ ! -f "$source_file" ]]; then
        echo -e "${RED}❌ Source file not found: $source_file${NC}"
        return 1
    fi
    
    # Check if target directory exists
    if [[ ! -d "$target_dir" ]]; then
        echo -e "${RED}❌ Target directory not found: $target_dir${NC}"
        return 1
    fi
    
    echo -e "${BLUE}📋 $component ($environment):${NC}"
    echo -e "  Source: $source_file"
    echo -e "  Target: $target_file"
    
    if [[ "$dry_run" == "true" ]]; then
        echo -e "${YELLOW}  Status: DRY RUN - would copy${NC}"
        return 0
    fi
    
    # Backup existing file if it exists
    if [[ -f "$target_file" ]]; then
        # Create history directory if it doesn't exist
        mkdir -p "$HISTORY_DIR"
        
        # Create backup in centralized history location
        local backup_file="$HISTORY_DIR/$component.env.backup.$(date +%Y%m%d_%H%M%S)"
        cp "$target_file" "$backup_file"
        echo -e "${YELLOW}  📁 Backup: $backup_file${NC}"
        
        # Cleanup old backups
        cleanup_old_backups "$component"
    fi
    
    # Copy new configuration
    cp "$source_file" "$target_file"
    echo -e "${GREEN}  Status: ✅ Deployed${NC}"
    
    return 0
}

# Function to restart services after deployment
restart_services() {
    local environment=$1
    local component=$2
    
    echo -e "${BLUE}🔄 Restarting services after deployment...${NC}"
    
    case $component in
        "backend"|"")
            if systemctl is-enabled review-platform.service &>/dev/null; then
                echo -e "${YELLOW}  Restarting backend API service...${NC}"
                sudo systemctl restart review-platform.service || true
                echo -e "${GREEN}  ✅ Backend API service restarted${NC}"
            fi
            
            if systemctl is-enabled processing-worker.service &>/dev/null; then
                echo -e "${YELLOW}  Restarting processing worker service...${NC}"
                sudo systemctl restart processing-worker.service || true
                echo -e "${GREEN}  ✅ Processing worker service restarted${NC}"
            fi
            ;;
        "gpu")
            if systemctl is-enabled gpu-http-server.service &>/dev/null; then
                echo -e "${YELLOW}  Restarting GPU HTTP server service...${NC}"
                sudo systemctl restart gpu-http-server.service || true
                echo -e "${GREEN}  ✅ GPU HTTP server service restarted${NC}"
            fi
            ;;
    esac
    
    # Always show service status after restart
    echo ""
    echo -e "${BLUE}📊 Service Status:${NC}"
    if [[ "$component" == "backend" || -z "$component" ]]; then
        systemctl is-active --quiet review-platform && \
            echo -e "${GREEN}  ✅ Backend API: Active${NC}" || \
            echo -e "${RED}  ❌ Backend API: Inactive${NC}"
            
        systemctl is-active --quiet processing-worker && \
            echo -e "${GREEN}  ✅ Processing Worker: Active${NC}" || \
            echo -e "${RED}  ❌ Processing Worker: Inactive${NC}"
    fi
    
    if [[ "$component" == "gpu" ]]; then
        systemctl is-active --quiet gpu-http-server && \
            echo -e "${GREEN}  ✅ GPU HTTP Server: Active${NC}" || \
            echo -e "${RED}  ❌ GPU HTTP Server: Inactive${NC}"
    fi
}

# Function to show current status
show_status() {
    echo -e "${BLUE}📊 Current Environment Status${NC}"
    echo ""
    
    local components=("backend" "frontend" "gpu")
    local environments=("development" "production")
    
    for component in "${components[@]}"; do
        echo -e "${YELLOW}$component:${NC}"
        
        case $component in
            "backend")
                local config_file="$PROJECT_ROOT/$BACKEND_PATH/.env"
                ;;
            "frontend")
                local config_file="$PROJECT_ROOT/$FRONTEND_PATH/.env.development"
                local prod_config_file="$PROJECT_ROOT/$FRONTEND_PATH/.env.production"
                ;;
            "gpu")
                local config_file="$PROJECT_ROOT/$GPU_PATH/.env.development"
                local prod_config_file="$PROJECT_ROOT/$GPU_PATH/.env.production"
                ;;
        esac
        
        if [[ -f "$config_file" ]]; then
            local modified=$(stat -c %Y "$config_file" 2>/dev/null || stat -f %m "$config_file" 2>/dev/null)
            local modified_date=$(date -d @$modified 2>/dev/null || date -r $modified 2>/dev/null)
            echo -e "  ✅ Active: $config_file"
            echo -e "  📅 Modified: $modified_date"
        else
            echo -e "  ❌ Missing: $config_file"
        fi
        
        if [[ "$component" != "backend" && -f "$prod_config_file" ]]; then
            local prod_modified=$(stat -c %Y "$prod_config_file" 2>/dev/null || stat -f %m "$prod_config_file" 2>/dev/null)
            local prod_modified_date=$(date -d @$prod_modified 2>/dev/null || date -r $prod_modified 2>/dev/null)
            echo -e "  ✅ Production: $prod_config_file"
            echo -e "  📅 Modified: $prod_modified_date"
        fi
        echo ""
    done
}

# Main function
main() {
    local environment=""
    local dry_run="false"
    local specific_component=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            development|production|status)
                environment="$1"
                shift
                ;;
            --dry-run)
                dry_run="true"
                shift
                ;;
            --component)
                specific_component="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Unknown argument: $1${NC}"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Handle status
    if [[ "$environment" == "status" ]]; then
        show_status
        exit 0
    fi
    
    # Validate environment argument
    if [[ -z "$environment" ]]; then
        echo -e "${RED}❌ Environment argument required${NC}"
        show_usage
        exit 1
    fi
    
    if [[ "$environment" != "development" && "$environment" != "production" ]]; then
        echo -e "${RED}❌ Invalid environment: $environment${NC}"
        show_usage
        exit 1
    fi
    
    # Validate environment files exist
    if ! validate_environment "$environment"; then
        echo -e "${RED}❌ Environment validation failed${NC}"
        exit 1
    fi
    
    echo ""
    echo -e "${GREEN}🚀 Deploying $environment environment${NC}"
    if [[ "$dry_run" == "true" ]]; then
        echo -e "${YELLOW}⚠️  DRY RUN MODE - No files will be modified${NC}"
    fi
    echo ""
    
    # Deploy components
    local components=("backend" "frontend" "gpu")
    if [[ -n "$specific_component" ]]; then
        components=("$specific_component")
    fi
    
    local success=true
    for component in "${components[@]}"; do
        if ! deploy_component "$component" "$environment" "$dry_run"; then
            success=false
        fi
    done
    
    echo ""
    if [[ "$success" == "true" ]]; then
        if [[ "$dry_run" == "false" ]]; then
            echo -e "${GREEN}✅ Environment deployment completed successfully!${NC}"
            
            # Restart services automatically
            restart_services "$environment" "$specific_component"
            
            echo ""
            echo -e "${YELLOW}📋 Additional steps (if needed):${NC}"
            echo -e "  1. Rebuild frontend: scripts/build-frontend.sh $environment"
            echo -e "  2. Check logs: journalctl -u review-platform.service -f"
            echo -e "  3. Check worker logs: journalctl -u processing-worker.service -f"
        else
            echo -e "${BLUE}✅ Dry run completed - deployment looks good!${NC}"
        fi
    else
        echo -e "${RED}❌ Environment deployment failed${NC}"
        exit 1
    fi
}

# Run main function
main "$@"