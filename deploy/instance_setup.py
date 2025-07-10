#!/usr/bin/env python3
"""
Script to create and configure web server instance on Datacrunch.io
"""
import asyncio
import sys
import os
from dotenv import load_dotenv

# Load environment variables from backend/.env
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '../backend/.env')
load_dotenv(env_path)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.datacrunch import datacrunch_client

async def create_web_server_instance():
    """Create x86 web server instance"""
    
    # Instance configuration  
    hostname = "review-platform-web-server"
    instance_type = "ccc00000-a5d2-4972-ae4e-d429115d055b"  # CPU.4V.16G (AMD EPYC)
    image = "77edfb23-bb0d-41cc-a191-dccae45d96fd"  # Ubuntu 24.04 (no CUDA/Docker)
    description = "Review Platform Web Server"
    startup_script = """#!/bin/bash
# Update system
apt-get update -y
apt-get upgrade -y

# Install Python 3.11, Node.js, and required packages
apt-get install -y python3.11 python3.11-venv python3-pip git nginx curl

# Install Node.js for frontend
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt-get install -y nodejs

# Install Docker (for database if needed)
apt-get install -y docker.io
systemctl enable docker
systemctl start docker

# Create app directory
mkdir -p /opt/review-platform
cd /opt/review-platform

# Create systemd service file
cat > /etc/systemd/system/review-platform.service << 'EOF'
[Unit]
Description=Review Platform API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/review-platform/backend
Environment=PATH=/opt/review-platform/venv/bin
ExecStart=/opt/review-platform/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable service (will start after deployment)
systemctl enable review-platform

echo "Instance setup completed. Ready for application deployment."
"""
    
    try:
        print("Creating web server instance...")
        instance = await datacrunch_client.deploy_instance(
            hostname=hostname,
            instance_type=instance_type,
            image=image,
            description=description
        )
        
        instance_id = instance["id"]
        print(f"✅ Instance created successfully!")
        print(f"Instance ID: {instance_id}")
        print(f"Instance Name: {instance['name']}")
        
        # Wait for instance to be running
        print("⏳ Waiting for instance to be running...")
        if await datacrunch_client.wait_for_instance_running(instance_id, timeout=600):
            print("✅ Instance is now running!")
            
            # Get instance details
            instance_details = await datacrunch_client.get_instance(instance_id)
            print(f"Public IP: {instance_details.get('public_ip', 'Not available yet')}")
            print(f"Status: {instance_details.get('status')}")
            
            return instance_id, instance_details
        else:
            print("❌ Instance failed to start within timeout")
            return None, None
            
    except Exception as e:
        print(f"❌ Error creating instance: {e}")
        return None, None

async def create_shared_volume(instance_id: str):
    """Create shared volume and attach to web server"""
    try:
        print("Creating shared volume...")
        volume = await datacrunch_client.create_volume(
            name="review-platform-shared-volume",
            size_gb=100,
            volume_type="NVMe_Shared"
        )
        
        volume_id = volume["id"]
        print(f"✅ Volume created: {volume_id}")
        
        # Note: Volume attachment might need to be done via web interface or different API call
        print(f"📝 Please attach volume {volume_id} to instance {instance_id} via the web interface")
        print(f"   Or use the API to attach the volume")
        
        return volume_id
        
    except Exception as e:
        print(f"❌ Error creating volume: {e}")
        return None

async def main():
    """Main setup function"""
    print("🚀 Setting up Review Platform on Datacrunch.io")
    print("=" * 50)
    
    # Check API credentials
    try:
        await datacrunch_client.get_access_token()
        print("✅ API credentials are valid")
    except Exception as e:
        print(f"❌ API credentials invalid: {e}")
        print("Please check your DATACRUNCH_CLIENT_ID and DATACRUNCH_CLIENT_SECRET")
        return
    
    # Create web server instance
    instance_id, instance_details = await create_web_server_instance()
    if not instance_id:
        print("❌ Failed to create instance. Exiting.")
        return
    
    # Create shared volume
    volume_id = await create_shared_volume(instance_id)
    
    # Print next steps
    print("\n" + "=" * 50)
    print("🎉 Setup completed! Next steps:")
    print(f"1. SSH into your instance: ssh root@{instance_details.get('public_ip', 'YOUR_IP')}")
    if volume_id:
        print(f"2. Attach volume {volume_id} to instance {instance_id} (via web interface)")
        print(f"3. Mount volume: sudo mount /dev/disk/by-id/virtio-{volume_id} /mnt/shared")
    print("4. Deploy application using deploy_app.sh")
    print("5. Configure environment variables")
    
    # Save config for later use
    config = {
        "instance_id": instance_id,
        "volume_id": volume_id,
        "public_ip": instance_details.get('public_ip'),
        "instance_name": instance_details.get('name')
    }
    
    with open('instance_config.txt', 'w') as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    
    print("💾 Instance details saved to instance_config.txt")

if __name__ == "__main__":
    asyncio.run(main())