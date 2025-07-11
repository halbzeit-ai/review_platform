#!/bin/bash
# Sync GPU processing code to shared filesystem

echo "🔄 Syncing GPU processing code to shared filesystem..."

# Check if shared filesystem is mounted
if [ ! -d "/mnt/shared" ]; then
    echo "❌ Shared filesystem not mounted at /mnt/shared"
    exit 1
fi

# Create gpu_processing directory on shared filesystem
mkdir -p /mnt/shared/gpu_processing

# Copy GPU processing code
echo "📁 Copying GPU processing code..."
cp -r /opt/review-platform/gpu_processing/* /mnt/shared/gpu_processing/

# Set permissions
chmod -R 755 /mnt/shared/gpu_processing
chmod +x /mnt/shared/gpu_processing/main.py

echo "✅ GPU processing code synced to shared filesystem"
echo "📝 GPU instances will now use the updated code"

# Verify sync
echo ""
echo "📊 Sync verification:"
echo "Local files:"
find /opt/review-platform/gpu_processing -name "*.py" | wc -l
echo "Shared files:"
find /mnt/shared/gpu_processing -name "*.py" | wc -l

echo ""
echo "🔧 Next steps:"
echo "1. Test GPU processing with a sample PDF"
echo "2. Monitor processing logs for any issues"
echo "3. Update GPU processing code as needed"