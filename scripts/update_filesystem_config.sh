#!/bin/bash
# Script to update configuration with new shared filesystem

if [ $# -ne 2 ]; then
    echo "Usage: $0 <NEW_FILESYSTEM_ID> <NEW_NFS_MOUNT_COMMAND>"
    echo ""
    echo "Example:"
    echo "$0 'abc123-def456-ghi789' 'mount -t nfs -o nconnect=16 nfs.fin-01.datacrunch.io:/SFS-NewID /mnt/shared'"
    exit 1
fi

NEW_FILESYSTEM_ID="$1"
NEW_MOUNT_COMMAND="$2"

echo "🔧 Updating Shared Filesystem Configuration"
echo "=" * 50

echo "📋 New Configuration:"
echo "  Filesystem ID: $NEW_FILESYSTEM_ID"
echo "  Mount Command: $NEW_MOUNT_COMMAND"
echo ""

# Update local configuration for testing
echo "✅ Updating local .env file..."
if [ -f "backend/.env" ]; then
    sed -i "s/DATACRUNCH_SHARED_FILESYSTEM_ID=.*/DATACRUNCH_SHARED_FILESYSTEM_ID=$NEW_FILESYSTEM_ID/" backend/.env
    echo "  Updated DATACRUNCH_SHARED_FILESYSTEM_ID in backend/.env"
else
    echo "  ⚠️  Local .env file not found, skipping local update"
fi

# Update GPU processing service
echo "✅ Updating GPU processing service..."
if [ -f "backend/app/services/gpu_processing.py" ]; then
    # Extract the NFS endpoint from the mount command
    NFS_ENDPOINT=$(echo "$NEW_MOUNT_COMMAND" | grep -o 'nfs\.fin-01\.datacrunch\.io:/SFS-[^[:space:]]*')
    
    if [ -n "$NFS_ENDPOINT" ]; then
        sed -i "s|nfs\.fin-01\.datacrunch\.io:/SFS-[^[:space:]]*|$NFS_ENDPOINT|g" backend/app/services/gpu_processing.py
        echo "  Updated NFS mount command in gpu_processing.py"
    else
        echo "  ⚠️  Could not extract NFS endpoint from mount command"
    fi
else
    echo "  ⚠️  GPU processing service file not found"
fi

echo ""
echo "📋 Next steps for production server:"
echo "1. Copy these changes to production:"
echo "   git add -A && git commit -m 'Update shared filesystem configuration'"
echo "   git push origin main"
echo ""
echo "2. On production server:"
echo "   cd /opt/review-platform"
echo "   git pull origin main"
echo "   sudo systemctl restart review-platform"
echo ""
echo "3. Test the new filesystem:"
echo "   ./scripts/test_nfs_gpu.sh"