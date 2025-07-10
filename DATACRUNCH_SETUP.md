# Datacrunch.io Setup Guide

This guide walks you through setting up the Datacrunch.io integration for on-demand GPU processing.

## Prerequisites

1. Datacrunch.io account with API access
2. Credits in your Datacrunch.io account

## Setup Steps

### 1. Get API Credentials

1. Log into your Datacrunch.io dashboard
2. Go to API section and create OAuth2 credentials
3. Note down your `client_id` and `client_secret`

### 2. Create Shared Volume

You can create a volume either via API or web interface:

**Via Web Interface:**
1. Go to Storage > Volumes in Datacrunch dashboard
2. Create new volume:
   - Name: `review-platform-shared`
   - Type: `NVMe_Shared`
   - Size: 100GB (adjust as needed)
3. Note down the volume ID

**Via API (using our client):**
```python
from app.core.datacrunch import datacrunch_client
import asyncio

async def create_volume():
    volume = await datacrunch_client.create_volume(
        name="review-platform-shared",
        size_gb=100,
        volume_type="NVMe_Shared"
    )
    print(f"Volume created: {volume['id']}")

asyncio.run(create_volume())
```

### 3. Configure Environment Variables

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
DATACRUNCH_CLIENT_ID=your_client_id_here
DATACRUNCH_CLIENT_SECRET=your_client_secret_here
DATACRUNCH_VOLUME_ID=your_volume_id_here
SHARED_VOLUME_MOUNT_PATH=/mnt/shared
```

### 4. Mount Volume on Your Instance

On your x86 web server instance, mount the shared volume:

```bash
# Create mount point
sudo mkdir -p /mnt/shared

# Mount the volume (replace with your volume device)
sudo mount /dev/disk/by-id/virtio-[your-volume-id] /mnt/shared

# Set permissions
sudo chown -R $USER:$USER /mnt/shared
sudo chmod -R 755 /mnt/shared

# Add to fstab for auto-mount on boot
echo "/dev/disk/by-id/virtio-[your-volume-id] /mnt/shared ext4 defaults 0 2" | sudo tee -a /etc/fstab
```

### 5. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 6. Test the Setup

```python
# Test volume storage
from app.core.volume_storage import volume_storage

# Check if volume is mounted
print(f"Volume mounted: {volume_storage.is_volume_mounted()}")

# Test API connection
from app.core.datacrunch import datacrunch_client
import asyncio

async def test_api():
    volumes = await datacrunch_client.get_volumes()
    print(f"Available volumes: {volumes}")

asyncio.run(test_api())
```

## How It Works

1. **File Upload**: PDFs are saved to `/mnt/shared/uploads/`
2. **GPU Trigger**: Background task creates GPU instance with the shared volume
3. **Processing**: GPU instance mounts same volume, processes PDF, saves results
4. **Cleanup**: GPU instance auto-shutdowns, results available in `/mnt/shared/results/`
5. **Access**: Web server can immediately access results

## Cost Optimization

- **Storage**: ~$0.20/GB/month for NVMe_Shared volume
- **GPU**: Only pay for processing time (~2 minutes per PDF)
- **Example**: 10 uploads/day × 2 min = 20 min/day ≈ 10 hours/month of GPU time

## Troubleshooting

### Volume Not Mounted
```bash
# Check available disks
lsblk

# Check mount status
df -h | grep mnt

# Manual mount
sudo mount /dev/[your-device] /mnt/shared
```

### API Authentication Issues
- Verify client_id and client_secret
- Check if credentials have proper permissions
- Test with simple API call

### GPU Instance Creation Fails
- Check available GPU types: `datacrunch_client.get_instance_types()`
- Verify sufficient credits
- Check volume attachment limits

## Security Notes

- Keep API credentials secure
- Use environment variables, never commit secrets
- Restrict volume access permissions
- Monitor API usage and costs