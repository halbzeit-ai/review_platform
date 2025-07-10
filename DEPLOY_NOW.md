# Deploy to Your Instance - Ready to Go!

Your instance details are configured. Here's how to deploy:

## Instance Details ✅
- **IP**: `65.108.32.168`
- **Instance ID**: `ca4223cd-a931-4989-8956-82356bf703dc`
- **Shared Filesystem ID**: `7cc261b3-b9ad-45be-8633-9f09c56a26c3`

## Step 1: Upload Code to Instance

```bash
# From your local machine, upload the code
scp -r /home/ramin/halbzeit-ai/review_platform/* root@65.108.32.168:/opt/review-platform/
```

## Step 2: SSH and Deploy

```bash
# SSH to your instance
ssh root@65.108.32.168

# Make deployment script executable and run
cd /opt/review-platform
chmod +x deploy/deploy_app.sh
./deploy/deploy_app.sh
```

## Step 3: Find and Set up Shared Filesystem

```bash
# Check where the shared filesystem is mounted
df -h | grep nfs
mount | grep nfs
ls /mnt/
ls /shared/

# Common NFS mount points on Datacrunch:
ls /mnt/nfs/
ls /shared/
ls /data/

# Once you find it, create a symlink to /mnt/shared
# Example (adjust path based on what you find):
ln -sf /actual/nfs/mount/path /mnt/shared

# Create required directories
mkdir -p /mnt/shared/{uploads,results,temp}
chmod -R 755 /mnt/shared

# Test read/write
echo "test" > /mnt/shared/test.txt && cat /mnt/shared/test.txt && rm /mnt/shared/test.txt
```

## Step 4: Generate Secret Key and Restart

```bash
# Generate a secure secret key
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Edit the .env file with the generated key
nano /opt/review-platform/backend/.env
# Update: SECRET_KEY=your_generated_key_here

# Restart services
systemctl restart review-platform
systemctl restart nginx

# Check status
systemctl status review-platform
systemctl status nginx
```

## Step 5: Test Application

Visit: **http://65.108.32.168**

1. Register as a startup user
2. Upload a test PDF
3. Check processing status

## Troubleshooting

### Check Logs
```bash
journalctl -f -u review-platform
tail -f /var/log/nginx/access.log
```

### Check Shared Filesystem
```bash
# Find all NFS mounts
mount | grep nfs
df -h | grep nfs

# Check if application can access filesystem
cd /opt/review-platform/backend
python3 -c "
from app.core.volume_storage import volume_storage
print(f'Filesystem mounted: {volume_storage.is_filesystem_mounted()}')
print(f'Mount path: {volume_storage.mount_path}')
"
```

### Manual Filesystem Setup
If auto-detection doesn't work:

```bash
# Check Datacrunch documentation for NFS mount commands
# Usually something like:
sudo mount -t nfs your-nfs-server:/path /mnt/shared

# Or check if it's already mounted elsewhere:
find /mnt /shared /data -name "*shared*" -type d 2>/dev/null
```

## Next Steps After Deployment

1. ✅ Test PDF upload
2. 🔄 Test GPU processing (once filesystem is working)
3. 🔧 Configure domain/SSL (optional)
4. 📊 Monitor costs and usage

## Cost Summary

- **Instance**: €0.02780/hour = ~€20/month (if running 24/7)
- **Shared Filesystem**: ~€10/month for 50GB
- **GPU Processing**: Only when needed (~€4/hour × 2 minutes = ~€0.13 per PDF)

**Total estimated cost for 10 PDFs/day: ~€35/month**