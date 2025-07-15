"""
File-Based GPU Processing Service
Uses shared filesystem for communication - no SSH required
"""

import json
import os
import time
import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import PitchDeck
from app.db.database import SessionLocal

logger = logging.getLogger(__name__)

class FileBasedGPUProcessingService:
    """Simple file-based processing using shared filesystem"""
    
    def __init__(self):
        self.shared_path = settings.SHARED_FILESYSTEM_MOUNT_PATH
        self.queue_path = os.path.join(self.shared_path, "queue")
        self.results_path = os.path.join(self.shared_path, "results")
        self.uploads_path = os.path.join(self.shared_path, "uploads")
        
        # Ensure directories exist
        os.makedirs(self.queue_path, exist_ok=True)
        os.makedirs(self.results_path, exist_ok=True)
        os.makedirs(self.uploads_path, exist_ok=True)
        
    async def process_pdf_direct(self, pitch_deck_id: int, file_path: str) -> Dict[str, Any]:
        """
        Process PDF using file-based communication
        
        Args:
            pitch_deck_id: Database ID of the pitch deck
            file_path: Path to PDF file in shared filesystem
            
        Returns:
            Processing results dictionary
        """
        logger.info(f"Starting file-based GPU processing for pitch deck {pitch_deck_id}")
        
        try:
            # Update database status
            self._update_processing_status(pitch_deck_id, "processing")
            
            # Create processing job file
            job_id = f"job_{pitch_deck_id}_{int(time.time())}"
            job_file = os.path.join(self.queue_path, f"{job_id}.json")
            
            job_data = {
                "job_id": job_id,
                "pitch_deck_id": pitch_deck_id,
                "file_path": file_path,
                "status": "queued",
                "created_at": time.time()
            }
            
            # Write job file
            with open(job_file, 'w') as f:
                json.dump(job_data, f, indent=2)
            
            logger.info(f"Created job file: {job_file}")
            
            # Wait for processing completion
            results = await self._wait_for_completion(job_id, pitch_deck_id)
            
            # Update database with results
            self._update_processing_status(pitch_deck_id, "completed", results)
            
            logger.info(f"File-based GPU processing completed for pitch deck {pitch_deck_id}")
            return results
            
        except Exception as e:
            logger.error(f"File-based GPU processing failed for pitch deck {pitch_deck_id}: {e}")
            self._update_processing_status(pitch_deck_id, "failed", {"error": str(e)})
            raise
            
    async def _wait_for_completion(self, job_id: str, pitch_deck_id: int, timeout: int = 900) -> Dict[str, Any]:
        """Wait for GPU processing to complete by monitoring result files"""
        
        result_file = os.path.join(self.results_path, f"{job_id}_results.json")
        start_time = time.time()
        
        logger.info(f"Waiting for result file: {result_file}")
        logger.info(f"Results directory: {self.results_path}")
        
        check_count = 0
        while time.time() - start_time < timeout:
            check_count += 1
            elapsed = time.time() - start_time
            
            # List all files in results directory every 10 checks for debugging
            if check_count % 10 == 0:
                try:
                    files = os.listdir(self.results_path)
                    result_files = [f for f in files if f.endswith('_results.json')]
                    logger.info(f"Check #{check_count} ({elapsed:.1f}s): Found {len(result_files)} result files: {result_files}")
                except Exception as e:
                    logger.error(f"Error listing results directory: {e}")
            
            if os.path.exists(result_file):
                try:
                    with open(result_file, 'r') as f:
                        results = json.load(f)
                    
                    logger.info(f"Found results for job {job_id} after {elapsed:.1f}s")
                    return results
                    
                except Exception as e:
                    logger.error(f"Error reading result file {result_file}: {e}")
                    
            # Check if job failed
            error_file = os.path.join(self.results_path, f"{job_id}_error.json")
            if os.path.exists(error_file):
                try:
                    with open(error_file, 'r') as f:
                        error_data = json.load(f)
                    raise Exception(f"GPU processing failed: {error_data.get('error', 'Unknown error')}")
                except json.JSONDecodeError:
                    raise Exception("GPU processing failed with unknown error")
            
            # Wait and check again
            await asyncio.sleep(5)
            
        # Final check - list all files before giving up
        try:
            files = os.listdir(self.results_path)
            result_files = [f for f in files if f.endswith('_results.json')]
            logger.error(f"Timeout after {timeout}s. Final check - result files: {result_files}")
        except Exception as e:
            logger.error(f"Error in final check: {e}")
            
        raise Exception(f"Processing timeout after {timeout} seconds")
        
    def _update_processing_status(self, pitch_deck_id: int, status: str, results: Optional[Dict[str, Any]] = None):
        """Update pitch deck processing status in database"""
        
        try:
            db = SessionLocal()
            
            pitch_deck = db.query(PitchDeck).filter(PitchDeck.id == pitch_deck_id).first()
            if not pitch_deck:
                logger.error(f"Pitch deck {pitch_deck_id} not found in database")
                db.close()
                return
            
            logger.info(f"Updating pitch deck {pitch_deck_id}: {pitch_deck.processing_status} -> {status}")
            
            # Update status
            pitch_deck.processing_status = status
            
            # Update results if provided
            if results:
                results_json = json.dumps(results)
                pitch_deck.ai_analysis_results = results_json
                logger.info(f"Added results to pitch deck {pitch_deck_id} ({len(results_json)} chars)")
            
            db.commit()
            db.close()
            
            logger.info(f"✅ Successfully updated pitch deck {pitch_deck_id} status to: {status}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update database for pitch deck {pitch_deck_id}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            try:
                db.close()
            except:
                pass
            
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
file_based_gpu_service = FileBasedGPUProcessingService()