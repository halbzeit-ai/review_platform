#!/bin/bash
# Deploy GPU Processing Code to Shared Filesystem
set -e

echo "=== Deploying GPU Processing Code ==="

# Configuration
SHARED_MOUNT_PATH="/mnt/shared"
GPU_CODE_SOURCE="$(dirname "$0")/../gpu_processing"
GPU_CODE_DEST="$SHARED_MOUNT_PATH/gpu_processing_code"

# Check if shared filesystem is mounted
if ! mountpoint -q "$SHARED_MOUNT_PATH"; then
    echo "Error: Shared filesystem not mounted at $SHARED_MOUNT_PATH"
    echo "Please ensure the shared filesystem is properly mounted"
    exit 1
fi

echo "✓ Shared filesystem mounted at $SHARED_MOUNT_PATH"

# Create destination directory
mkdir -p "$GPU_CODE_DEST"

# Copy GPU processing code
echo "Copying GPU processing code..."
rsync -av --delete "$GPU_CODE_SOURCE/" "$GPU_CODE_DEST/"

# Verify critical files exist
CRITICAL_FILES=(
    "main.py"
    "utils/pitch_deck_analyzer.py" 
    "requirements.txt"
    "setup_ai_environment.py"
)

echo "Verifying deployment..."
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$GPU_CODE_DEST/$file" ]; then
        echo "✓ $file"
    else
        echo "✗ Missing: $file"
        exit 1
    fi
done

# Set proper permissions
chmod +x "$GPU_CODE_DEST/main.py"
chmod +x "$GPU_CODE_DEST/setup_ai_environment.py"

# Create version info
echo "{
    \"deployed_at\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
    \"git_commit\": \"$(git rev-parse HEAD 2>/dev/null || echo 'unknown')\",
    \"version\": \"ai-v1.0\"
}" > "$GPU_CODE_DEST/deployment_info.json"

echo "=== GPU Code Deployment Complete ==="
echo "Code deployed to: $GPU_CODE_DEST"
echo "Ready for GPU instance processing"

# Test the deployment
echo ""
echo "Testing deployment..."
cd "$GPU_CODE_DEST"
python3 -c "
try:
    from utils.pitch_deck_analyzer import PitchDeckAnalyzer
    from main import PDFProcessor
    print('✓ All imports successful')
    print('✓ Deployment verified')
except Exception as e:
    print(f'✗ Deployment test failed: {e}')
    exit(1)
"

echo "🎉 GPU processing code successfully deployed and verified!"