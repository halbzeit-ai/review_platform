#!/bin/bash
# Simple GPU processing test script

echo "🧪 GPU Processing Test - Simple Version"
echo "=" * 50

# Check if we're in the right directory
if [ ! -f "/opt/review-platform/backend/app/services/gpu_processing.py" ]; then
    echo "❌ Not in the correct directory or files missing"
    exit 1
fi

# Activate virtual environment and test
cd /opt/review-platform/backend
source ../venv/bin/activate

echo "📋 Testing GPU Processing Configuration..."

# Test Python imports
python3 -c "
import sys
sys.path.append('/opt/review-platform/backend')

try:
    from app.services.gpu_processing import GPUProcessingService
    print('✅ GPUProcessingService import successful')
    
    service = GPUProcessingService()
    print(f'✅ GPU Instance Type: {service.gpu_instance_type}')
    print(f'✅ GPU Image: {service.gpu_image}')
    print(f'✅ Processing Timeout: {service.processing_timeout}s')
    
except Exception as e:
    print(f'❌ Import failed: {e}')
    sys.exit(1)

try:
    from app.core.datacrunch import datacrunch_client
    print('✅ Datacrunch client import successful')
except Exception as e:
    print(f'❌ Datacrunch client import failed: {e}')
    sys.exit(1)

try:
    from app.core.config import settings
    print('✅ Settings import successful')
    
    filesystem_id = settings.DATACRUNCH_SHARED_FILESYSTEM_ID
    if filesystem_id:
        print(f'✅ Shared Filesystem ID: {filesystem_id}')
    else:
        print('❌ Shared Filesystem ID not configured')
        sys.exit(1)
        
except Exception as e:
    print(f'❌ Settings import failed: {e}')
    sys.exit(1)

print('✅ All imports successful!')
"

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ GPU Processing Configuration Test PASSED!"
    echo "🚀 Ready to test GPU instance creation"
else
    echo ""
    echo "❌ GPU Processing Configuration Test FAILED!"
    echo "🔧 Check the error messages above"
    exit 1
fi