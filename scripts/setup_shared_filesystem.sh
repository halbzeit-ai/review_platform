#!/bin/bash
# Setup script for shared filesystem mounting and directory creation

set -e  # Exit on any error

echo "🗂️ Setting up Shared Filesystem for Review Platform"
echo "============================================================"

# Configuration
MOUNT_POINT="/mnt/shared"
NFS_ENDPOINT="nfs.fin-01.datacrunch.io:/SFS-3H6ebwA1-b0cbae8b"
FILESYSTEM_ID="a0a3a880-5dc3-4184-9e76-0279e22bae49"
ENV_FILE="/opt/review-platform/backend/.env"

# Auto-detect service user by checking multiple sources
SERVICE_USER="root"  # Default fallback

# Method 1: Check who owns the project directory
if [ -d "/opt/review-platform" ]; then
    PROJECT_OWNER=$(stat -c '%U' /opt/review-platform)
    echo "🔍 Project directory owner: $PROJECT_OWNER"
fi

# Method 2: Check systemd service configuration
if [ -f "/etc/systemd/system/review-platform.service" ]; then
    SYSTEMD_USER=$(grep "^User=" /etc/systemd/system/review-platform.service | cut -d= -f2 || echo "")
    if [ -n "$SYSTEMD_USER" ]; then
        echo "🔍 Systemd service user: $SYSTEMD_USER"
        SERVICE_USER="$SYSTEMD_USER"
    else
        echo "🔍 Systemd service runs as root (no User= specified)"
        SERVICE_USER="root"
    fi
else
    echo "⚠️  Systemd service file not found, using root"
    SERVICE_USER="root"
fi

echo "✅ Using service user: $SERVICE_USER"

echo "📋 Configuration:"
echo "  Mount Point: $MOUNT_POINT"
echo "  NFS Endpoint: $NFS_ENDPOINT"
echo "  Filesystem ID: $FILESYSTEM_ID"
echo "  Service User: $SERVICE_USER"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# Step 1: Create mount point
echo "📁 Step 1: Creating mount point..."
echo "  Current user: $(whoami)"
echo "  Current permissions on /mnt: $(ls -ld /mnt 2>/dev/null || echo 'Cannot access /mnt')"
echo "  Contents of /mnt: $(ls -la /mnt 2>/dev/null || echo 'Cannot list /mnt')"

# Check if there's an existing mount or filesystem issue
echo "  Checking for existing mounts..."
mount | grep "/mnt" || echo "  No existing mounts in /mnt"

if [ ! -d "$MOUNT_POINT" ]; then
    echo "  Creating directory $MOUNT_POINT..."
    
    # Try different approaches
    if mkdir -p "$MOUNT_POINT" 2>/dev/null; then
        echo "  ✅ Created $MOUNT_POINT successfully"
    else
        echo "  ❌ mkdir failed, trying alternative approach..."
        
        # Check if something is already mounted there
        if mount | grep -q "$MOUNT_POINT"; then
            echo "  ⚠️  Something is already mounted at $MOUNT_POINT"
            umount "$MOUNT_POINT" 2>/dev/null || echo "  Could not unmount"
        fi
        
        # Try creating with different permissions
        echo "  Trying to create with explicit permissions..."
        install -d -m 755 "$MOUNT_POINT" 2>/dev/null || {
            echo "  ❌ All methods failed. Manual intervention needed."
            echo "  Please run: rm -rf $MOUNT_POINT && mkdir -p $MOUNT_POINT"
            exit 1
        }
        echo "  ✅ Created $MOUNT_POINT with install command"
    fi
else
    echo "  ✅ $MOUNT_POINT already exists"
fi

# Step 2: Install NFS utilities if needed
echo "📦 Step 2: Installing NFS utilities..."
if ! command -v mount.nfs &> /dev/null; then
    apt-get update
    apt-get install -y nfs-common
    echo "  ✅ Installed NFS utilities"
else
    echo "  ✅ NFS utilities already installed"
fi

# Step 3: Unmount if already mounted (cleanup)
echo "🔄 Step 3: Checking for existing mounts..."
if mountpoint -q "$MOUNT_POINT"; then
    echo "  ⚠️  Unmounting existing filesystem..."
    umount "$MOUNT_POINT"
    echo "  ✅ Unmounted existing filesystem"
else
    echo "  ✅ No existing mount found"
fi

# Step 4: Mount the new shared filesystem
echo "🔗 Step 4: Mounting new shared filesystem..."
mount -t nfs -o nconnect=16 "$NFS_ENDPOINT" "$MOUNT_POINT"
echo "  ✅ Mounted shared filesystem"

# Step 5: Verify mount
echo "🔍 Step 5: Verifying mount..."
if mountpoint -q "$MOUNT_POINT"; then
    echo "  ✅ Mount verification successful"
    df -h | grep shared
else
    echo "  ❌ Mount verification failed"
    exit 1
fi

# Step 6: Create required directories
echo "📂 Step 6: Creating required directories..."
mkdir -p "$MOUNT_POINT/uploads"
mkdir -p "$MOUNT_POINT/results"
mkdir -p "$MOUNT_POINT/temp"
echo "  ✅ Created uploads, results, and temp directories"

# Step 7: Set proper permissions
echo "🔐 Step 7: Setting proper permissions..."
chown -R "$SERVICE_USER:$SERVICE_USER" "$MOUNT_POINT"
chmod -R 755 "$MOUNT_POINT"
echo "  ✅ Set ownership to $SERVICE_USER and permissions to 755"

# Step 8: Update fstab for persistent mounting
echo "💾 Step 8: Setting up persistent mounting..."
FSTAB_LINE="$NFS_ENDPOINT $MOUNT_POINT nfs defaults,nconnect=16 0 0"
if ! grep -qF "$FSTAB_LINE" /etc/fstab; then
    echo "$FSTAB_LINE" >> /etc/fstab
    echo "  ✅ Added to /etc/fstab for persistent mounting"
else
    echo "  ✅ Already in /etc/fstab"
fi

# Step 9: Update .env file with correct filesystem ID
echo "⚙️  Step 9: Updating .env file..."
if [ -f "$ENV_FILE" ]; then
    # Backup original
    cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    
    # Update filesystem ID
    sed -i "s/DATACRUNCH_SHARED_FILESYSTEM_ID=.*/DATACRUNCH_SHARED_FILESYSTEM_ID=$FILESYSTEM_ID/" "$ENV_FILE"
    echo "  ✅ Updated $ENV_FILE with filesystem ID: $FILESYSTEM_ID"
    echo "  📄 Backup created: $ENV_FILE.backup.*"
else
    echo "  ⚠️  .env file not found at $ENV_FILE"
fi

# Step 10: Restart service
echo "🔄 Step 10: Restarting review-platform service..."
systemctl restart review-platform
echo "  ✅ Service restarted"

# Step 11: Verify service status
echo "🔍 Step 11: Checking service status..."
sleep 3
if systemctl is-active --quiet review-platform; then
    echo "  ✅ Service is running successfully"
else
    echo "  ❌ Service failed to start - checking logs..."
    journalctl -u review-platform --since "1 minute ago" --no-pager
    exit 1
fi

echo ""
echo "🎉 Shared filesystem setup completed successfully!"
echo ""
echo "📊 Summary:"
echo "  Mount Point: $MOUNT_POINT"
echo "  NFS Endpoint: $NFS_ENDPOINT"
echo "  Filesystem ID: $FILESYSTEM_ID"
echo "  Service Status: $(systemctl is-active review-platform)"
echo ""
echo "🧪 Next steps:"
echo "  1. Test file uploads through the web interface"
echo "  2. Test GPU processing: ./scripts/test_nfs_gpu.sh"
echo "  3. Monitor logs: journalctl -f -u review-platform"