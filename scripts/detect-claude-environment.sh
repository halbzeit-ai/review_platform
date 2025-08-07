#!/bin/bash

# detect-claude-environment.sh
# Detects which server Claude Code is running on based on IP address and hostname

# Get the current IP address
CURRENT_IP=$(hostname -I | awk '{print $1}')
HOSTNAME=$(hostname)

# Known server IPs and their identifiers
DEV_CPU_IP="65.108.32.143"
DEV_GPU_IP="135.181.71.17"
PROD_CPU_IP="135.181.63.224"
PROD_GPU_IP="135.181.63.133"

# Detect environment based on IP
case "$CURRENT_IP" in
    "$DEV_CPU_IP")
        echo "dev_cpu"
        echo "Claude is running on: Development CPU Server ($DEV_CPU_IP)"
        echo "Capabilities: Full development access, service management, git operations"
        ;;
    "$DEV_GPU_IP")
        echo "dev_gpu"
        echo "Claude is running on: Development GPU Server ($DEV_GPU_IP)"
        echo "Capabilities: AI development, processing debugging, shared filesystem access"
        ;;
    "$PROD_CPU_IP")
        echo "prod_cpu"
        echo "Claude is running on: Production CPU Server ($PROD_CPU_IP)"
        echo "Capabilities: Production management, service debugging, direct deployment"
        ;;
    "$PROD_GPU_IP")
        echo "prod_gpu"
        echo "Claude is running on: Production GPU Server ($PROD_GPU_IP)"
        echo "Capabilities: AI processing, production debugging, shared filesystem access"
        ;;
    *)
        echo "local"
        echo "Claude is running on: Local/Unknown Server ($CURRENT_IP)"
        echo "Hostname: $HOSTNAME"
        echo "Capabilities: Depends on local setup and network access"
        ;;
esac

# Additional environment information
echo ""
echo "Current working directory: $(pwd)"
echo "Git repository status: $(git rev-parse --is-inside-work-tree 2>/dev/null || echo 'Not in git repo')"

# Check if this is the review-platform directory
if [[ $(basename "$(pwd)") == "review-platform" ]]; then
    echo "Located in review-platform repository ✓"
else
    echo "WARNING: Not in review-platform directory"
fi