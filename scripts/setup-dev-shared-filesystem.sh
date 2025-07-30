#!/bin/bash
# Setup script for development shared filesystem mounting

set -e  # Exit on any error

echo "🗂️ Setting up Development Shared Filesystem"
echo "============================================================"

# Configuration for development environment
MOUNT_POINT="/mnt/dev-shared"
NFS_ENDPOINT="nfs.fin-01.datacrunch.io:/dev-cpu-gpu-sf-9d6799ad"
SERVICE_USER="root"  # For development

echo "📋 Configuration:"
echo "  Mount Point: $MOUNT_POINT"
echo "  NFS Endpoint: $NFS_ENDPOINT"
echo "  Service User: $SERVICE_USER"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# Step 1: Remove old mount if exists
echo "🔄 Step 1: Cleaning up old mounts..."
if mountpoint -q "/mnt/shared"; then
    echo "  Unmounting /mnt/shared..."
    umount /mnt/shared || umount -l /mnt/shared
fi

# Remove empty directory
if [ -d "/mnt/shared" ] && [ -z "$(ls -A /mnt/shared)" ]; then
    rmdir /mnt/shared
    echo "  ✅ Removed empty /mnt/shared directory"
fi

# Step 2: Create mount point
echo "📁 Step 2: Creating mount point..."
if [ ! -d "$MOUNT_POINT" ]; then
    mkdir -p "$MOUNT_POINT"
    echo "  ✅ Created $MOUNT_POINT"
else
    echo "  ✅ $MOUNT_POINT already exists"
fi

# Step 3: Install NFS utilities if needed
echo "📦 Step 3: Checking NFS utilities..."
if ! command -v mount.nfs &> /dev/null; then
    apt-get update
    apt-get install -y nfs-common
    echo "  ✅ Installed NFS utilities"
else
    echo "  ✅ NFS utilities already installed"
fi

# Step 4: Start required services
echo "🔧 Step 4: Starting required NFS services..."
systemctl start rpcbind || echo "  rpcbind already running or not needed"
systemctl start nfs-common || echo "  nfs-common already running or not needed"

# Step 5: Mount the development shared filesystem
echo "🔗 Step 5: Mounting development shared filesystem..."
if mountpoint -q "$MOUNT_POINT"; then
    echo "  ⚠️  Unmounting existing filesystem..."
    umount "$MOUNT_POINT"
fi

# Try mounting with different options
echo "  Attempting to mount..."
if ! mount -t nfs -o nconnect=16 "$NFS_ENDPOINT" "$MOUNT_POINT" 2>/dev/null; then
    echo "  Trying with nolock option..."
    mount -t nfs -o nolock,nconnect=16 "$NFS_ENDPOINT" "$MOUNT_POINT"
fi
echo "  ✅ Mounted development shared filesystem"

# Step 6: Verify mount
echo "🔍 Step 6: Verifying mount..."
if mountpoint -q "$MOUNT_POINT"; then
    echo "  ✅ Mount verification successful"
    df -h | grep "$MOUNT_POINT" || true
else
    echo "  ❌ Mount verification failed"
    exit 1
fi

# Step 7: Create required directories
echo "📂 Step 7: Creating required directories..."
mkdir -p "$MOUNT_POINT/uploads"
mkdir -p "$MOUNT_POINT/results" 
mkdir -p "$MOUNT_POINT/temp"
echo "  ✅ Created uploads, results, and temp directories"

# Step 8: Set proper permissions
echo "🔐 Step 8: Setting proper permissions..."
chown -R "$SERVICE_USER:$SERVICE_USER" "$MOUNT_POINT"
chmod -R 755 "$MOUNT_POINT"
echo "  ✅ Set ownership to $SERVICE_USER and permissions to 755"

# Step 9: Update fstab for persistent mounting
echo "💾 Step 9: Setting up persistent mounting..."
FSTAB_LINE="$NFS_ENDPOINT $MOUNT_POINT nfs defaults,nolock,nconnect=16 0 0"
# Remove any old entries
sed -i '/\/mnt\/shared/d' /etc/fstab
# Add new entry if not exists
if ! grep -qF "$MOUNT_POINT" /etc/fstab; then
    echo "$FSTAB_LINE" >> /etc/fstab
    echo "  ✅ Added to /etc/fstab for persistent mounting"
else
    echo "  ✅ Already in /etc/fstab"
fi

# Step 10: Update backend configuration
echo "⚙️  Step 10: Updating backend configuration..."
BACKEND_ENV="/opt/review-platform-dev/backend/.env"
if [ -f "$BACKEND_ENV" ]; then
    # Backup original
    cp "$BACKEND_ENV" "$BACKEND_ENV.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Update shared directory path
    if grep -q "SHARED_DIR=" "$BACKEND_ENV"; then
        sed -i "s|SHARED_DIR=.*|SHARED_DIR=$MOUNT_POINT|" "$BACKEND_ENV"
    else
        echo "SHARED_DIR=$MOUNT_POINT" >> "$BACKEND_ENV"
    fi
    
    echo "  ✅ Updated $BACKEND_ENV with new mount point"
else
    echo "  ⚠️  Backend .env file not found, creating one..."
    cat > "$BACKEND_ENV" << EOF
# Development environment configuration
SHARED_DIR=$MOUNT_POINT
UPLOAD_DIR=$MOUNT_POINT/uploads
RESULTS_DIR=$MOUNT_POINT/results
TEMP_DIR=$MOUNT_POINT/temp
EOF
    echo "  ✅ Created $BACKEND_ENV with development configuration"
fi

echo ""
echo "🎉 Development shared filesystem setup completed successfully!"
echo ""
echo "📊 Summary:"
echo "  Mount Point: $MOUNT_POINT"
echo "  NFS Endpoint: $NFS_ENDPOINT"
echo "  Directories:"
echo "    - Uploads: $MOUNT_POINT/uploads"
echo "    - Results: $MOUNT_POINT/results" 
echo "    - Temp: $MOUNT_POINT/temp"
echo ""
echo "🧪 To test the setup:"
echo "  1. Create a test file: echo 'test' > $MOUNT_POINT/test.txt"
echo "  2. Check from GPU instance: ssh dev-gpu 'cat $MOUNT_POINT/test.txt'"