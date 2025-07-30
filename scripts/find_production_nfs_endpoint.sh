#!/bin/bash
# Script to run on PRODUCTION server to find the correct NFS endpoint

echo "🔍 Finding Production NFS Endpoint"
echo "=================================="

echo "📋 Current NFS mounts on production server:"
mount | grep nfs || echo "No NFS mounts found"

echo ""
echo "📂 Checking mount points:"
df -h | grep -E "/mnt|nfs" || echo "No relevant mount points found"

echo ""
echo "🔍 Checking shared filesystem environment variables:"
env | grep -i filesystem || echo "No filesystem environment variables found"

echo ""
echo "📄 Checking for shared filesystem configuration files:"
find /opt -name "*.env" -exec grep -l "FILESYSTEM\|NFS\|SHARED" {} \; 2>/dev/null || echo "No config files found"

echo ""
echo "📋 Available Datacrunch filesystems (if any):"
ls -la /mnt/

echo ""
echo "🔧 To get the correct NFS endpoint, check:"
echo "   1. Datacrunch dashboard for your shared filesystem details"
echo "   2. Current production mount: mount | grep shared"
echo "   3. Backend configuration files for SHARED_FILESYSTEM_MOUNT_PATH"