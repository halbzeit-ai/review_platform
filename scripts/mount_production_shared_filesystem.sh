#!/bin/bash
# Mount production shared filesystem on development server for file exchange
# This allows easy access to production data and file sharing

set -e

echo "🗂️ Setting up Production Shared Filesystem Access"
echo "============================================================"

# Production shared filesystem configuration
PROD_MOUNT_POINT="/mnt/production-shared"
PROD_NFS_ENDPOINT="nfs.fin-01.datacrunch.io:/CPU-GPU-d3ddf613"

echo "📋 Configuration:"
echo "  Production Mount Point: $PROD_MOUNT_POINT"
echo "  Production NFS Endpoint: $PROD_NFS_ENDPOINT"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo "❌ This script must be run as root (use sudo)"
   exit 1
fi

# Step 1: Create mount point
echo "📁 Step 1: Creating production mount point..."
if [ ! -d "$PROD_MOUNT_POINT" ]; then
    mkdir -p "$PROD_MOUNT_POINT"
    echo "  ✅ Created $PROD_MOUNT_POINT"
else
    echo "  ✅ $PROD_MOUNT_POINT already exists"
fi

# Step 2: Check for existing mounts
echo "🔄 Step 2: Checking for existing mounts..."
if mountpoint -q "$PROD_MOUNT_POINT"; then
    echo "  ⚠️  Unmounting existing filesystem..."
    umount "$PROD_MOUNT_POINT"
    echo "  ✅ Unmounted existing filesystem"
else
    echo "  ✅ No existing mount found"
fi

# Step 3: Mount the production shared filesystem (read-only for safety)
echo "🔗 Step 3: Mounting production shared filesystem (read-only)..."
if ! mount -t nfs -o ro,nconnect=16 "$PROD_NFS_ENDPOINT" "$PROD_MOUNT_POINT" 2>/dev/null; then
    echo "  Trying with nolock option..."
    mount -t nfs -o ro,nolock,nconnect=16 "$PROD_NFS_ENDPOINT" "$PROD_MOUNT_POINT"
fi
echo "  ✅ Mounted production shared filesystem (read-only)"

# Step 4: Verify mount
echo "🔍 Step 4: Verifying mount..."
if mountpoint -q "$PROD_MOUNT_POINT"; then
    echo "  ✅ Mount verification successful"
    df -h | grep "$PROD_MOUNT_POINT" || true
    
    echo "  📂 Checking directory structure:"
    ls -la "$PROD_MOUNT_POINT" 2>/dev/null || echo "  ⚠️  Could not list directory contents"
else
    echo "  ❌ Mount verification failed"
    exit 1
fi

# Step 5: Update fstab for persistent mounting
echo "💾 Step 5: Setting up persistent mounting..."
FSTAB_LINE="$PROD_NFS_ENDPOINT $PROD_MOUNT_POINT nfs defaults,ro,nolock,nconnect=16 0 0"
# Remove any old entries for this mount point
sed -i "\|$PROD_MOUNT_POINT|d" /etc/fstab
# Add new entry
echo "$FSTAB_LINE" >> /etc/fstab
echo "  ✅ Added to /etc/fstab for persistent mounting (read-only)"

# Step 6: Create file exchange directory
echo "📂 Step 6: Setting up file exchange..."
EXCHANGE_DIR="/opt/file-exchange"
mkdir -p "$EXCHANGE_DIR"
echo "  ✅ Created local file exchange directory: $EXCHANGE_DIR"

echo ""
echo "🎉 Production shared filesystem access completed successfully!"
echo ""
echo "📊 Summary:"
echo "  Production Mount: $PROD_MOUNT_POINT (read-only)"
echo "  Development Mount: /mnt/dev-shared (read-write)"
echo "  File Exchange: $EXCHANGE_DIR (local temp directory)"
echo ""
echo "🔍 Available directories:"
echo "  Production files: $PROD_MOUNT_POINT/uploads, $PROD_MOUNT_POINT/results"
echo "  Development files: /mnt/dev-shared/uploads, /mnt/dev-shared/results"
echo ""
echo "📝 Usage examples:"
echo "  1. Copy file from production: cp $PROD_MOUNT_POINT/uploads/file.pdf $EXCHANGE_DIR/"
echo "  2. Copy prompts: cp /tmp/production_prompts.sql $EXCHANGE_DIR/"
echo "  3. Access production data: ls -la $PROD_MOUNT_POINT/"