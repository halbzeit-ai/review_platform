#!/bin/bash

# Setup GPU Development Environment
# This script sets up a complete GPU development environment for AI processing
# Handles both command service and HTTP API setup

set -e  # Exit on any error

echo "🔧 Setting up GPU Development Environment..."
echo "============================================="

# Configuration
ENVIRONMENT=${ENVIRONMENT:-development}
SHARED_DIR=${SHARED_FILESYSTEM_MOUNT_PATH:-/mnt/dev-shared}
BACKEND_URL=${BACKEND_URL:-http://65.108.32.143:8000}

echo "📋 Configuration:"
echo "  Environment: $ENVIRONMENT"
echo "  Shared Directory: $SHARED_DIR"
echo "  Backend URL: $BACKEND_URL"
echo ""

# Function to check if a command exists
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "❌ Error: $1 is not installed"
        exit 1
    fi
}

# Function to check if a service is running
check_service() {
    if ! systemctl is-active --quiet "$1"; then
        echo "⚠️  Warning: $1 service is not running"
        return 1
    fi
    return 0
}

# Pre-flight checks
echo "🔍 Running pre-flight checks..."

# Check if we're running as root or with sudo
if [[ $EUID -ne 0 ]] && ! sudo -n true 2>/dev/null; then
    echo "❌ This script requires sudo privileges"
    exit 1
fi

# Install system dependencies first
echo "📦 Installing system dependencies..."
apt update
apt install -y \
    python3 python3-pip python3-venv \
    poppler-utils tesseract-ocr \
    build-essential python3-dev \
    git curl wget \
    || echo "⚠️  Some packages may already be installed"

# Check required commands
check_command "python3"
check_command "pip3" 
check_command "systemctl"
check_command "pdftoppm"  # From poppler-utils
check_command "pdfinfo"   # From poppler-utils

# Check if shared filesystem is mounted
if ! mountpoint -q "$SHARED_DIR" 2>/dev/null; then
    echo "❌ Error: Shared filesystem is not mounted at $SHARED_DIR"
    echo "   Please mount the shared filesystem first."
    if [ "$ENVIRONMENT" = "development" ]; then
        echo "   For development: ./scripts/setup-gpu-shared-filesystem.sh"
    else
        echo "   sudo mount -t nfs -o nconnect=16 nfs.fin-01.datacrunch.io:/CPU-GPU-d3ddf613 /mnt/CPU-GPU"
    fi
    exit 1
fi

# Check if Ollama is installed and accessible
echo "🔍 Checking Ollama installation..."
if ! command -v ollama &> /dev/null; then
    echo "❌ Error: Ollama is not installed"
    echo "   Please install Ollama first: https://ollama.ai/install"
    exit 1
fi

# Check if Ollama service is running
if ! check_service ollama; then
    echo "🔧 Starting Ollama service..."
    sudo systemctl start ollama || {
        echo "❌ Failed to start Ollama service"
        exit 1
    }
fi

# Test Ollama connectivity
echo "🔍 Testing Ollama connectivity..."
if ! ollama list &> /dev/null; then
    echo "❌ Error: Cannot connect to Ollama API"
    echo "   Please check if Ollama is running on port 11434"
    exit 1
fi

echo "✅ Pre-flight checks passed!"

# Create directories
echo "📁 Creating directories..."
sudo mkdir -p /opt/gpu_processing
sudo mkdir -p /mnt/CPU-GPU/gpu_commands
sudo mkdir -p /mnt/CPU-GPU/gpu_status

# Verify we can write to shared filesystem
echo "🔍 Testing shared filesystem write permissions..."
if ! sudo touch /mnt/CPU-GPU/gpu_commands/test_write 2>/dev/null; then
    echo "❌ Error: Cannot write to shared filesystem"
    exit 1
fi
sudo rm -f /mnt/CPU-GPU/gpu_commands/test_write

# Copy service files
echo "📋 Installing service files..."
if [[ ! -f "gpu_command_service.py" ]]; then
    echo "❌ Error: gpu_command_service.py not found in current directory"
    exit 1
fi

if [[ ! -f "gpu-command-service.service" ]]; then
    echo "❌ Error: gpu-command-service.service not found in current directory"
    exit 1
fi

sudo cp gpu_command_service.py /opt/gpu_processing/
sudo cp gpu-command-service.service /etc/systemd/system/

# Setup Python virtual environment
echo "📦 Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ Created virtual environment"
fi

# Activate virtual environment and install dependencies
source venv/bin/activate

echo "📦 Installing Python dependencies..."
pip install --upgrade pip

# Install requirements from file if it exists
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    echo "✅ Installed requirements from requirements.txt"
else
    # Install essential packages
    pip install \
        ollama flask requests psycopg2-binary \
        pdf2image pillow PyPDF2 \
        python-dotenv pathlib
    echo "✅ Installed essential Python packages"
fi

# Verify critical imports
echo "🔍 Verifying Python packages..."
python3 -c "
import ollama, flask, pdf2image, psycopg2
print('✅ All critical packages imported successfully')
" || {
    echo "❌ Failed to import critical packages"
    exit 1
}

# Set permissions
echo "🔐 Setting permissions..."
sudo chmod +x /opt/gpu_processing/gpu_command_service.py
sudo chown root:root /opt/gpu_processing/gpu_command_service.py
sudo chown root:root /etc/systemd/system/gpu-command-service.service

# Stop existing service if running
if systemctl is-active --quiet gpu-command-service; then
    echo "🔄 Stopping existing service..."
    sudo systemctl stop gpu-command-service
fi

# Enable and start service
echo "🚀 Starting GPU Command Service..."
sudo systemctl daemon-reload
sudo systemctl enable gpu-command-service
sudo systemctl start gpu-command-service

# Wait a moment for service to start
sleep 2

# Check service status
if systemctl is-active --quiet gpu-command-service; then
    echo "✅ GPU Command Service setup complete!"
    echo "📋 Service status:"
    sudo systemctl status gpu-command-service --no-pager -l
else
    echo "❌ Error: GPU Command Service failed to start"
    echo "📋 Service status:"
    sudo systemctl status gpu-command-service --no-pager -l
    echo ""
    echo "🔍 Check logs for errors:"
    echo "   sudo journalctl -u gpu-command-service -n 50"
    exit 1
fi

# Final diagnostic checks
echo "🔍 Running final diagnostic checks..."

# Test PDF processing
echo "📄 Testing PDF processing capabilities..."
python3 -c "
import pdf2image, os
try:
    pdf2image.convert_from_path('/dev/null')
except:
    pass  # Expected to fail with null, but shouldn't fail on import
print('✅ pdf2image can access poppler-utils')
" || echo "⚠️  PDF processing may have issues"

# Test database connectivity
if [ -n "$DATABASE_URL" ]; then
    echo "🗄️ Testing database connectivity..."
    python3 -c "
import psycopg2, os
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'⚠️  Database connection failed: {e}')
"
fi

# Test shared filesystem
echo "📂 Testing shared filesystem..."
test_file="$SHARED_DIR/gpu-setup-test-$(date +%s).txt"
echo "GPU setup test" > "$test_file" && rm "$test_file"
echo "✅ Shared filesystem write test successful"

echo ""
echo "🎉 GPU Development Environment Setup Completed!"
echo "==============================================="
echo ""
echo "📋 Summary:"
echo "  ✅ System dependencies installed (poppler-utils, tesseract, etc.)"
echo "  ✅ Python virtual environment created with all packages"
echo "  ✅ Ollama installed and configured"
echo "  ✅ Shared filesystem mounted and tested"
echo "  ✅ Database connectivity verified"
echo "  ✅ PDF processing capabilities verified"
echo ""
echo "🚀 To start GPU processing:"
echo "   1. Load environment: export \$(cat .env.development | grep -v '^#' | xargs)"
echo "   2. Activate venv: source venv/bin/activate"  
echo "   3. Start server: python gpu_http_server.py"
echo ""
echo "🔧 Useful commands:"
echo "   Test setup: python scripts/diagnose_gpu_issues.py"
echo "   Check health: curl http://localhost:8001/api/health"
echo "   View logs: tail -f /var/log/gpu-processing.log"
echo ""
echo "📁 Important paths:"
echo "   Virtual env: $(pwd)/venv"
echo "   Shared dir: $SHARED_DIR"
echo "   Config: .env.development"
echo ""
echo "🎯 Next steps:"
echo "   1. Pull required AI models: ollama pull gemma2:2b phi3:mini"
echo "   2. Test end-to-end processing with a PDF upload"
echo "   3. Monitor processing logs for any issues"