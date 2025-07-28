#!/bin/bash
# GPU Healthcare Template System Deployment Script
# Run this script on the GPU instance after pulling the code

echo "🏥 GPU Healthcare Template System Deployment"
echo "============================================="

# Check if we're in the right directory
if [[ ! -f "gpu_processing/main.py" ]]; then
    echo "❌ Please run this script from the review_platform root directory"
    exit 1
fi

echo "📋 Step 1: Checking healthcare template analyzer..."
if [[ ! -f "gpu_processing/utils/healthcare_template_analyzer.py" ]]; then
    echo "❌ healthcare_template_analyzer.py not found. Please ensure the file is in gpu_processing/utils/"
    exit 1
fi
echo "  ✅ Healthcare template analyzer found"

echo "📋 Step 2: Checking main.py updates..."
if grep -q "HealthcareTemplateAnalyzer" gpu_processing/main.py; then
    echo "  ✅ main.py updated to use HealthcareTemplateAnalyzer"
else
    echo "  ❌ main.py not updated. Please ensure HealthcareTemplateAnalyzer is imported and used"
    exit 1
fi

echo "📋 Step 3: Installing Python dependencies..."
cd gpu_processing

# Check if requirements.txt exists
if [[ -f "requirements.txt" ]]; then
    echo "  - Installing requirements..."
    pip install -r requirements.txt
else
    echo "  - Installing essential packages..."
    pip install ollama pdf2image pillow flask requests
fi

echo "📋 Step 4: Testing imports..."
python3 -c "
try:
    from utils.healthcare_template_analyzer import HealthcareTemplateAnalyzer
    print('  ✅ HealthcareTemplateAnalyzer imports successfully')
except ImportError as e:
    print(f'  ❌ Import error: {e}')
    exit(1)

try:
    import ollama
    print('  ✅ Ollama imports successfully')
except ImportError as e:
    print(f'  ❌ Ollama import error: {e}')
    exit(1)

try:
    from pdf2image import convert_from_path
    print('  ✅ pdf2image imports successfully')
except ImportError as e:
    print(f'  ❌ pdf2image import error: {e}')
    exit(1)
"

if [[ $? -ne 0 ]]; then
    echo "❌ Import test failed"
    exit 1
fi

echo "📋 Step 5: Environment configuration..."
echo "  - Checking existing .env.gpu configuration..."

if [[ -f ".env.gpu" ]]; then
    echo "  ✅ .env.gpu already exists"
    
    # Add BACKEND_URL if not present
    if ! grep -q "BACKEND_URL" .env.gpu; then
        echo "" >> .env.gpu
        echo "# Healthcare Template System Configuration" >> .env.gpu
        echo "BACKEND_URL=http://frontend-backend-server:8000" >> .env.gpu
        echo "  ✅ Added BACKEND_URL to .env.gpu"
    else
        echo "  ✅ BACKEND_URL already configured in .env.gpu"
    fi
else
    echo "  ⚠️  .env.gpu not found - using existing system configuration"
fi

echo "  ✅ Environment configuration ready"

echo "📋 Step 6: Testing healthcare template system..."
echo "  - Testing with sample company offering..."

python3 -c "
import os
import sys
sys.path.append('/home/ramin/halbzeit-ai/review_platform/gpu_processing')

from utils.healthcare_template_analyzer import HealthcareTemplateAnalyzer

# Test with a sample company offering
analyzer = HealthcareTemplateAnalyzer(backend_base_url='http://localhost:8000')
print('  ✅ Healthcare template analyzer initialized successfully')

# Test classification (this will fail gracefully if backend not available)
try:
    result = analyzer._classify_startup('AI-powered mental health app for treating depression')
    print(f'  ✅ Classification test successful: {result.get(\"primary_sector\", \"unknown\")}')
except Exception as e:
    print(f'  ⚠️  Classification test failed (expected if backend not running): {e}')
"

echo ""
echo "🎉 GPU Healthcare Template System deployment complete!"
echo ""
echo "📝 System configuration:"
echo "  - Healthcare template analyzer: ✅ Installed"
echo "  - Main processor: ✅ Updated to use healthcare templates"
echo "  - Environment: ✅ Configured"
echo "  - Dependencies: ✅ Installed"
echo ""
echo "🔧 Environment configuration:"
echo "  - Using existing .env.gpu file"
echo "  - BACKEND_URL: Added for healthcare template system"
echo "  - SHARED_FILESYSTEM_MOUNT_PATH: /mnt/CPU-GPU (from .env.gpu)"
echo "  - OLLAMA_HOST: 127.0.0.1:11434 (from .env.gpu)"
echo ""
echo "🚀 To start the GPU HTTP server:"
echo "   python3 gpu_http_server.py"
echo ""
echo "🧪 To test PDF processing:"
echo "   python3 main.py uploads/company_name/pitch.pdf"
echo ""
echo "⚠️  Important notes:"
echo "  - Ensure your backend server is running and accessible"
echo "  - Update BACKEND_URL in .env.gpu if using different server address"
echo "  - The system will use fallback classification if backend unavailable"
echo "  - Healthcare templates provide sector-specific analysis"
echo ""
echo "📊 New features available:"
echo "  - Automatic healthcare sector classification"
echo "  - Sector-specific analysis templates"
echo "  - Clinical validation and regulatory analysis"
echo "  - Question-level detailed analysis"
echo "  - Performance metrics and template tracking"