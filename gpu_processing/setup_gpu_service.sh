#!/bin/bash

# Setup GPU Command Service on GPU instance
# This script sets up the GPU command service that monitors shared filesystem
# for model management commands from the production server

set -e  # Exit on any error

echo "🔧 Setting up GPU Command Service..."

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

# Check required commands
check_command "python3"
check_command "pip3"
check_command "systemctl"

# Check if shared filesystem is mounted
if ! mountpoint -q /mnt/CPU-GPU 2>/dev/null; then
    echo "❌ Error: Shared filesystem is not mounted at /mnt/CPU-GPU"
    echo "   Please mount the shared filesystem first:"
    echo "   sudo mount -t nfs -o nconnect=16 nfs.fin-01.datacrunch.io:/CPU-GPU-d3ddf613 /mnt/CPU-GPU"
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

# Install Python dependencies
echo "📦 Installing Python dependencies..."
# Always use --break-system-packages and ignore conflicts for system-wide installation
echo "🔧 Installing ollama with --break-system-packages and --ignore-installed..."
pip3 install --break-system-packages --ignore-installed ollama

# Verify installation
if python3 -c "import ollama" 2>/dev/null; then
    echo "✅ Ollama Python package installed successfully"
else
    echo "❌ Failed to install Ollama Python package"
    exit 1
fi

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

echo ""
echo "🎉 Setup completed successfully!"
echo ""
echo "📋 Useful commands:"
echo "   Status:   sudo systemctl status gpu-command-service"
echo "   Logs:     sudo journalctl -f -u gpu-command-service"
echo "   Restart:  sudo systemctl restart gpu-command-service"
echo "   Stop:     sudo systemctl stop gpu-command-service"
echo ""
echo "📁 Service files:"
echo "   Script:   /opt/gpu_processing/gpu_command_service.py"
echo "   Service:  /etc/systemd/system/gpu-command-service.service"
echo "   Commands: /mnt/CPU-GPU/gpu_commands/"
echo "   Status:   /mnt/CPU-GPU/gpu_status/"
echo ""
echo "💡 The service will now monitor /mnt/CPU-GPU/gpu_commands/ for commands"
echo "   and write responses to /mnt/CPU-GPU/gpu_status/"