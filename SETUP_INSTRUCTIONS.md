# Quick Setup Instructions

Since the automated instance creation requires SSH keys, here's a simplified setup approach:

## Step 1: Manual Setup via Datacrunch Web Interface

1. **Add SSH Key**:
   - Go to Datacrunch.io dashboard
   - Add your SSH public key in the SSH Keys section
   - Note down the key ID

2. **Create Instance Manually**:
   - Create a new instance with these settings:
     - **Instance Type**: Any available (B200, H100, etc.)
     - **Image**: Ubuntu 24.04 + CUDA 12.8 + Docker
     - **Hostname**: review-platform-web-server
     - **SSH Key**: Your uploaded key

3. **Create Shared Volume**:
   - Go to Storage > Volumes
   - Create new volume:
     - **Type**: NVMe_Shared  
     - **Size**: 100GB
     - **Name**: review-platform-shared
   - **Attach volume to your instance**

## Step 2: Deploy Application

Once your instance is running:

```bash
# SSH to your instance
ssh root@YOUR_INSTANCE_IP

# Download deployment script
curl -L https://raw.githubusercontent.com/your-repo/review-platform/main/deploy/deploy_app.sh -o deploy_app.sh
chmod +x deploy_app.sh

# Run deployment
./deploy_app.sh
```

## Step 3: Configure Environment

```bash
# Edit configuration
nano /opt/review-platform/backend/.env

# Add your credentials:
DATACRUNCH_CLIENT_ID=your_client_id
DATACRUNCH_CLIENT_SECRET=your_client_secret  
DATACRUNCH_VOLUME_ID=your_volume_id
SECRET_KEY=generate_a_secure_key

# Restart service
systemctl restart review-platform
```

## Step 4: Mount Shared Volume

```bash
# Find your volume device
lsblk

# Mount the volume (replace with your device)
mkdir -p /mnt/shared
mount /dev/disk/by-id/virtio-YOUR_VOLUME_ID /mnt/shared

# Create directories
mkdir -p /mnt/shared/{uploads,results,temp}

# Add to fstab for auto-mount
echo "/dev/disk/by-id/virtio-YOUR_VOLUME_ID /mnt/shared ext4 defaults 0 2" >> /etc/fstab
```

## Step 5: Test

Visit `http://YOUR_INSTANCE_IP` and test the upload functionality!

## Cost Estimates

- **Instance**: $4.49/hour for B200 (you can stop it when not in use)
- **Storage**: ~$20/month for 100GB shared volume
- **GPU Processing**: Only when processing PDFs (~2 minutes per upload)

**Tip**: Stop your instance when not actively developing to save costs!