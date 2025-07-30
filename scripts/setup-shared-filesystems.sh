#!/bin/bash

# Setup Shared NFS Filesystems for Development Environment
# This script configures shared filesystem access between:
# - Development CPU (65.108.32.143) and Development GPU (135.181.71.17)
# - Read-only access to production filesystem for file transfers

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Server configuration
DEVELOPMENT_CPU="65.108.32.143"
DEVELOPMENT_GPU="135.181.71.17"
PRODUCTION_CPU="65.108.32.168"

# Filesystem configuration based on CLAUDE.md and DATACRUNCH_SETUP.md
DEV_SHARED_MOUNT="/mnt/dev-CPU-GPU"
PROD_SHARED_MOUNT="/mnt/shared-production"

# Parse arguments
DRY_RUN=false
MOUNT_PRODUCTION=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --no-production-mount)
            MOUNT_PRODUCTION=false
            shift
            ;;
        --help|-h)
            cat << 'EOF'
Setup Shared NFS Filesystems for Development Environment

This script configures shared filesystem access between development CPU and GPU servers,
and optionally mounts production filesystem for file transfers.

Usage: ./setup-shared-filesystems.sh [options]

Options:
  --dry-run                Show what would be done without executing
  --no-production-mount    Skip mounting production filesystem
  --help, -h              Show this help message

Filesystems configured:
  /mnt/dev-CPU-GPU        - Shared between development CPU and GPU
  /mnt/shared-production  - Read-only access to production files (optional)

Directory structure created:
  {mount}/uploads/        - PDF upload directory
  {mount}/results/        - AI processing results
  {mount}/cache/          - Temporary processing cache
  {mount}/logs/           - Processing logs

EOF
            exit 0
            ;;
        *)
            log_error "Unknown argument: $1"
            exit 1
            ;;
    esac
done

echo "📁 Setting up Shared NFS Filesystems"
echo "===================================="
echo "Development CPU: $DEVELOPMENT_CPU"
echo "Development GPU: $DEVELOPMENT_GPU"
echo ""

if [ "$DRY_RUN" = true ]; then
    log_warning "DRY RUN MODE - No changes will be made"
    echo ""
fi

# Function to run command on remote server
run_remote() {
    local server="$1"
    local cmd="$2"
    local description="$3"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would run on $server: $cmd"
        [ -n "$description" ] && echo "   Purpose: $description"
    else
        log_info "Running on $server: $description"
        ssh -o StrictHostKeyChecking=no root@"$server" "$cmd"
    fi
}

# Step 1: Install NFS utilities on both servers
install_nfs_utilities() {
    log_info "Step 1: Installing NFS utilities..."
    
    local install_cmd="apt update && apt install -y nfs-kernel-server nfs-common"
    
    run_remote "$DEVELOPMENT_CPU" "$install_cmd" "Install NFS utilities on development CPU"
    run_remote "$DEVELOPMENT_GPU" "$install_cmd" "Install NFS utilities on development GPU"
    
    log_success "NFS utilities installed on both servers"
}

# Step 2: Setup NFS server on development CPU
setup_nfs_server() {
    log_info "Step 2: Setting up NFS server on development CPU..."
    
    # Create shared directory structure
    local create_dirs_cmd="
        mkdir -p $DEV_SHARED_MOUNT/{uploads,results,cache,logs} &&
        chown -R nobody:nogroup $DEV_SHARED_MOUNT &&
        chmod -R 755 $DEV_SHARED_MOUNT
    "
    run_remote "$DEVELOPMENT_CPU" "$create_dirs_cmd" "Create shared directory structure"
    
    # Configure NFS exports
    local exports_config="$DEV_SHARED_MOUNT $DEVELOPMENT_GPU(rw,sync,no_subtree_check,no_root_squash)"
    local setup_exports_cmd="
        echo '$exports_config' >> /etc/exports &&
        exportfs -ra &&
        systemctl restart nfs-kernel-server &&
        systemctl enable nfs-kernel-server
    "
    run_remote "$DEVELOPMENT_CPU" "$setup_exports_cmd" "Configure NFS exports"
    
    log_success "NFS server configured on development CPU"
}

# Step 3: Mount NFS share on development GPU
mount_nfs_client() {
    log_info "Step 3: Mounting NFS share on development GPU..."
    
    # Create mount point and mount NFS share
    local mount_cmd="
        mkdir -p $DEV_SHARED_MOUNT &&
        mount -t nfs $DEVELOPMENT_CPU:$DEV_SHARED_MOUNT $DEV_SHARED_MOUNT &&
        echo '$DEVELOPMENT_CPU:$DEV_SHARED_MOUNT $DEV_SHARED_MOUNT nfs defaults 0 0' >> /etc/fstab
    "
    run_remote "$DEVELOPMENT_GPU" "$mount_cmd" "Mount development shared filesystem"
    
    log_success "NFS share mounted on development GPU"
}

# Step 4: Setup production filesystem access (optional)
setup_production_access() {
    if [ "$MOUNT_PRODUCTION" = false ]; then
        log_info "Skipping production filesystem mount"
        return
    fi
    
    log_info "Step 4: Setting up production filesystem access..."
    
    # Mount production filesystem on development CPU (read-only)
    local prod_mount_cmd="
        mkdir -p $PROD_SHARED_MOUNT &&
        mount -t nfs -o ro $PRODUCTION_CPU:/mnt/CPU-GPU $PROD_SHARED_MOUNT &&
        echo '$PRODUCTION_CPU:/mnt/CPU-GPU $PROD_SHARED_MOUNT nfs ro,defaults 0 0' >> /etc/fstab
    "
    run_remote "$DEVELOPMENT_CPU" "$prod_mount_cmd" "Mount production filesystem (read-only)"
    
    log_success "Production filesystem access configured"
}

# Step 5: Test filesystem access
test_filesystem_access() {
    log_info "Step 5: Testing filesystem access..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would test filesystem read/write access"
        log_info "Would verify directory structure"
        log_info "Would test file synchronization between servers"
        return
    fi
    
    # Test file creation on CPU
    local test_file="$DEV_SHARED_MOUNT/test-$(date +%s).txt"
    local cpu_test_cmd="echo 'Test from CPU' > $test_file && ls -la $test_file"
    run_remote "$DEVELOPMENT_CPU" "$cpu_test_cmd" "Create test file on CPU"
    
    # Verify file appears on GPU
    local gpu_test_cmd="sleep 2 && cat $test_file && rm -f $test_file"
    run_remote "$DEVELOPMENT_GPU" "$gpu_test_cmd" "Verify file access on GPU"
    
    # Test directory structure
    local structure_test="ls -la $DEV_SHARED_MOUNT/"
    run_remote "$DEVELOPMENT_CPU" "$structure_test" "Verify directory structure on CPU"
    run_remote "$DEVELOPMENT_GPU" "$structure_test" "Verify directory structure on GPU"
    
    log_success "Filesystem access tests completed"
}

# Step 6: Create development configuration
create_development_config() {
    log_info "Step 6: Creating development configuration..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would create filesystem configuration files"
        return
    fi
    
    # Create filesystem configuration file
    cat > filesystem-config.json << EOF
{
    "development": {
        "shared_mount": "$DEV_SHARED_MOUNT",
        "uploads_path": "$DEV_SHARED_MOUNT/uploads",
        "results_path": "$DEV_SHARED_MOUNT/results",
        "cache_path": "$DEV_SHARED_MOUNT/cache",
        "logs_path": "$DEV_SHARED_MOUNT/logs"
    },
    "production_access": {
        "enabled": $MOUNT_PRODUCTION,
        "mount_path": "$PROD_SHARED_MOUNT",
        "access_mode": "read-only"
    },
    "servers": {
        "development_cpu": "$DEVELOPMENT_CPU",
        "development_gpu": "$DEVELOPMENT_GPU",
        "production_cpu": "$PRODUCTION_CPU"
    }
}
EOF
    
    log_success "Development configuration created: filesystem-config.json"
}

# Main execution
main() {
    log_info "Starting shared filesystem setup..."
    
    install_nfs_utilities
    setup_nfs_server
    mount_nfs_client
    setup_production_access
    test_filesystem_access
    create_development_config
    
    if [ "$DRY_RUN" = true ]; then
        log_info "DRY RUN COMPLETED - No changes were made"
    else
        log_success "🎉 Shared filesystem setup completed!"
        echo ""
        echo "📁 Filesystem Summary:"
        echo "====================="
        echo "✅ Development shared: $DEV_SHARED_MOUNT (CPU ↔ GPU)"
        if [ "$MOUNT_PRODUCTION" = true ]; then
            echo "✅ Production access: $PROD_SHARED_MOUNT (read-only)"
        fi
        echo ""
        echo "📂 Directory Structure:"
        echo "  $DEV_SHARED_MOUNT/uploads/  - PDF uploads"
        echo "  $DEV_SHARED_MOUNT/results/  - AI processing results"
        echo "  $DEV_SHARED_MOUNT/cache/    - Temporary cache"
        echo "  $DEV_SHARED_MOUNT/logs/     - Processing logs"
        echo ""
        echo "🔧 Next Steps:"
        echo "1. Configure development GPU server: ./scripts/setup-development-gpu.sh"
        echo "2. Test complete workflow: ./scripts/test-development-workflow.sh"
    fi
}

# Run main function
main