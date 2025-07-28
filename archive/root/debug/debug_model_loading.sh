#!/bin/bash

echo "=== Model Loading Diagnostics Script ==="
echo "Server: $(hostname -I | awk '{print $1}')"
echo "Date: $(date)"
echo ""

# Check if this is CPU or GPU server
if [ -d "backend" ] || [ -d "/opt/review-platform/backend" ]; then
    echo "=== CPU SERVER DIAGNOSTICS ==="
    
    echo "1. Backend Configuration:"
    # Find the backend directory
    if [ -d "backend" ]; then
        BACKEND_DIR="backend"
    else
        BACKEND_DIR="/opt/review-platform/backend"
    fi
    cd "$BACKEND_DIR"
    python3 -c "
try:
    from app.core.config import settings
    print(f'  GPU_INSTANCE_HOST: {settings.GPU_INSTANCE_HOST}')
    print(f'  DATABASE_URL: {settings.DATABASE_URL}')
except Exception as e:
    print(f'  Error loading config: {e}')
"
    
    echo ""
    echo "2. Environment Variables:"
    env | grep -E "(GPU|DATABASE|SHARED)" | sort
    
    echo ""
    echo "3. Testing GPU HTTP Client Connection:"
    python3 -c "
import sys
sys.path.append('$BACKEND_DIR')
try:
    from app.services.gpu_http_client import gpu_http_client
    print(f'  GPU Host: {gpu_http_client.gpu_host}')
    print(f'  Base URL: {gpu_http_client.base_url}')
    print(f'  Testing connection...')
    available = gpu_http_client.is_available()
    print(f'  GPU Available: {available}')
    
    if available:
        models = gpu_http_client.get_installed_models()
        print(f'  Found {len(models)} models:')
        for model in models[:5]:  # Show first 5 models
            print(f'    - {model.name} ({model.size} bytes)')
        if len(models) > 5:
            print(f'    ... and {len(models) - 5} more')
    else:
        status = gpu_http_client.check_gpu_status()
        print(f'  GPU Status: {status}')
except Exception as e:
    print(f'  Error: {e}')
"

    echo ""
    echo "4. Testing Direct API Call:"
    echo "  Trying to reach GPU server directly..."
    
    # Try different potential GPU IPs based on common patterns
    for GPU_IP in "localhost" "127.0.0.1" "10.0.0.2" "10.0.0.3" "192.168.1.2"; do
        echo -n "    Testing ${GPU_IP}:8001... "
        timeout 3 curl -s "http://${GPU_IP}:8001/api/health" >/dev/null 2>&1
        if [ $? -eq 0 ]; then
            echo "SUCCESS"
            echo "      Health check response:"
            curl -s "http://${GPU_IP}:8001/api/health" | python3 -m json.tool 2>/dev/null | head -10
            echo ""
            echo "      Models available:"
            curl -s "http://${GPU_IP}:8001/api/models" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data.get('success') and 'models' in data:
        print(f'        Found {len(data[\"models\"])} models:')
        for model in data['models'][:3]:
            print(f'          - {model.get(\"name\", \"unknown\")}')
    else:
        print(f'        Response: {data}')
except:
    print('        Failed to parse JSON response')
" 2>/dev/null
            break
        else
            echo "failed"
        fi
    done

elif [ -d "gpu_processing" ] || [ -d "/opt/review-platform/gpu_processing" ]; then
    echo "=== GPU SERVER DIAGNOSTICS ==="
    
    echo "1. GPU HTTP Server Status:"
    if systemctl is-active --quiet gpu-http-server; then
        echo "  Service Status: RUNNING"
    else
        echo "  Service Status: NOT RUNNING"
        systemctl status gpu-http-server --no-pager -l
    fi
    
    echo ""
    echo "2. Server Configuration:"
    # Find the gpu_processing directory
    if [ -d "gpu_processing" ]; then
        GPU_DIR="gpu_processing"
    else
        GPU_DIR="/opt/review-platform/gpu_processing"
    fi
    cd "$GPU_DIR"
    python3 -c "
try:
    import os
    print(f'  GPU_HTTP_HOST: {os.getenv(\"GPU_HTTP_HOST\", \"0.0.0.0\")}')
    print(f'  GPU_HTTP_PORT: {os.getenv(\"GPU_HTTP_PORT\", \"8001\")}')
    print(f'  PRODUCTION_SERVER_URL: {os.getenv(\"PRODUCTION_SERVER_URL\", \"http://65.108.32.168\")}')
except Exception as e:
    print(f'  Error: {e}')
"

    echo ""
    echo "3. Network Interfaces:"
    ip addr show | grep -E "(inet |UP,)" | head -10
    
    echo ""
    echo "4. Testing Local Server:"
    echo -n "  Testing localhost:8001... "
    timeout 3 curl -s "http://localhost:8001/api/health" >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "SUCCESS"
        curl -s "http://localhost:8001/api/health" | python3 -m json.tool 2>/dev/null
    else
        echo "FAILED"
        echo "  Checking if port 8001 is listening:"
        netstat -ln | grep :8001 || ss -ln | grep :8001
    fi
    
    echo ""
    echo "5. Ollama Status:"
    if command -v ollama >/dev/null 2>&1; then
        echo "  Ollama installed: YES"
        echo "  Available models:"
        ollama list 2>/dev/null | head -10
    else
        echo "  Ollama installed: NO"
    fi
    
    echo ""
    echo "6. Recent GPU Server Logs:"
    if [ -f "/var/log/gpu-http-server.log" ]; then
        echo "  Last 10 lines from /var/log/gpu-http-server.log:"
        tail -n 10 /var/log/gpu-http-server.log
    else
        echo "  Checking journalctl for gpu-http-server:"
        journalctl -u gpu-http-server --no-pager -n 5
    fi

else
    echo "=== UNKNOWN SERVER TYPE ==="
    echo "Neither backend nor gpu_processing directory found"
    echo "Current directory contents:"
    ls -la
fi

echo ""
echo "=== NETWORK CONNECTIVITY ==="
echo "Active network connections on port 8001:"
netstat -an 2>/dev/null | grep :8001 || ss -an 2>/dev/null | grep :8001

echo ""
echo "=== END DIAGNOSTICS ==="