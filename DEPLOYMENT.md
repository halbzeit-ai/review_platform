# Deployment Guide

Production-ready deployment guide for the Review Platform to Datacrunch.io infrastructure.

## Prerequisites

- Datacrunch.io account with API credentials
- SSH access to instance
- Local environment with Python 3.11+ and Node.js

## Current Production Configuration

**Instance Details (Working):**
- IP: `65.108.32.168`
- Instance ID: `ca4223cd-a931-4989-8956-82356bf703dc`
- Shared Filesystem ID: `7cc261b3-b9ad-45be-8633-9f09c56a26c3`
- NFS Mount: `nfs.fin-01.datacrunch.io:/SFS-5gkKcxHe-6721608d`

## Quick Deploy to Existing Instance

### 1. Upload Code
```bash
# From local machine
scp -r /home/ramin/halbzeit-ai/review_platform/* root@65.108.32.168:/opt/review-platform/
```

### 2. Deploy Application
```bash
# SSH to instance
ssh root@65.108.32.168

# Run deployment script
cd /opt/review-platform
chmod +x deploy/deploy_app.sh
./deploy/deploy_app.sh
```

### 3. Configure Environment
```bash
# Edit configuration
nano /opt/review-platform/backend/.env

# Required settings:
DATACRUNCH_CLIENT_ID=WGR1owy5MQJpDZDAJ9ahU
DATACRUNCH_CLIENT_SECRET=wFPRRj1GGnn4KI0oQ8Ysa1HGoDCwlwyH3MOrfQUv1y
DATACRUNCH_SHARED_FILESYSTEM_ID=7cc261b3-b9ad-45be-8633-9f09c56a26c3
SHARED_FILESYSTEM_MOUNT_PATH=/mnt/shared
SECRET_KEY=generate_a_secure_random_key

# Generate secure secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. Set up Shared Filesystem
```bash
# Check NFS mount
mount | grep nfs
df -h | grep nfs

# Create symlink to standard path
ln -sf /actual/nfs/mount/path /mnt/shared

# Create required directories
mkdir -p /mnt/shared/{uploads,results,temp}
chmod -R 755 /mnt/shared

# Test filesystem access
echo "test" > /mnt/shared/test.txt && cat /mnt/shared/test.txt && rm /mnt/shared/test.txt
```

### 5. Start Services
```bash
# Restart services
systemctl restart review-platform
systemctl restart nginx

# Verify status
systemctl status review-platform
systemctl status nginx
```

### 6. Test Application
Visit: **http://65.108.32.168**
1. Register as startup user
2. Upload test PDF (up to 50MB)
3. Check processing status

## Fresh Instance Setup

### 1. Configure API Credentials
```bash
# Create environment file
cp backend/.env.example backend/.env

# Add credentials
DATACRUNCH_CLIENT_ID=your_client_id
DATACRUNCH_CLIENT_SECRET=your_client_secret
```

### 2. Create Infrastructure
```bash
# Run setup script
cd deploy
python3 instance_setup.py

# This creates:
# - x86 web server instance
# - Shared NVMe volume
# - Basic server configuration
# - Saves details to instance_config.txt
```

### 3. Mount Shared Volume
```bash
# SSH to new instance
ssh root@YOUR_INSTANCE_IP

# Find volume device
lsblk

# Mount volume
mkdir -p /mnt/shared
mount /dev/disk/by-id/virtio-YOUR_VOLUME_ID /mnt/shared

# Create directories
mkdir -p /mnt/shared/{uploads,results,temp}

# Auto-mount on boot
echo "/dev/disk/by-id/virtio-YOUR_VOLUME_ID /mnt/shared ext4 defaults 0 2" >> /etc/fstab
```

## Production Architecture

### Service Configuration
- **Backend API**: Port 8000 (systemd service: `review-platform`)
- **Nginx Proxy**: Port 80 (frontend + `/api` routing)
- **Database**: SQLite with proper schema
- **File Storage**: NFS shared filesystem

### Key Features Working
- ✅ User registration/login (startup/GP roles)
- ✅ PDF upload validation (50MB limit)
- ✅ Dashboard navigation
- ✅ Centralized API communication
- ✅ Proper error handling

### Nginx Configuration
```nginx
# Key settings for file uploads
client_max_body_size 50M;
proxy_connect_timeout 600s;
proxy_send_timeout 600s;
proxy_read_timeout 600s;
```

## Monitoring & Troubleshooting

### Check Service Status
```bash
# View service status
systemctl status review-platform nginx

# Real-time logs
journalctl -f -u review-platform
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### Database Issues
```bash
# Check database schema
cd /opt/review-platform/backend
python3 -c "
from app.db.database import engine
from sqlalchemy import inspect
inspector = inspect(engine)
print('Tables:', inspector.get_table_names())
"

# Run migration if needed
python3 migrate_db.py
```

### Filesystem Issues
```bash
# Check mount status
mountpoint /mnt/shared
df -h /mnt/shared

# Test application filesystem access
cd /opt/review-platform/backend
python3 -c "
from app.core.volume_storage import volume_storage
print(f'Filesystem mounted: {volume_storage.is_filesystem_mounted()}')
print(f'Mount path: {volume_storage.mount_path}')
"
```

### API Connection Test
```bash
# Test backend API
curl http://localhost:8000/api/
curl http://YOUR_INSTANCE_IP/api/

# Test Datacrunch API
cd /opt/review-platform/backend
python3 -c "
import asyncio
from app.core.datacrunch import datacrunch_client
async def test():
    token = await datacrunch_client.get_access_token()
    print(f'API connection successful: {token[:20]}...')
asyncio.run(test())
"
```

## Deployment Scripts

### Quick Fix Scripts
```bash
# Database schema fix
./scripts/fix_database.sh

# Upload size limit fix
./scripts/fix_upload_size.sh

# Initial server setup
./scripts/remote_setup.sh

# Sync GPU processing code
./scripts/sync_gpu_code.sh

# Full service restart
systemctl restart review-platform nginx
```

### Code Updates
```bash
# Update deployed code
cd /opt/review-platform
git pull origin main
cd frontend && NODE_ENV=production npm run build
systemctl restart review-platform
```

## Cost Optimization

### Instance Costs
- **CPU.4V.16G**: ~€0.50-1.00/hour (€360-720/month 24/7)
- **Shared Filesystem**: ~€10-20/month for 50-100GB
- **GPU Processing**: ~€4/hour × 2 minutes = ~€0.13 per PDF

### Optimization Tips
- Stop instance when not in use
- Use on-demand GPU instances only for processing
- Monitor usage with Datacrunch dashboard
- Regular database cleanup

**Estimated cost for 10 PDFs/day: €35-50/month**

## Security Best Practices

- ✅ Change default SECRET_KEY
- ✅ Configure firewall rules
- ✅ Keep API credentials secure
- ✅ Regular backups of database
- ✅ Monitor access logs
- ✅ SSL certificate for production domain

## Next Steps

1. **AI Processing**: Configure GPU workflow
2. **Email Notifications**: Set up SMTP service
3. **Domain Setup**: Configure custom domain + SSL
4. **Monitoring**: Set up alerts and usage tracking
5. **Backup Strategy**: Automated database backups

## Troubleshooting Common Issues

### "No such column: pitch_decks.file_path"
```bash
cd /opt/review-platform
./scripts/fix_database.sh
```

### "413 Request Entity Too Large"
```bash
cd /opt/review-platform
./scripts/fix_upload_size.sh
```

### "502 Bad Gateway"
```bash
# Check backend service
systemctl status review-platform
journalctl -u review-platform --no-pager -l
```

### Frontend API Connection Issues
```bash
# Verify API base URL configuration
cd /opt/review-platform/frontend/src
grep -r "baseURL\|0.0.0.0" .
```

This deployment guide represents production-tested best practices from successful deployments.