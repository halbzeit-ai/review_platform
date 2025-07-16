#!/bin/bash

# GPU Service Deployment Script
# This script deploys the GPU HTTP server with proper configuration

set -e

echo "🚀 Deploying GPU HTTP Server with configuration..."

# Configuration
GPU_PROCESSING_DIR="/opt/gpu_processing"
REPO_DIR="/opt/review_platform"
SERVICE_NAME="gpu-http-server"

# Stop existing service
echo "⏹️  Stopping existing service..."
sudo systemctl stop $SERVICE_NAME || true

# Create deployment directory
echo "📁 Creating deployment directory..."
sudo mkdir -p $GPU_PROCESSING_DIR
sudo mkdir -p $GPU_PROCESSING_DIR/config

# Copy files
echo "📋 Copying files..."
sudo cp $REPO_DIR/gpu_processing/gpu_http_server.py $GPU_PROCESSING_DIR/
sudo cp $REPO_DIR/gpu_processing/main.py $GPU_PROCESSING_DIR/
sudo cp $REPO_DIR/gpu_processing/.env.gpu $GPU_PROCESSING_DIR/
sudo cp $REPO_DIR/gpu_processing/requirements.txt $GPU_PROCESSING_DIR/
sudo cp -r $REPO_DIR/gpu_processing/utils $GPU_PROCESSING_DIR/
sudo cp -r $REPO_DIR/gpu_processing/config $GPU_PROCESSING_DIR/

# Install system dependencies
echo "📦 Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    poppler-utils \
    tesseract-ocr \
    python3-dev \
    build-essential \
    pkg-config \
    libcairo2-dev \
    libgirepository1.0-dev

# Verify poppler installation
echo "🔍 Verifying poppler installation..."
if ! command -v pdfinfo &> /dev/null; then
    echo "❌ poppler-utils not found! Installation may have failed."
    exit 1
fi
echo "✅ poppler-utils installed successfully"

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
cd $GPU_PROCESSING_DIR
pip install -r requirements.txt --break-system-packages --ignore-installed

# Verify critical Python packages
echo "🔍 Verifying Python dependencies..."
python3 -c "import pdf2image; print('✅ pdf2image installed')" || echo "❌ pdf2image installation failed"
python3 -c "import PyPDF2; print('✅ PyPDF2 installed')" || echo "❌ PyPDF2 installation failed"
python3 -c "import ollama; print('✅ ollama installed')" || echo "❌ ollama installation failed"
python3 -c "import flask; print('✅ flask installed')" || echo "❌ flask installation failed"

# Copy and enable systemd service
echo "⚙️  Setting up systemd service..."
sudo cp $REPO_DIR/gpu_processing/gpu-http-server.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

# Start service
echo "▶️  Starting service..."
sudo systemctl start $SERVICE_NAME

# Check status
echo "✅ Checking service status..."
sudo systemctl status $SERVICE_NAME --no-pager

echo "🎉 GPU HTTP Server deployed successfully!"
echo "📊 Monitor logs with: sudo journalctl -u $SERVICE_NAME -f"
echo "🔧 Configuration file: $GPU_PROCESSING_DIR/.env.gpu"