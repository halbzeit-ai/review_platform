#!/bin/bash

# Quick deployment script for GPU instance
# Usage: ./deploy_to_gpu.sh <gpu_instance_ip>

GPU_IP=$1
if [ -z "$GPU_IP" ]; then
    echo "Usage: $0 <gpu_instance_ip>"
    exit 1
fi

echo "Deploying to GPU instance: $GPU_IP"

# Copy processing code to GPU instance
scp -r gpu_processing/ root@$GPU_IP:/tmp/

# Install on GPU instance
ssh root@$GPU_IP << 'EOF'
# Install Python dependencies
pip3 install pdf2image torch torchvision requests pillow

# Copy processing code to shared filesystem
cp -r /tmp/gpu_processing /mnt/shared/

# Create processing directories
mkdir -p /mnt/shared/results
mkdir -p /mnt/shared/temp

# Test installation
cd /mnt/shared/gpu_processing
python3 -c "from utils.pitch_deck_analyzer import PitchDeckAnalyzer; print('AI analyzer imported successfully')"

echo "GPU instance setup complete!"
EOF

echo "Deployment completed successfully!"