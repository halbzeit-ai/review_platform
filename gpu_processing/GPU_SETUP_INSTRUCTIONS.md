# GPU Instance Setup Instructions

## Prerequisites
- Fresh GPU instance with CUDA drivers installed
- Ubuntu 22.04 or 24.04
- Root access
- Internet connectivity

## Step-by-Step Setup

### 1. Initial System Setup
```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y curl python3 python3-pip nfs-common
```

### 2. Install Ollama
```bash
# Download and install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version

# Check if GPU is detected (should show GPU info, not CPU-only warning)
nvidia-smi
```

### 3. Mount Shared NFS Filesystem
```bash
# Create mount point
sudo mkdir -p /mnt/shared

# Mount the shared filesystem
sudo mount -t nfs -o nconnect=16 nfs.fin-01.datacrunch.io:/SFS-3H6ebwA1-b0cbae8b /mnt/shared

# Verify mount
df -h /mnt/shared
ls -la /mnt/shared

# Make mount persistent (optional)
echo "nfs.fin-01.datacrunch.io:/SFS-3H6ebwA1-b0cbae8b /mnt/shared nfs defaults,nconnect=16 0 0" | sudo tee -a /etc/fstab
```

### 4. Verify Ollama Service
```bash
# Check Ollama service status
sudo systemctl status ollama

# Start Ollama if not running
sudo systemctl start ollama
sudo systemctl enable ollama

# Test Ollama API
ollama list
```

### 5. Access Deployment Files via Shared Filesystem
```bash
# Navigate to the shared filesystem where deployment files are stored
cd /mnt/shared/gpu_processing_code

# Verify the required files are present
ls -la gpu_command_service.py gpu-command-service.service setup_gpu_service.sh
```

### 6. Deploy GPU Command Service
```bash
# Make setup script executable
chmod +x setup_gpu_service.sh

# Run the setup script (this will install files to /opt/gpu_processing/)
sudo ./setup_gpu_service.sh
```

### 7. Install AI Models (Optional)
```bash
# Pull required models for the platform
ollama pull phi4:latest
ollama pull gemma3:12b

# Verify models are installed
ollama list
```

### 8. Verify Complete Setup
```bash
# Check GPU service status
sudo systemctl status gpu-command-service

# Check service logs
sudo journalctl -f -u gpu-command-service

# Verify filesystem access
ls -la /mnt/shared/gpu_commands/
ls -la /mnt/shared/gpu_status/

# Test GPU detection
nvidia-smi
```

## Required Files

The setup requires these 3 files from the shared filesystem at `/mnt/shared/gpu_processing_code/`:

1. **gpu_command_service.py** - Main service script
2. **gpu-command-service.service** - Systemd service configuration
3. **setup_gpu_service.sh** - Installation script

## Directory Structure After Setup

```
/mnt/shared/                    # NFS mount point
├── gpu_processing_code/        # Deployment files location
│   ├── gpu_command_service.py  # Service script
│   ├── gpu-command-service.service # Service configuration
│   └── setup_gpu_service.sh    # Setup script
├── gpu_commands/               # Commands from production server
├── gpu_status/                 # Responses to production server
├── uploads/                    # PDF files for processing
├── results/                    # AI analysis results
└── temp/                       # Temporary processing files

/opt/gpu_processing/            # Final installation location (created by setup script)
├── gpu_command_service.py      # Installed by setup script

/etc/systemd/system/            # System service directory
├── gpu-command-service.service # Installed by setup script
```

## Service Management Commands

```bash
# Check service status
sudo systemctl status gpu-command-service

# View real-time logs
sudo journalctl -f -u gpu-command-service

# Restart service
sudo systemctl restart gpu-command-service

# Stop service
sudo systemctl stop gpu-command-service

# Start service
sudo systemctl start gpu-command-service
```

## Troubleshooting

### GPU Not Detected
```bash
# Check GPU hardware
lspci | grep -i nvidia
nvidia-smi

# Check CUDA installation
nvcc --version
ls /usr/local/cuda*/bin/

# Restart Ollama after GPU fixes
sudo systemctl restart ollama
```

### NFS Mount Issues
```bash
# Check if NFS is mounted
mountpoint -q /mnt/shared

# Remount if needed
sudo umount /mnt/shared
sudo mount -t nfs -o nconnect=16 nfs.fin-01.datacrunch.io:/SFS-3H6ebwA1-b0cbae8b /mnt/shared

# Check NFS connectivity
ping nfs.fin-01.datacrunch.io
```

### Service Issues
```bash
# Check service logs for errors
sudo journalctl -u gpu-command-service -n 50

# Check if Python dependencies are installed
python3 -c "import ollama; print('Ollama Python library OK')"

# Check file permissions
ls -la /opt/gpu_processing/gpu_command_service.py
```

## Expected Service Behavior

Once properly set up, the service will:
1. Monitor `/mnt/shared/gpu_commands/` every 5 seconds
2. Process command files (list_models, pull_model, delete_model)
3. Execute Ollama API calls
4. Write responses to `/mnt/shared/gpu_status/`
5. Log all activities to systemd journal

## Configuration Files

### Environment Variables (in service file)
- `PYTHONPATH=/opt/gpu_processing`
- `OLLAMA_HOST=127.0.0.1:11434`

### NFS Mount Details
- **Endpoint**: `nfs.fin-01.datacrunch.io:/SFS-3H6ebwA1-b0cbae8b`
- **Mount Point**: `/mnt/shared`
- **Options**: `nconnect=16` (for better performance)

## Security Notes

- Service runs as `root` user (required for system operations)
- NFS filesystem is shared between production and GPU instances
- All command/response files are in JSON format
- Service includes built-in command deduplication

## Next Steps

After successful setup:
1. The GPU instance is ready to receive commands from the production server
2. Test the communication by checking the web interface model management
3. Monitor logs during initial operations to ensure everything works correctly