#!/bin/bash
# Setup script for GPU shared filesystem mounting

set -e  # Exit on any error

echo "🖥️  Setting up GPU Shared Filesystem"
echo "============================================================"

# Configuration for GPU environment
MOUNT_POINT="/mnt/dev-shared"
NFS_ENDPOINT="nfs.fin-01.datacrunch.io:/dev-cpu-gpu-sf-9d6799ad"
SERVICE_USER="root"  # For development

echo "📋 Configuration:"
echo "  Mount Point: $MOUNT_POINT"
echo "  NFS Endpoint: $NFS_ENDPOINT"
echo "  Service User: $SERVICE_USER"
echo "  Host Type: GPU Instance"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# Step 1: Create mount point
echo "📁 Step 1: Creating mount point..."
if [ ! -d "$MOUNT_POINT" ]; then
    mkdir -p "$MOUNT_POINT"
    echo "  ✅ Created $MOUNT_POINT"
else
    echo "  ✅ $MOUNT_POINT already exists"
fi

# Step 2: Install NFS utilities if needed
echo "📦 Step 2: Checking NFS utilities..."
if ! command -v mount.nfs &> /dev/null; then
    # Detect the OS and install accordingly
    if [ -f /etc/debian_version ]; then
        apt-get update
        apt-get install -y nfs-common
    elif [ -f /etc/redhat-release ]; then
        yum install -y nfs-utils
    else
        echo "  ❌ Unsupported OS. Please install NFS utilities manually."
        exit 1
    fi
    echo "  ✅ Installed NFS utilities"
else
    echo "  ✅ NFS utilities already installed"
fi

# Step 3: Start required services
echo "🔧 Step 3: Starting required NFS services..."
# Try to start services but don't fail if they're already running or not needed
if command -v systemctl &> /dev/null; then
    systemctl start rpcbind 2>/dev/null || echo "  rpcbind already running or not needed"
    systemctl start nfs-common 2>/dev/null || echo "  nfs-common already running or not needed"
else
    service rpcbind start 2>/dev/null || echo "  rpcbind already running or not needed"
    service nfs-common start 2>/dev/null || echo "  nfs-common already running or not needed"
fi

# Step 4: Check for existing mounts
echo "🔄 Step 4: Checking for existing mounts..."
if mountpoint -q "$MOUNT_POINT"; then
    echo "  ⚠️  Unmounting existing filesystem..."
    umount "$MOUNT_POINT" || umount -l "$MOUNT_POINT"
    echo "  ✅ Unmounted existing filesystem"
else
    echo "  ✅ No existing mount found"
fi

# Step 5: Mount the shared filesystem
echo "🔗 Step 5: Mounting shared filesystem..."
# Try mounting with different options
echo "  Attempting to mount..."
if ! mount -t nfs -o nconnect=16 "$NFS_ENDPOINT" "$MOUNT_POINT" 2>/dev/null; then
    echo "  Trying with nolock option..."
    if ! mount -t nfs -o nolock,nconnect=16 "$NFS_ENDPOINT" "$MOUNT_POINT" 2>/dev/null; then
        echo "  Trying with basic options..."
        mount -t nfs -o nolock "$NFS_ENDPOINT" "$MOUNT_POINT"
    fi
fi
echo "  ✅ Mounted shared filesystem"

# Step 6: Verify mount
echo "🔍 Step 6: Verifying mount..."
if mountpoint -q "$MOUNT_POINT"; then
    echo "  ✅ Mount verification successful"
    df -h | grep "$MOUNT_POINT" || true
    
    # List contents to verify access
    echo "  📂 Checking directory contents:"
    ls -la "$MOUNT_POINT" || echo "  ⚠️  Could not list directory contents"
else
    echo "  ❌ Mount verification failed"
    exit 1
fi

# Step 7: Update fstab for persistent mounting
echo "💾 Step 7: Setting up persistent mounting..."
FSTAB_LINE="$NFS_ENDPOINT $MOUNT_POINT nfs defaults,nolock,nconnect=16 0 0"
# Remove any old entries for this mount point
sed -i "\|$MOUNT_POINT|d" /etc/fstab
# Add new entry
echo "$FSTAB_LINE" >> /etc/fstab
echo "  ✅ Added to /etc/fstab for persistent mounting"

# Step 8: Create GPU processing directories if needed
echo "📂 Step 8: Ensuring GPU processing directories exist..."
# These should already exist from CPU setup, but let's make sure
if [ ! -d "$MOUNT_POINT/uploads" ]; then
    mkdir -p "$MOUNT_POINT/uploads"
    echo "  ✅ Created uploads directory"
fi
if [ ! -d "$MOUNT_POINT/results" ]; then
    mkdir -p "$MOUNT_POINT/results"
    echo "  ✅ Created results directory"
fi
if [ ! -d "$MOUNT_POINT/temp" ]; then
    mkdir -p "$MOUNT_POINT/temp"
    echo "  ✅ Created temp directory"
fi

# Step 9: Set permissions
echo "🔐 Step 9: Setting permissions..."
# Make sure GPU can read/write
chmod -R 755 "$MOUNT_POINT"
echo "  ✅ Set permissions to 755"

# Step 10: Test write access
echo "🧪 Step 10: Testing write access..."
TEST_FILE="$MOUNT_POINT/gpu-test-$(date +%s).txt"
if echo "GPU instance connected at $(date)" > "$TEST_FILE" 2>/dev/null; then
    echo "  ✅ Write test successful"
    echo "  📄 Test file created: $TEST_FILE"
else
    echo "  ❌ Write test failed - check permissions"
fi

echo ""
echo "🎉 GPU shared filesystem setup completed successfully!"
echo ""
echo "📊 Summary:"
echo "  Mount Point: $MOUNT_POINT"
echo "  NFS Endpoint: $NFS_ENDPOINT"
echo "  Access: Read/Write"
echo ""
echo "🔍 Shared directories available:"
echo "  - Uploads: $MOUNT_POINT/uploads (for PDF uploads from CPU)"
echo "  - Results: $MOUNT_POINT/results (for AI processing results)"
echo "  - Temp: $MOUNT_POINT/temp (for temporary files)"
echo ""
echo "📝 Next steps on GPU:"
echo "  1. Configure GPU processing service to use $MOUNT_POINT"
echo "  2. Update any GPU processing scripts to read from uploads/"
echo "  3. Update any GPU processing scripts to write to results/"