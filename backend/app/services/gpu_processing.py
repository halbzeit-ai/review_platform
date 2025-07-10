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
        self.gpu_instance_type = "1xA100.40GB"  # Default GPU instance type
        self.processing_timeout = 600  # 10 minutes timeout
    
    async def trigger_processing(self, pitch_deck_id: int, file_path: str) -> bool:
        """
        Trigger GPU processing for a pitch deck
        1. Create GPU instance with shared volume
        2. Wait for instance to be ready
        3. Monitor processing completion
        4. Clean up instance
        """
        db = next(get_db())
        
        try:
            # Update processing status
            pitch_deck = db.query(PitchDeck).filter(PitchDeck.id == pitch_deck_id).first()
            if not pitch_deck:
                logger.error(f"Pitch deck {pitch_deck_id} not found")
                return False
            
            pitch_deck.processing_status = "processing"
            db.commit()
            
            # Create processing marker
            volume_storage.create_processing_marker(file_path)
            
            # Create startup script for GPU instance
            startup_script = self._create_startup_script(file_path)
            
            # Create GPU instance
            instance_name = f"gpu-processor-{pitch_deck_id}"
            filesystem_id = settings.DATACRUNCH_SHARED_FILESYSTEM_ID
            
            if not filesystem_id:
                raise Exception("DATACRUNCH_SHARED_FILESYSTEM_ID not configured")
            
            instance_data = await datacrunch_client.deploy_instance(
                hostname=instance_name,
                instance_type=self.gpu_instance_type,
                existing_volume_ids=[filesystem_id],
                startup_script=startup_script
            )
            
            instance_id = instance_data["id"]
            logger.info(f"Created GPU instance {instance_id} for pitch deck {pitch_deck_id}")
            
            # Wait for instance to be running
            if not await datacrunch_client.wait_for_instance_running(instance_id, timeout=300):
                raise Exception("GPU instance failed to start within timeout")
            
            # Monitor processing completion
            processing_complete = await self._monitor_processing(file_path, instance_id)
            
            if processing_complete:
                pitch_deck.processing_status = "completed"
                logger.info(f"Processing completed for pitch deck {pitch_deck_id}")
            else:
                pitch_deck.processing_status = "failed"
                logger.error(f"Processing failed for pitch deck {pitch_deck_id}")
            
            # Clean up
            await self._cleanup_instance(instance_id)
            volume_storage.remove_processing_marker(file_path)
            
            db.commit()
            return processing_complete
            
        except Exception as e:
            logger.error(f"GPU processing failed for pitch deck {pitch_deck_id}: {str(e)}")
            pitch_deck.processing_status = "failed"
            db.commit()
            volume_storage.remove_processing_marker(file_path)
            return False
        finally:
            db.close()
    
    def _create_startup_script(self, file_path: str) -> str:
        """Create startup script for GPU instance"""
        mount_path = settings.SHARED_FILESYSTEM_MOUNT_PATH
        
        script = f"""#!/bin/bash
# Mount shared filesystem (auto-mounted on Datacrunch instances with shared filesystem)
mkdir -p {mount_path}
# Shared filesystem should be auto-mounted, but ensure directory exists

# Install dependencies
apt-get update
apt-get install -y python3-pip

# Install your AI processing dependencies
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip3 install transformers pypdf2 opencv-python

# Create processing script
cat > /root/process_pdf.py << 'EOF'
import sys
import json
import os
from pathlib import Path

def process_pdf(file_path):
    # TODO: Implement your AI processing logic here
    # This is a placeholder that creates fake results
    
    print(f"Processing PDF: {{file_path}}")
    
    # Simulate processing time
    import time
    time.sleep(30)  # Simulate 30 seconds of processing
    
    # Create fake results
    results = {{
        "summary": "This is a placeholder summary of the pitch deck",
        "key_points": [
            "Strong market opportunity",
            "Experienced team",
            "Clear business model"
        ],
        "score": 8.5,
        "recommendations": [
            "Focus on customer acquisition",
            "Develop partnerships",
            "Expand market reach"
        ]
    }}
    
    return results

if __name__ == "__main__":
    input_file = "{mount_path}/{file_path}"
    
    if not os.path.exists(input_file):
        print(f"Error: File {{input_file}} not found")
        sys.exit(1)
    
    try:
        results = process_pdf(input_file)
        
        # Save results
        results_file = input_file.replace('uploads/', 'results/').replace('.pdf', '_results.json')
        results_dir = os.path.dirname(results_file)
        os.makedirs(results_dir, exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to: {{results_file}}")
        
        # Create completion marker
        completion_marker = "{mount_path}/temp/processing_complete_{file_path.replace('/', '_')}"
        Path(completion_marker).touch()
        
    except Exception as e:
        print(f"Error processing PDF: {{e}}")
        sys.exit(1)
EOF

# Run processing
python3 /root/process_pdf.py

# Auto-shutdown after processing
shutdown -h now
"""
        return script
    
    async def _monitor_processing(self, file_path: str, instance_id: str) -> bool:
        """Monitor processing completion"""
        completion_marker = f"temp/processing_complete_{file_path.replace('/', '_')}"
        
        # Wait for completion marker or timeout
        for i in range(self.processing_timeout):
            if volume_storage.file_exists(completion_marker):
                # Clean up completion marker
                volume_storage.delete_file(completion_marker)
                return True
            
            # Check if instance is still running
            try:
                instance = await datacrunch_client.get_instance(instance_id)
                if instance.get("status", "").lower() in ["stopped", "error", "failed"]:
                    logger.warning(f"Instance {instance_id} stopped unexpectedly")
                    break
            except Exception as e:
                logger.warning(f"Error checking instance status: {e}")
            
            await asyncio.sleep(1)
        
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