# Deployment Guide - Datacrunch.io

This guide walks you through deploying the Review Platform to Datacrunch.io.

## Prerequisites

1. Datacrunch.io account with API credentials
2. SSH key added to your Datacrunch account
3. Local environment with Python 3.11+

## Step 1: Configure API Credentials

Create a `.env` file in the backend directory:

```bash
cp backend/.env.example backend/.env
```

Add your Datacrunch credentials:
```
DATACRUNCH_CLIENT_ID=your_client_id
DATACRUNCH_CLIENT_SECRET=your_client_secret
```

## Step 2: Create Instance and Volume

Run the setup script:

```bash
cd deploy
python3 instance_setup.py
```

This will:
- ✅ Create an x86 web server instance 
- ✅ Create a shared NVMe volume
- ✅ Configure basic server setup
- 💾 Save instance details to `instance_config.txt`

## Step 3: Deploy Application

### Option A: Manual Upload
```bash
# Get instance IP from instance_config.txt
scp -r ../review_platform/* root@YOUR_INSTANCE_IP:/opt/review-platform/
ssh root@YOUR_INSTANCE_IP
cd /opt/review-platform
chmod +x deploy/deploy_app.sh
./deploy/deploy_app.sh
```

### Option B: Git Repository (Recommended)
1. Push your code to a Git repository
2. Update `REPO_URL` in `deploy_app.sh`
3. SSH to instance and run:
```bash
curl -L https://raw.githubusercontent.com/your-repo/review-platform/main/deploy/deploy_app.sh | bash
```

## Step 4: Mount Shared Volume

SSH to your instance:
```bash
ssh root@YOUR_INSTANCE_IP
```

Mount the shared volume:
```bash
# Find your volume device
lsblk

# Mount the volume (replace with your device)
mkdir -p /mnt/shared
mount /dev/disk/by-id/virtio-YOUR_VOLUME_ID /mnt/shared

# Create required directories
mkdir -p /mnt/shared/{uploads,results,temp}

# Add to fstab for auto-mount
echo "/dev/disk/by-id/virtio-YOUR_VOLUME_ID /mnt/shared ext4 defaults 0 2" >> /etc/fstab
```

## Step 5: Configure Environment

Edit the environment file:
```bash
nano /opt/review-platform/backend/.env
```

Required settings:
```
DATACRUNCH_CLIENT_ID=your_client_id
DATACRUNCH_CLIENT_SECRET=your_client_secret
DATACRUNCH_VOLUME_ID=your_volume_id
SHARED_VOLUME_MOUNT_PATH=/mnt/shared
SECRET_KEY=generate_a_secure_random_key
```

## Step 6: Start Services

```bash
systemctl restart review-platform
systemctl restart nginx
systemctl status review-platform
```

## Step 7: Test the Application

Visit your application:
- `http://YOUR_INSTANCE_IP`
- Register as a startup user
- Upload a test PDF
- Check processing status

## Monitoring

### View Logs
```bash
# API logs
journalctl -f -u review-platform

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Check Services
```bash
systemctl status review-platform
systemctl status nginx
```

### Volume Status
```bash
df -h /mnt/shared
ls -la /mnt/shared/
```

## Troubleshooting

### Service Won't Start
```bash
# Check detailed logs
journalctl -u review-platform --no-pager -l

# Check configuration
cd /opt/review-platform/backend
source ../venv/bin/activate
python -c "from app.core.config import settings; print('Config loaded')"
```

### Volume Issues
```bash
# Check if volume is mounted
mountpoint /mnt/shared

# Check available disks
lsblk

# Manual mount
mount /dev/disk/by-id/virtio-YOUR_VOLUME_ID /mnt/shared
```

### API Connection Issues
```bash
# Test Datacrunch API
cd /opt/review-platform/backend
source ../venv/bin/activate
python -c "
import asyncio
from app.core.datacrunch import datacrunch_client
async def test():
    token = await datacrunch_client.get_access_token()
    print(f'API connection successful: {token[:20]}...')
asyncio.run(test())
"
```

## Security Notes

- ✅ Change default SECRET_KEY
- ✅ Configure firewall if needed
- ✅ Keep API credentials secure
- ✅ Monitor costs and usage
- ✅ Regular backups of database

## Cost Monitoring

- **Instance**: ~$0.10/hour for 2xCPU.4GB
- **Volume**: ~$20/month for 100GB NVMe_Shared  
- **GPU**: Only when processing (~$1/hour × 2 minutes = ~$0.03 per PDF)

Total estimated cost for 10 PDFs/day: ~$95/month