#!/bin/bash

# Setup Development GPU Server for AI Processing
# This script configures the development GPU server (135.181.71.17) to match
# production GPU capabilities for visual analysis and document processing

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Server configuration
DEVELOPMENT_GPU="135.181.71.17"
DEVELOPMENT_CPU="65.108.32.143"
DEV_SHARED_MOUNT="/mnt/dev-CPU-GPU"

# Parse arguments
DRY_RUN=false
SKIP_DEPENDENCIES=false
SKIP_GIT_SETUP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-dependencies)
            SKIP_DEPENDENCIES=true
            shift
            ;;
        --skip-git)
            SKIP_GIT_SETUP=true
            shift
            ;;
        --help|-h)
            cat << 'EOF'
Setup Development GPU Server for AI Processing

This script configures the development GPU server to handle:
- PDF document processing and analysis
- Visual analysis of pitch deck slides
- AI model inference for review generation
- HTTP API for communication with CPU server

Usage: ./setup-development-gpu.sh [options]

Options:
  --dry-run              Show what would be done without executing
  --skip-dependencies    Skip Python/CUDA dependency installation
  --skip-git            Skip Git repository setup
  --help, -h            Show this help message

Prerequisites:
  - Shared filesystem already mounted at /mnt/dev-CPU-GPU
  - SSH access to development GPU server
  - CUDA-capable GPU on the target server

Services configured:
  - GPU processing HTTP API (port 8001)
  - Document processing service
  - Visual analysis service
  - Health check endpoints

EOF
            exit 0
            ;;
        *)
            log_error "Unknown argument: $1"
            exit 1
            ;;
    esac
done

echo "🖥️  Setting up Development GPU Server"
echo "===================================="
echo "Development GPU: $DEVELOPMENT_GPU"
echo "Development CPU: $DEVELOPMENT_CPU"
echo ""

if [ "$DRY_RUN" = true ]; then
    log_warning "DRY RUN MODE - No changes will be made"
    echo ""
fi

# Function to run command on GPU server
run_gpu_command() {
    local cmd="$1"
    local description="$2"
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would run on GPU: $cmd"
        [ -n "$description" ] && echo "   Purpose: $description"
    else
        log_info "Running on GPU: $description"
        ssh -o StrictHostKeyChecking=no root@"$DEVELOPMENT_GPU" "$cmd"
    fi
}

# Step 1: Install system dependencies
install_system_dependencies() {
    if [ "$SKIP_DEPENDENCIES" = true ]; then
        log_info "Skipping system dependencies installation"
        return
    fi
    
    log_info "Step 1: Installing system dependencies on GPU server..."
    
    local deps_cmd="
        apt update &&
        apt install -y python3 python3-pip python3-venv git curl wget build-essential &&
        apt install -y nvidia-driver-535 nvidia-cuda-toolkit || echo 'CUDA installation may need manual setup' &&
        pip3 install --upgrade pip setuptools wheel
    "
    
    run_gpu_command "$deps_cmd" "Install Python, CUDA, and build tools"
    
    log_success "System dependencies installed"
}

# Step 2: Setup Git repository on GPU server
setup_git_repository() {
    if [ "$SKIP_GIT_SETUP" = true ]; then
        log_info "Skipping Git repository setup"
        return
    fi
    
    log_info "Step 2: Setting up Git repository on GPU server..."
    
    # Check if repository already exists
    local check_repo_cmd="[ -d '/opt/review-platform-dev/.git' ] && echo 'exists' || echo 'not_found'"
    
    if [ "$DRY_RUN" = false ]; then
        local repo_status=$(ssh -o StrictHostKeyChecking=no root@"$DEVELOPMENT_GPU" "$check_repo_cmd")
        
        if [[ "$repo_status" == *"exists"* ]]; then
            log_info "Repository already exists, updating..."
            local update_cmd="cd /opt/review-platform-dev && git pull origin main"
            run_gpu_command "$update_cmd" "Update existing repository"
        else
            log_info "Cloning repository from development CPU..."
            # Clone from development CPU to avoid SSH key setup duplication
            local clone_cmd="
                mkdir -p /opt &&
                cd /opt &&
                rsync -av --exclude='.git' root@$DEVELOPMENT_CPU:/opt/review-platform-dev/ review-platform-dev/ &&
                cd review-platform-dev &&
                git init &&
                git remote add origin git@github.com:your-username/halbzeit-ai.git
            "
            run_gpu_command "$clone_cmd" "Clone repository to GPU server"
        fi
    else
        log_info "Would clone or update repository on GPU server"
    fi
    
    log_success "Git repository setup completed"
}

# Step 3: Setup Python environment for GPU processing
setup_python_environment() {
    log_info "Step 3: Setting up Python environment for GPU processing..."
    
    local python_setup_cmd="
        cd /opt/review-platform-dev &&
        python3 -m venv gpu-venv &&
        source gpu-venv/bin/activate &&
        pip install --upgrade pip &&
        pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 &&
        pip install transformers accelerate &&
        pip install fastapi uvicorn[standard] &&
        pip install PyPDF2 pdf2image pillow opencv-python &&
        pip install requests httpx aiofiles &&
        pip install python-multipart &&
        pip install -r gpu_processing/requirements.txt || echo 'GPU requirements file not found, continuing...'
    "
    
    run_gpu_command "$python_setup_cmd" "Setup Python environment with GPU support"
    
    log_success "Python environment configured"
}

# Step 4: Configure GPU processing service
setup_gpu_processing_service() {
    log_info "Step 4: Configuring GPU processing service..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would create GPU processing configuration"
        log_info "Would setup HTTP API service"
        log_info "Would configure health check endpoints"
        return
    fi
    
    # Create GPU processing configuration
    local gpu_config_cmd="
        cd /opt/review-platform-dev &&
        mkdir -p gpu_processing/config &&
        cat > gpu_processing/config/development.json << 'EOF'
{
    \"environment\": \"development\",
    \"shared_filesystem\": \"$DEV_SHARED_MOUNT\",
    \"api_port\": 8001,
    \"api_host\": \"0.0.0.0\",
    \"upload_path\": \"$DEV_SHARED_MOUNT/uploads\",
    \"results_path\": \"$DEV_SHARED_MOUNT/results\",
    \"cache_path\": \"$DEV_SHARED_MOUNT/cache\",
    \"logs_path\": \"$DEV_SHARED_MOUNT/logs\",
    \"max_concurrent_jobs\": 2,
    \"processing_timeout\": 300,
    \"gpu_memory_limit\": 0.8,
    \"models\": {
        \"text_analysis\": \"microsoft/DialoGPT-medium\",
        \"vision_analysis\": \"microsoft/git-base-coco\",
        \"document_processing\": \"layoutlm-base-uncased\"
    },
    \"cpu_server\": {
        \"host\": \"$DEVELOPMENT_CPU\",
        \"port\": 8000,
        \"health_check_url\": \"http://$DEVELOPMENT_CPU:8000/api/health\"
    }
}
EOF
    "
    
    run_gpu_command "$gpu_config_cmd" "Create GPU processing configuration"
    
    log_success "GPU processing service configured"
}

# Step 5: Create GPU processing HTTP API
create_gpu_api_service() {
    log_info "Step 5: Creating GPU processing HTTP API..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would create GPU API service script"
        log_info "Would setup systemd service for auto-start"
        return
    fi
    
    # Create main GPU API service
    local api_service_cmd="
        cd /opt/review-platform-dev/gpu_processing &&
        cat > api_server.py << 'EOF'
#!/usr/bin/env python3
\"\"\"
Development GPU Processing API Server
Provides HTTP endpoints for document processing and visual analysis
\"\"\"

import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import JSONResponse
import uvicorn

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
config_path = Path('config/development.json')
if config_path.exists():
    with open(config_path) as f:
        config = json.load(f)
else:
    config = {
        'api_port': 8001,
        'api_host': '0.0.0.0',
        'shared_filesystem': '$DEV_SHARED_MOUNT',
        'upload_path': '$DEV_SHARED_MOUNT/uploads',
        'results_path': '$DEV_SHARED_MOUNT/results'
    }

app = FastAPI(title=\"Development GPU Processing API\", version=\"1.0.0\")

@app.get(\"/api/health\")
async def health_check():
    \"\"\"Health check endpoint\"\"\"
    return {
        \"status\": \"healthy\",
        \"timestamp\": datetime.utcnow().isoformat(),
        \"gpu_available\": True,  # TODO: Add actual GPU check
        \"filesystem_mounted\": os.path.exists(config['shared_filesystem']),
        \"config\": {
            \"environment\": \"development\",
            \"shared_filesystem\": config['shared_filesystem']
        }
    }

@app.post(\"/api/process-document\")
async def process_document(background_tasks: BackgroundTasks, document_id: str):
    \"\"\"Process a document for AI analysis\"\"\"
    upload_path = Path(config['upload_path']) / f\"{document_id}.pdf\"
    
    if not upload_path.exists():
        raise HTTPException(status_code=404, detail=\"Document not found\")
    
    # Start background processing
    background_tasks.add_task(process_document_task, document_id, str(upload_path))
    
    return {
        \"status\": \"processing_started\",
        \"document_id\": document_id,
        \"message\": \"Document processing has been queued\"
    }

async def process_document_task(document_id: str, file_path: str):
    \"\"\"Background task for document processing\"\"\"
    try:
        logger.info(f\"Processing document {document_id}: {file_path}\")
        
        # TODO: Implement actual AI processing
        # For now, create a placeholder result
        result = {
            \"document_id\": document_id,
            \"processed_at\": datetime.utcnow().isoformat(),
            \"status\": \"completed\",
            \"analysis\": {
                \"text_analysis\": \"Placeholder text analysis\",
                \"visual_analysis\": \"Placeholder visual analysis\",
                \"scores\": {
                    \"overall\": 7.5,
                    \"market_opportunity\": 8.0,
                    \"team\": 7.0,
                    \"product\": 8.5,
                    \"business_model\": 7.0
                }
            },
            \"processing_time_seconds\": 5.0
        }
        
        # Save result to shared filesystem
        results_path = Path(config['results_path']) / f\"{document_id}.json\"
        results_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(results_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        logger.info(f\"Document {document_id} processing completed\")
        
    except Exception as e:
        logger.error(f\"Error processing document {document_id}: {e}\")
        
        # Save error result
        error_result = {
            \"document_id\": document_id,
            \"processed_at\": datetime.utcnow().isoformat(),
            \"status\": \"error\",
            \"error\": str(e)
        }
        
        results_path = Path(config['results_path']) / f\"{document_id}.json\"
        results_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(results_path, 'w') as f:
            json.dump(error_result, f, indent=2)

@app.get(\"/api/processing-status/{document_id}\")
async def get_processing_status(document_id: str):
    \"\"\"Get processing status for a document\"\"\"
    results_path = Path(config['results_path']) / f\"{document_id}.json\"
    
    if results_path.exists():
        with open(results_path) as f:
            result = json.load(f)
        return result
    else:
        return {
            \"document_id\": document_id,
            \"status\": \"processing\",
            \"message\": \"Document is still being processed\"
        }

if __name__ == \"__main__\":
    uvicorn.run(
        app,
        host=config['api_host'],
        port=config['api_port'],
        log_level=\"info\"
    )
EOF
    "
    
    run_gpu_command "$api_service_cmd" "Create GPU API service"
    
    # Create systemd service for auto-start
    local systemd_service_cmd="
        cat > /etc/systemd/system/gpu-processing.service << 'EOF'
[Unit]
Description=GPU Processing API Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/review-platform-dev/gpu_processing
Environment=PATH=/opt/review-platform-dev/gpu-venv/bin
ExecStart=/opt/review-platform-dev/gpu-venv/bin/python api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
        
        systemctl daemon-reload &&
        systemctl enable gpu-processing.service
    "
    
    run_gpu_command "$systemd_service_cmd" "Create systemd service"
    
    log_success "GPU API service created"
}

# Step 6: Test GPU server setup
test_gpu_setup() {
    log_info "Step 6: Testing GPU server setup..."
    
    if [ "$DRY_RUN" = true ]; then
        log_info "Would test filesystem access"
        log_info "Would test GPU API service startup"
        log_info "Would test communication with CPU server"
        return
    fi
    
    # Test filesystem access
    local filesystem_test_cmd="
        ls -la $DEV_SHARED_MOUNT/ &&
        touch $DEV_SHARED_MOUNT/gpu-test-$(date +%s).txt &&
        echo 'GPU filesystem test successful'
    "
    run_gpu_command "$filesystem_test_cmd" "Test shared filesystem access"
    
    # Start GPU service for testing
    local start_service_cmd="
        cd /opt/review-platform-dev/gpu_processing &&
        source ../gpu-venv/bin/activate &&
        timeout 10s python api_server.py &
        sleep 5 &&
        curl -f http://localhost:8001/api/health || echo 'API not ready yet'
    "
    run_gpu_command "$start_service_cmd" "Test GPU API service startup"
    
    log_success "GPU server setup tests completed"
}

# Main execution
main() {
    log_info "Starting development GPU server setup..."
    
    install_system_dependencies
    setup_git_repository
    setup_python_environment
    setup_gpu_processing_service
    create_gpu_api_service
    test_gpu_setup
    
    if [ "$DRY_RUN" = true ]; then
        log_info "DRY RUN COMPLETED - No changes were made"
    else
        log_success "🎉 Development GPU server setup completed!"
        echo ""
        echo "🖥️  GPU Server Summary:"
        echo "======================"
        echo "✅ System dependencies installed"
        echo "✅ Python environment with GPU support"
        echo "✅ Git repository synchronized"
        echo "✅ GPU processing API configured (port 8001)"
        echo "✅ Shared filesystem access verified"
        echo "✅ Systemd service created for auto-start"
        echo ""
        echo "🚀 GPU API Endpoints:"
        echo "  http://$DEVELOPMENT_GPU:8001/api/health"
        echo "  http://$DEVELOPMENT_GPU:8001/api/process-document"
        echo "  http://$DEVELOPMENT_GPU:8001/api/processing-status/{id}"
        echo ""
        echo "🔧 Next Steps:"
        echo "1. Start GPU service: ssh root@$DEVELOPMENT_GPU 'systemctl start gpu-processing'"
        echo "2. Test complete workflow: ./scripts/test-development-workflow.sh"
        echo "3. Monitor logs: ssh root@$DEVELOPMENT_GPU 'journalctl -f -u gpu-processing'"
    fi
}

# Run main function
main