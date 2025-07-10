# Deploy to Existing Instance

Since you already have a CPU.4V.16G instance running with Ubuntu 24.04, here's how to deploy the Review Platform to it.

## Prerequisites

- ✅ Instance running (CPU.4V.16G, Ubuntu 24.04)
- ✅ SSH access to the instance
- ✅ Shared filesystem attached

## Step 1: Get Instance Details

Please provide:
- Instance public IP address
- SSH key for access
- Instance ID (for volume attachment)

## Step 2: Shared Filesystem Details

Since you already have a shared filesystem attached:
1. Note the **shared filesystem ID** (you'll need this for GPU instances)
2. Check where it's mounted (usually `/mnt/shared` or similar)
3. Verify you can read/write to it

## Step 3: Deploy Application

### Option A: Direct Upload (Recommended)

```bash
# From your local machine, upload the code
scp -r /home/ramin/halbzeit-ai/review_platform/* root@YOUR_INSTANCE_IP:/opt/review-platform/

# SSH to instance
ssh root@YOUR_INSTANCE_IP

# Make deployment script executable and run
cd /opt/review-platform
chmod +x deploy/deploy_app.sh
./deploy/deploy_app.sh
```

### Option B: Git Repository

If you've pushed to a git repository:

```bash
# SSH to instance
ssh root@YOUR_INSTANCE_IP

# Clone repository
git clone YOUR_REPO_URL /opt/review-platform
cd /opt/review-platform

# Run deployment
chmod +x deploy/deploy_app.sh
./deploy/deploy_app.sh
```

## Step 4: Configure Environment

```bash
# Edit configuration file
nano /opt/review-platform/backend/.env

# Update these values:
DATACRUNCH_CLIENT_ID=WGR1owy5MQJpDZDAJ9ahU
DATACRUNCH_CLIENT_SECRET=wFPRRj1GGnn4KI0oQ8Ysa1HGoDCwlwyH3MOrfQUv1y
DATACRUNCH_SHARED_FILESYSTEM_ID=your_shared_filesystem_id_here
SECRET_KEY=generate_a_long_random_string_here
SHARED_FILESYSTEM_MOUNT_PATH=/mnt/shared
```

## Step 5: Set up Shared Filesystem

```bash
# Check if shared filesystem is already mounted
df -h | grep shared
mount | grep shared

# If not mounted, check where Datacrunch mounts shared filesystems
ls /mnt/
ls /shared/

# Create symbolic link if needed (adjust path based on where it's mounted)
# Example: if mounted at /shared, link to /mnt/shared
ln -sf /path/to/shared/filesystem /mnt/shared

# Create required directories
mkdir -p /mnt/shared/{uploads,results,temp}
chown -R root:root /mnt/shared
chmod -R 755 /mnt/shared

# Test read/write access
echo "test" > /mnt/shared/test.txt && cat /mnt/shared/test.txt && rm /mnt/shared/test.txt
```

## Step 6: Start Services

```bash
# Restart services with new configuration
systemctl restart review-platform
systemctl restart nginx

# Check status
systemctl status review-platform
systemctl status nginx

# View logs if needed
journalctl -f -u review-platform
```

## Step 7: Test Application

1. Visit `http://YOUR_INSTANCE_IP`
2. Register as a startup user
3. Upload a test PDF
4. Check processing status

## Troubleshooting

### Check Service Status
```bash
systemctl status review-platform nginx
journalctl -u review-platform --no-pager -l
```

### Check Volume Mount
```bash
mountpoint /mnt/shared
ls -la /mnt/shared/
```

### Test API Manually
```bash
curl http://localhost:8000/api/
curl http://YOUR_INSTANCE_IP/api/
```

### Check Nginx Configuration
```bash
nginx -t
systemctl reload nginx
```

## Cost Optimization

- **Instance**: ~$0.50-1.00/hour for CPU.4V.16G
- **Volume**: ~$20/month for 100GB NVMe_Shared
- **GPU**: Only during processing (~2 min × $4/hour = ~$0.13 per PDF)

**Tip**: You can stop the instance when not in use to save costs!

## Next Steps After Deployment

1. Configure domain name (optional)
2. Set up SSL certificate (optional) 
3. Configure email notifications
4. Test GPU processing workflow
5. Monitor costs and usage