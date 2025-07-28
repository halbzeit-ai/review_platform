#!/bin/bash

echo "=== Fixing GPU Connection for Model Loading ==="

# GPU server IP from the diagnostics output
GPU_SERVER_IP="135.181.63.133"

# Check if we're on the CPU server
if [ -d "backend" ] || [ -d "/opt/review-platform/backend" ]; then
    echo "Configuring CPU server to connect to GPU server at $GPU_SERVER_IP"
    
    # Create or update .env file for the backend
    if [ -d "backend" ]; then
        BACKEND_DIR="backend"
    else
        BACKEND_DIR="/opt/review-platform/backend"
    fi
    
    ENV_FILE="$BACKEND_DIR/.env"
    
    echo "Creating/updating $ENV_FILE with GPU configuration..."
    
    # Remove existing GPU_INSTANCE_HOST if it exists
    if [ -f "$ENV_FILE" ]; then
        sed -i '/^GPU_INSTANCE_HOST=/d' "$ENV_FILE"
    fi
    
    # Add GPU_INSTANCE_HOST
    echo "GPU_INSTANCE_HOST=$GPU_SERVER_IP" >> "$ENV_FILE"
    
    echo "Configuration updated. Contents of $ENV_FILE:"
    cat "$ENV_FILE"
    
    echo ""
    echo "Testing connection to GPU server..."
    timeout 5 curl -s "http://$GPU_SERVER_IP:8001/api/health" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "✓ Connection to GPU server successful!"
        echo "Health check response:"
        curl -s "http://$GPU_SERVER_IP:8001/api/health" | python3 -m json.tool 2>/dev/null
        echo ""
        echo "Available models:"
        curl -s "http://$GPU_SERVER_IP:8001/api/models" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('success') and 'models' in data:
        print(f'Found {len(data[\"models\"])} models:')
        for model in data['models']:
            print(f'  - {model.get(\"name\", \"unknown\")} ({model.get(\"size\", 0)} bytes)')
    else:
        print(f'Response: {data}')
except Exception as e:
    print(f'Error parsing response: {e}')
" 2>/dev/null
    else
        echo "✗ Cannot connect to GPU server at $GPU_SERVER_IP:8001"
        echo "Please check if the GPU server is running and accessible"
    fi
    
    echo ""
    echo "You may need to restart the backend service for changes to take effect:"
    echo "  systemctl restart your-backend-service"
    
elif [ -d "gpu_processing" ] || [ -d "/opt/review-platform/gpu_processing" ]; then
    echo "This is the GPU server - no configuration needed."
    echo "GPU server is running on $(hostname -I | awk '{print $1}'):8001"
    
    # Check if the service is running
    if systemctl is-active --quiet gpu-http-server; then
        echo "✓ GPU HTTP server service is running"
    else
        echo "✗ GPU HTTP server service is not running"
        echo "Start it with: systemctl start gpu-http-server"
    fi
    
else
    echo "Unknown server type - neither backend nor gpu_processing found"
fi

echo "=== Fix Complete ==="