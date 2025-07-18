"""
Direct GPU Processing Service (Lean Implementation)
No hibernation - direct SSH processing on persistent GPU instance
"""

import json
import os
import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import paramiko
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import PitchDeck
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)

class DirectGPUProcessingService:
    """Lean service for direct GPU processing without hibernation"""
    
    def __init__(self):
        self.gpu_host = settings.GPU_INSTANCE_HOST
        self.gpu_user = settings.GPU_INSTANCE_USER
        self.gpu_key_path = settings.GPU_INSTANCE_SSH_KEY_PATH
        self.shared_path = settings.SHARED_FILESYSTEM_MOUNT_PATH
        
    def _get_ssh_client(self) -> paramiko.SSHClient:
        """Create SSH client for GPU instance"""
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # Use SSH key authentication
        client.connect(
            hostname=self.gpu_host,
            username=self.gpu_user,
            key_filename=self.gpu_key_path,
            timeout=30
        )
        
        return client
        
    async def process_pdf_direct(self, pitch_deck_id: int, file_path: str) -> Dict[str, Any]:
        """
        Process PDF directly on GPU instance
        
        Args:
            pitch_deck_id: Database ID of the pitch deck
            file_path: Path to PDF file in shared filesystem
            
        Returns:
            Processing results dictionary
        """
        logger.info(f"Starting direct GPU processing for pitch deck {pitch_deck_id}")
        
        try:
            # Update database status
            self._update_processing_status(pitch_deck_id, "processing")
            
            # Execute processing on GPU via SSH
            results = await self._execute_remote_processing(file_path)
            
            # Update database with results
            self._update_processing_status(pitch_deck_id, "completed", results)
            
            logger.info(f"Direct GPU processing completed for pitch deck {pitch_deck_id}")
            return results
            
        except Exception as e:
            logger.error(f"Direct GPU processing failed for pitch deck {pitch_deck_id}: {e}")
            self._update_processing_status(pitch_deck_id, "failed", {"error": str(e)})
            raise
            
    async def _execute_remote_processing(self, file_path: str) -> Dict[str, Any]:
        """Execute processing command on GPU instance via SSH"""
        
        # Command to run on GPU instance
        processing_command = f"""
        cd {self.shared_path}/gpu_processing && \
        python3 main.py {file_path}
        """
        
        try:
            # Execute command via SSH
            client = self._get_ssh_client()
            
            logger.info(f"Executing processing command: {processing_command}")
            stdin, stdout, stderr = client.exec_command(processing_command)
            
            # Wait for completion
            exit_status = stdout.channel.recv_exit_status()
            
            if exit_status != 0:
                error_output = stderr.read().decode()
                raise Exception(f"Processing command failed with exit code {exit_status}: {error_output}")
            
            # Processing completed successfully, read results
            results = self._read_processing_results(file_path)
            
            client.close()
            return results
            
        except Exception as e:
            logger.error(f"Remote processing execution failed: {e}")
            raise
            
    def _read_processing_results(self, file_path: str) -> Dict[str, Any]:
        """Read processing results from shared filesystem"""
        
        # Calculate expected results file path
        flat_filename = file_path.replace('/', '_').replace('.pdf', '_results.json')
        results_path = os.path.join(self.shared_path, 'results', flat_filename)
        
        if not os.path.exists(results_path):
            raise FileNotFoundError(f"Results file not found: {results_path}")
        
        try:
            with open(results_path, 'r') as f:
                results = json.load(f)
            
            logger.info(f"Successfully read results from: {results_path}")
            return results
            
        except Exception as e:
            logger.error(f"Failed to read results file {results_path}: {e}")
            raise
            
    def _update_processing_status(self, pitch_deck_id: int, status: str, results: Optional[Dict[str, Any]] = None):
        """Update pitch deck processing status in database"""
        
        try:
            db = SessionLocal()
            
            pitch_deck = db.query(PitchDeck).filter(PitchDeck.id == pitch_deck_id).first()
            if not pitch_deck:
                logger.error(f"Pitch deck {pitch_deck_id} not found in database")
                return
            
            # Update status
            pitch_deck.processing_status = status
            
            # Update results if provided
            if results:
                pitch_deck.ai_analysis_results = json.dumps(results)
                
                # Extract and store the startup name if available
                startup_name = results.get("startup_name")
                if startup_name:
                    pitch_deck.ai_extracted_startup_name = startup_name
                    logger.info(f"Extracted startup name: {startup_name}")
            
            db.commit()
            db.close()
            
            logger.info(f"Updated pitch deck {pitch_deck_id} status to: {status}")
            
        except Exception as e:
            logger.error(f"Failed to update database for pitch deck {pitch_deck_id}: {e}")
            
    async def get_processing_status(self, pitch_deck_id: int) -> Dict[str, Any]:
        """Get current processing status for a pitch deck"""
        
        try:
            db = SessionLocal()
            
            pitch_deck = db.query(PitchDeck).filter(PitchDeck.id == pitch_deck_id).first()
            if not pitch_deck:
                return {"error": "Pitch deck not found"}
            
            result = {
                "id": pitch_deck.id,
                "status": pitch_deck.processing_status,
                "file_name": pitch_deck.file_name,
                "created_at": pitch_deck.created_at.isoformat() if pitch_deck.created_at else None
            }
            
            # Include results if processing completed
            if pitch_deck.processing_status == "completed" and pitch_deck.ai_analysis_results:
                try:
                    result["results"] = json.loads(pitch_deck.ai_analysis_results)
                except json.JSONDecodeError:
                    result["results"] = {"error": "Failed to parse results"}
            
            db.close()
            return result
            
        except Exception as e:
            logger.error(f"Failed to get processing status for pitch deck {pitch_deck_id}: {e}")
            return {"error": str(e)}

# Global instance
direct_gpu_service = DirectGPUProcessingService()