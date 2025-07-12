"""
GPU Processing Service for on-demand AI analysis
"""
import asyncio
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from ..core.datacrunch import datacrunch_client
from ..core.volume_storage import volume_storage
from ..db.models import PitchDeck
from ..db.database import get_db
from ..core.config import settings

logger = logging.getLogger(__name__)

class GPUProcessingService:
    def __init__(self):
        self.gpu_instance_type = "1RTX6000ADA.10V"  # Correct GPU instance type from screenshot
        self.processing_timeout = 600  # 10 minutes timeout
        self.gpu_image = "ubuntu-22.04"  # Standard Ubuntu image for GPU instances
    
    async def trigger_processing(self, pitch_deck_id: int, file_path: str) -> bool:
        """
        Trigger GPU processing for a pitch deck
        1. Create GPU instance with shared volume
        2. Wait for instance to be ready
        3. Monitor processing completion
        4. Clean up instance
        """
        print(f"DEBUG: trigger_processing called for pitch_deck_id={pitch_deck_id}, file_path={file_path}")
        logger.info(f"ENTRY: trigger_processing called for pitch_deck_id={pitch_deck_id}, file_path={file_path}")
        
        try:
            print(f"DEBUG: Getting database session for pitch deck {pitch_deck_id}")
            logger.info(f"Getting database session for pitch deck {pitch_deck_id}")
            db = next(get_db())
            print(f"DEBUG: Database session obtained for pitch deck {pitch_deck_id}")
            logger.info(f"Database session obtained for pitch deck {pitch_deck_id}")
        except Exception as e:
            print(f"DEBUG: Failed to get database session: {e}")
            logger.error(f"Failed to get database session for pitch deck {pitch_deck_id}: {e}")
            return False
        
        try:
            # Update processing status
            print(f"DEBUG: Starting GPU processing for pitch deck {pitch_deck_id}")
            logger.info(f"Starting GPU processing for pitch deck {pitch_deck_id}")
            print(f"DEBUG: Querying database for pitch deck {pitch_deck_id}")
            pitch_deck = db.query(PitchDeck).filter(PitchDeck.id == pitch_deck_id).first()
            print(f"DEBUG: Database query completed for pitch deck {pitch_deck_id}")
            if not pitch_deck:
                print(f"DEBUG: Pitch deck {pitch_deck_id} not found!")
                logger.error(f"Pitch deck {pitch_deck_id} not found")
                return False
            
            print(f"DEBUG: Setting processing status to 'processing' for pitch deck {pitch_deck_id}")
            logger.info(f"Setting processing status to 'processing' for pitch deck {pitch_deck_id}")
            pitch_deck.processing_status = "processing"
            print(f"DEBUG: About to commit database changes for pitch deck {pitch_deck_id}")
            db.commit()
            print(f"DEBUG: Database commit completed for pitch deck {pitch_deck_id}")
            logger.info(f"Database updated for pitch deck {pitch_deck_id}")
            
            print(f"DEBUG: Creating processing marker for pitch deck {pitch_deck_id}")
            # Create processing marker
            volume_storage.create_processing_marker(file_path)
            print(f"DEBUG: Processing marker created for pitch deck {pitch_deck_id}")
            
            print(f"DEBUG: Checking for existing results file for pitch deck {pitch_deck_id}")
            # Clean up any existing results file to prevent reading stale data
            results_path = file_path.replace('/', '_').replace('.pdf', '_results.json')
            if volume_storage.file_exists(f"results/{results_path}"):
                print(f"DEBUG: Deleting existing results file for pitch deck {pitch_deck_id}")
                volume_storage.delete_file(f"results/{results_path}")
                logger.info(f"Cleaned up existing results file for pitch deck {pitch_deck_id}")
            print(f"DEBUG: Results cleanup completed for pitch deck {pitch_deck_id}")
            
            # Create startup script for GPU instance
            print(f"DEBUG: Creating startup script for pitch deck {pitch_deck_id}")
            logger.info(f"Creating startup script for pitch deck {pitch_deck_id}")
            startup_script_content = self._create_startup_script(file_path, pitch_deck_id)
            print(f"DEBUG: Startup script content created for pitch deck {pitch_deck_id}")
            
            # Step 1: Create startup script via API
            script_name = f"gpu-processing-{pitch_deck_id}"
            startup_script_data = await datacrunch_client.create_startup_script(
                name=script_name,
                script=startup_script_content
            )
            startup_script_id = startup_script_data["id"]
            print(f"DEBUG: Startup script created with ID: {startup_script_id}")
            logger.info(f"Created startup script {startup_script_id} for pitch deck {pitch_deck_id}")
            
            # Step 2: Create GPU instance with startup script ID
            instance_name = f"gpu-processor-{pitch_deck_id}"
            filesystem_id = settings.DATACRUNCH_SHARED_FILESYSTEM_ID
            
            print(f"DEBUG: Checking filesystem ID for pitch deck {pitch_deck_id}")
            if not filesystem_id:
                print(f"DEBUG: No filesystem ID configured!")
                raise Exception("DATACRUNCH_SHARED_FILESYSTEM_ID not configured")
            print(f"DEBUG: Filesystem ID OK: {filesystem_id}")
            
            # Get SSH key IDs for instance
            print(f"DEBUG: Getting SSH keys for pitch deck {pitch_deck_id}")
            ssh_key_ids = []
            if settings.DATACRUNCH_SSH_KEY_IDS:
                ssh_key_ids = [key.strip() for key in settings.DATACRUNCH_SSH_KEY_IDS.split(",") if key.strip()]
            print(f"DEBUG: SSH keys obtained: {len(ssh_key_ids)} keys")
            
            print(f"DEBUG: About to call datacrunch_client.deploy_instance for pitch deck {pitch_deck_id}")
            print(f"DEBUG: Instance config - hostname: {instance_name}, type: {self.gpu_instance_type}, image: {self.gpu_image}")
            print(f"DEBUG: SSH keys: {ssh_key_ids}, filesystem: {filesystem_id}")
            print(f"DEBUG: Startup script ID: {startup_script_id}")
            logger.info(f"Creating GPU instance {instance_name} for pitch deck {pitch_deck_id}")
            instance_data = await datacrunch_client.deploy_instance(
                hostname=instance_name,
                instance_type=self.gpu_instance_type,
                image=self.gpu_image,
                ssh_key_ids=ssh_key_ids,
                existing_volume_ids=[filesystem_id],
                startup_script_id=startup_script_id
            )
            print(f"DEBUG: datacrunch_client.deploy_instance returned for pitch deck {pitch_deck_id}")
            logger.info(f"GPU instance creation response received for pitch deck {pitch_deck_id}")
            
            instance_id = instance_data["id"]
            logger.info(f"Created GPU instance {instance_id} for pitch deck {pitch_deck_id}")
            
            # Wait for instance to be running
            logger.info(f"Waiting for GPU instance {instance_id} to start...")
            if not await datacrunch_client.wait_for_instance_running(instance_id, timeout=300):
                raise Exception("GPU instance failed to start within timeout")
            
            logger.info(f"GPU instance {instance_id} is running, starting processing monitor...")
            
            # Monitor processing completion with detailed logging
            processing_complete = await self._monitor_processing(file_path, instance_id)
            
            if processing_complete:
                # Verify results file exists before marking as completed
                results_path = file_path.replace('/', '_').replace('.pdf', '_results.json')
                if volume_storage.file_exists(f"results/{results_path}"):
                    pitch_deck.processing_status = "completed"
                    logger.info(f"Processing completed for pitch deck {pitch_deck_id}")
                else:
                    pitch_deck.processing_status = "failed"
                    logger.error(f"Processing completed but results file missing for pitch deck {pitch_deck_id}")
            else:
                pitch_deck.processing_status = "failed"
                logger.error(f"Processing failed for pitch deck {pitch_deck_id}")
            
            # Clean up instance and volumes
            await self._cleanup_instance(instance_id)
            volume_storage.remove_processing_marker(file_path)
            
            db.commit()
            return processing_complete
            
        except Exception as e:
            print(f"DEBUG EXCEPTION in trigger_processing: {e}")
            print(f"DEBUG Exception type: {type(e)}")
            import traceback
            print(f"DEBUG Full traceback: {traceback.format_exc()}")
            logger.error(f"GPU processing failed for pitch deck {pitch_deck_id}: {str(e)}")
            logger.error(f"Full error details: {traceback.format_exc()}")
            pitch_deck.processing_status = "failed"
            db.commit()
            volume_storage.remove_processing_marker(file_path)
            return False
        finally:
            db.close()
    
    def _create_startup_script(self, file_path: str, pitch_deck_id: int = None) -> str:
        """Create bash startup script for GPU instance"""
        mount_path = settings.SHARED_FILESYSTEM_MOUNT_PATH
        
        script = f"""#!/bin/bash
exec > /var/log/startup.log 2>&1
echo "AI PROCESSING: Starting at $(date)"
mkdir -p {mount_path}
echo "VOLUME MOUNT: Checking for attached volumes..."
lsblk

VOLUME_DEVICE=""
for device in /dev/sd* /dev/vd*; do
  if [ -b "$device" ] && [ "$device" != "/dev/sda" ] && [ "$device" != "/dev/sda1" ] && [ "$device" != "/dev/vda" ] && [ "$device" != "/dev/vda1" ] && [ "$device" != "/dev/vda2" ] && [ "$device" != "/dev/vda3" ]; then
    echo "VOLUME MOUNT: Found potential volume device: $device"
    VOLUME_DEVICE="$device"
    break
  fi
done

if [ -n "$VOLUME_DEVICE" ]; then
  echo "VOLUME MOUNT: Mounting volume $VOLUME_DEVICE to {mount_path}"
  mount "$VOLUME_DEVICE" {mount_path}
fi

if ! mountpoint -q {mount_path}; then
  echo "VOLUME MOUNT: Volume mount failed, trying NFS..."
  apt-get update && apt-get install -y nfs-common
  mount -t nfs -o nconnect=16 nfs.fin-01.datacrunch.io:/SFS-3H6ebwA1-b0cbae8b {mount_path}
fi

if mountpoint -q {mount_path}; then
  echo "MOUNT SUCCESS: Shared filesystem mounted"
  ls -la {mount_path}/
else
  echo "MOUNT FAILED: All methods failed"
  exit 1
fi

mkdir -p {mount_path}/results {mount_path}/temp

# Setup AI environment
echo "AI SETUP: Installing AI dependencies..."
apt update
apt install -y python3-pip poppler-utils
pip3 install Pillow pdf2image ollama tqdm

# Install and setup Ollama
echo "AI SETUP: Installing Ollama..."
curl -fsSL https://ollama.com/install.sh | sh
systemctl enable ollama
systemctl start ollama
sleep 10

# Set HOME environment for Ollama
export HOME=/root

# Pull AI models
echo "AI SETUP: Pulling AI models..."
ollama pull gemma3:12b
ollama pull phi4:latest

# Verify installation
echo "AI SETUP: Verifying installation..."
export HOME=/root
ollama list

# Use AI processing code from shared filesystem
echo "AI PROCESSING: Setting up processing code..."
mkdir -p /tmp/gpu_processing

# Copy from mounted volume (already deployed there)
if [ -d "{mount_path}/gpu_processing_code" ]; then
  echo "AI PROCESSING: Copying code from shared filesystem..."
  cp -r {mount_path}/gpu_processing_code/* /tmp/gpu_processing/
  echo "AI PROCESSING: Code copied successfully"
  ls -la /tmp/gpu_processing/
else
  echo "ERROR: No processing code found at {mount_path}/gpu_processing_code"
  ls -la {mount_path}/
  exit 1
fi

cd /tmp/gpu_processing

# Set environment variables
export SHARED_FILESYSTEM_MOUNT_PATH="{mount_path}"

# Run AI processing
echo "AI PROCESSING: Starting analysis for {file_path}..."
python3 main.py "{file_path}"

if [ $? -eq 0 ]; then
  echo "AI PROCESSING: Completed successfully"
else
  echo "AI PROCESSING: Failed with error code $?"
fi

echo "AI PROCESSING: Shutting down at $(date)"
shutdown -h now
"""
        
        return script
    
    async def _monitor_processing(self, file_path: str, instance_id: str) -> bool:
        """Monitor processing completion"""
        # Look for real AI processing completion marker
        marker_name = f"processing_complete_{file_path.replace('/', '_')}"
        completion_marker = f"temp/{marker_name}"
        
        logger.info(f"Monitoring AI processing, looking for marker: {completion_marker}")
        
        # Wait for completion marker or timeout (increase timeout for AI processing)
        ai_timeout = 1200  # 20 minutes for AI processing
        for i in range(ai_timeout):
            if volume_storage.file_exists(completion_marker):
                logger.info(f"AI processing completion marker found after {i} seconds")
                # Clean up completion marker
                volume_storage.delete_file(completion_marker)
                return True
            
            # Log progress every 30 seconds
            if i % 30 == 0 and i > 0:
                logger.info(f"Still waiting for AI processing completion... {i}/{ai_timeout} seconds elapsed")
                
                # Check if any results file exists yet
                results_path = file_path.replace('/', '_').replace('.pdf', '_results.json')
                if volume_storage.file_exists(f"results/{results_path}"):
                    logger.info(f"Results file already exists at results/{results_path}")
                else:
                    logger.info(f"No results file yet at results/{results_path}")
            
            # Check if instance is still running (handle API outages gracefully)
            try:
                instance = await datacrunch_client.get_instance(instance_id)
                status = instance.get("status", "").lower()
                if status in ["stopped", "error", "failed"]:
                    logger.warning(f"Instance {instance_id} stopped unexpectedly with status: {status}")
                    break
                elif i % 60 == 0 and i > 0:
                    logger.info(f"Instance {instance_id} status: {status}")
            except Exception as e:
                if "502" in str(e) or "Bad gateway" in str(e):
                    logger.info(f"Datacrunch API temporarily unavailable (502), continuing to monitor for results...")
                else:
                    logger.warning(f"Error checking instance status: {e}")
            
            await asyncio.sleep(1)
        
        logger.warning(f"AI processing timeout reached after {ai_timeout} seconds")
        return False
    
    async def _cleanup_instance(self, instance_id: str):
        """Clean up GPU instance and detach volumes"""
        try:
            # First, detach all volumes to prevent quota issues
            logger.info(f"Detaching volumes from instance {instance_id}")
            
            try:
                volumes = await datacrunch_client.get_instance_volumes(instance_id)
                for volume in volumes:
                    volume_id = volume.get("id")
                    if volume_id:
                        logger.info(f"Detaching volume {volume_id} from instance {instance_id}")
                        await datacrunch_client.detach_volume(volume_id)
            except Exception as volume_error:
                logger.warning(f"Error detaching volumes from instance {instance_id}: {volume_error}")
                # Continue with instance deletion even if volume detachment fails
            
            # Then delete the instance
            await datacrunch_client.delete_instance(instance_id)
            logger.info(f"Cleaned up GPU instance {instance_id}")
            
        except Exception as e:
            # Instance might have already shut down automatically
            if "404" in str(e) or "not_found" in str(e):
                logger.info(f"GPU instance {instance_id} already deleted (likely shut down automatically)")
            else:
                logger.error(f"Error cleaning up instance {instance_id}: {e}")

# Global service instance
gpu_processing_service = GPUProcessingService()