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
            startup_script = self._create_startup_script(file_path)
            print(f"DEBUG: Startup script created for pitch deck {pitch_deck_id}")
            
            # Create GPU instance
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
            print(f"DEBUG: Startup script length: {len(startup_script)} characters")
            logger.info(f"Creating GPU instance {instance_name} for pitch deck {pitch_deck_id}")
            instance_data = await datacrunch_client.deploy_instance(
                hostname=instance_name,
                instance_type=self.gpu_instance_type,
                image=self.gpu_image,
                ssh_key_ids=ssh_key_ids,
                existing_volume_ids=[filesystem_id],
                startup_script=startup_script
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
            
            # Clean up
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
    
    def _create_startup_script(self, file_path: str) -> str:
        """Create startup script for GPU instance"""
        mount_path = settings.SHARED_FILESYSTEM_MOUNT_PATH
        
        script = """#!/bin/bash
# Startup script with NFS mounting of shared filesystem
exec > /var/log/startup.log 2>&1

echo "NFS MOUNT: Starting at $(date)"

# Install NFS utilities if needed
apt-get update && apt-get install -y nfs-common

# Create mount point
mkdir -p {mount_path}

# Mount shared filesystem via NFS (from Datacrunch dashboard)
echo "NFS MOUNT: Mounting shared filesystem..."
mount -t nfs -o nconnect=16 nfs.fin-01.datacrunch.io:/SFS-3H6ebwA1-b0cbae8b {mount_path}

# Verify mount worked
if mountpoint -q {mount_path}; then
    echo "NFS MOUNT: Success! Shared filesystem mounted"
    ls -la {mount_path}/
else
    echo "NFS MOUNT: Failed to mount shared filesystem"
    exit 1
fi

# Create directories
mkdir -p {mount_path}/results {mount_path}/temp

# Create result file directly with bash (no Python dependencies)
cat > {mount_path}/results/test_result.json << 'EOL'
{{
  "nfs_test": true,
  "timestamp": "$(date)",
  "file_path": "{file_path}",
  "status": "success"
}}
EOL

# Create completion marker
touch {mount_path}/temp/processing_complete_test

echo "NFS MOUNT: Files created, shutting down..."
# Keep running for 2 minutes so we can SSH in and verify
sleep 120
shutdown -h now
"""
        # Replace placeholders
        script = script.replace("{mount_path}", mount_path)
        script = script.replace("{file_path}", file_path)
        
        return script
    
    async def _monitor_processing(self, file_path: str, instance_id: str) -> bool:
        """Monitor processing completion"""
        # Look for the simple test completion marker
        completion_marker = "temp/processing_complete_test"
        
        logger.info(f"Monitoring simple test processing, looking for marker: {completion_marker}")
        
        # Wait for completion marker or timeout
        for i in range(self.processing_timeout):
            if volume_storage.file_exists(completion_marker):
                logger.info(f"Simple test completion marker found after {i} seconds")
                # Clean up completion marker
                volume_storage.delete_file(completion_marker)
                return True
            
            # Log progress every 30 seconds
            if i % 30 == 0 and i > 0:
                logger.info(f"Still waiting for processing completion... {i}/{self.processing_timeout} seconds elapsed")
                
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
        
        logger.warning(f"Processing timeout reached after {self.processing_timeout} seconds")
        return False
    
    async def _cleanup_instance(self, instance_id: str):
        """Clean up GPU instance"""
        try:
            await datacrunch_client.delete_instance(instance_id)
            logger.info(f"Cleaned up GPU instance {instance_id}")
        except Exception as e:
            logger.error(f"Error cleaning up instance {instance_id}: {e}")

# Global service instance
gpu_processing_service = GPUProcessingService()