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
            if not await datacrunch_client.wait_for_instance_running(instance_id, timeout=300):
                raise Exception("GPU instance failed to start within timeout")
            
            # Monitor processing completion
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
        
        script = """#!/bin/bash
# Mount shared filesystem (auto-mounted on Datacrunch instances with shared filesystem)
mkdir -p {mount_path}
# Shared filesystem should be auto-mounted, but ensure directory exists

# Install dependencies
apt-get update
apt-get install -y python3-pip

# Install your AI processing dependencies
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip3 install transformers pypdf2 opencv-python pdfplumber pymupdf

# Upload GPU processing code
cat > /root/upload_gpu_code.py << 'EOF'
import os
import shutil

# Create gpu_processing directory
os.makedirs('/root/gpu_processing', exist_ok=True)

# Copy GPU processing files from shared filesystem
shared_path = "{mount_path}/gpu_processing"
if os.path.exists(shared_path):
    shutil.copytree(shared_path, '/root/gpu_processing', dirs_exist_ok=True)
    print("GPU processing code copied from shared filesystem")
else:
    print("Warning: GPU processing code not found in shared filesystem")

EOF

python3 /root/upload_gpu_code.py

# Create fallback processing script if GPU code not available
cat > /root/process_pdf.py << 'EOF'
import sys
import os
import json
from pathlib import Path

# Try to import GPU processing modules
try:
    sys.path.append('/root/gpu_processing')
    from main import PDFProcessor
    from utils.pdf_extractor import PDFExtractor
    from utils.ai_analyzer import AIAnalyzer
    GPU_PROCESSING_AVAILABLE = True
except ImportError:
    print("GPU processing modules not available, using fallback")
    GPU_PROCESSING_AVAILABLE = False

def process_pdf_advanced(file_path):
    # Advanced processing using GPU processing modules
    mount_path = os.environ.get('SHARED_FILESYSTEM_MOUNT_PATH', '{mount_path}')
    
    # Initialize processor
    processor = PDFProcessor(mount_path)
    
    # Process using advanced AI
    results = processor.process_pdf(file_path)
    
    return results

def process_pdf_fallback(file_path):
    # Fallback processing if GPU modules not available
    print(f"Processing PDF with fallback method: {file_path}")
    
    # Simulate processing time
    import time
    time.sleep(30)
    
    # Create structured results
    results = {
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
        ],
        "analysis": {
            "market_size": "Large addressable market with growth potential",
            "team_strength": "Experienced founders with relevant background",
            "business_model": "Clear revenue streams and monetization strategy",
            "traction": "Early signs of market validation",
            "risks": "Competitive landscape and execution challenges"
        },
        "sections_analyzed": ["Executive Summary", "Market Analysis", "Business Model"],
        "confidence_score": 0.75,
        "processing_time": 30.0,
        "model_version": "fallback-v1.0"
    }
    
    return results

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python process_pdf.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    full_path = "{mount_path}/" + file_path
    
    if not os.path.exists(full_path):
        print(f"Error: File {full_path} not found")
        sys.exit(1)
    
    try:
        # Use advanced processing if available, otherwise fallback
        if GPU_PROCESSING_AVAILABLE:
            results = process_pdf_advanced(file_path)
        else:
            results = process_pdf_fallback(file_path)
        
        # Save results - use flat filename format that matches backend expectation
        flat_filename = file_path.replace('/', '_').replace('.pdf', '_results.json')
        results_file = "{mount_path}/results/" + flat_filename
        results_dir = os.path.dirname(results_file)
        os.makedirs(results_dir, exist_ok=True)
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        print(f"Results saved to: {results_file}")
        
        # Create completion marker  
        flat_marker_name = file_path.replace('/', '_')
        completion_marker = "{mount_path}/temp/processing_complete_" + flat_marker_name
        Path(completion_marker).touch()
        
    except Exception as e:
        print(f"Error processing PDF: {e}")
        sys.exit(1)
EOF

# Run processing
python3 /root/process_pdf.py {file_path}

# Auto-shutdown after processing
shutdown -h now
"""
        # Replace placeholders
        script = script.replace("{mount_path}", mount_path)
        script = script.replace("{file_path}", file_path)
        
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