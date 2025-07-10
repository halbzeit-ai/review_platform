#!/bin/bash
# Remote setup script - run this on your Datacrunch instance

set -e

echo "🚀 Setting up Review Platform on Datacrunch instance..."

# Create application directory
mkdir -p /opt/review-platform
cd /opt/review-platform

# Since we can't upload directly, we'll create the essential files here
echo "📁 Creating project structure..."

# Create backend directory structure
mkdir -p backend/app/{api,core,db,services}
mkdir -p frontend/src/{components,pages,services,utils}
mkdir -p deploy

# Install basic dependencies first
echo "📦 Installing system dependencies..."
apt-get update -y
apt-get install -y python3.11 python3.11-venv python3-pip git nginx curl nodejs npm

# Install Docker for database management
apt-get install -y docker.io
systemctl enable docker
systemctl start docker

echo "✅ Basic setup completed!"
echo ""
echo "Next steps:"
echo "1. You'll need to upload your application code manually"
echo "2. Or provide a git repository URL to clone from"
echo "3. Then run the deployment script"
echo ""
echo "Would you like to:"
echo "A) Upload code files manually"
echo "B) Use git to clone from a repository"
echo "C) I'll provide the code via another method"