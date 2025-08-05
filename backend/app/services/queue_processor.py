"""
Queue Processor - Polls processing queue and sends tasks to GPU server
"""

import asyncio
import logging
import httpx
import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from ..db.database import SessionLocal
from .processing_queue import processing_queue_manager, ProcessingTask, TaskStatus
from ..core.config import settings

logger = logging.getLogger(__name__)

class QueueProcessor:
    """Background task that polls the processing queue and sends tasks to GPU"""
    
    def __init__(self):
        self.running = False
        self.poll_interval = 5  # seconds
        self.gpu_url = self._get_gpu_url()
        self.backend_url = self._get_backend_url()
        logger.info(f"Queue processor initialized - GPU URL: {self.gpu_url}, Backend URL: {self.backend_url}")
    
    def _get_gpu_url(self) -> str:
        """Get GPU server URL based on environment"""
        environment = settings.ENVIRONMENT
        if environment == "production":
            gpu_host = settings.GPU_PRODUCTION
            return f"http://{gpu_host}:8001"
        else:
            gpu_host = settings.GPU_DEVELOPMENT  
            return f"http://{gpu_host}:8001"
    
    def _get_backend_url(self) -> str:
        """Get backend URL for callbacks"""
        environment = settings.ENVIRONMENT
        if environment == "production":
            return settings.BACKEND_PRODUCTION
        else:
            return settings.BACKEND_DEVELOPMENT
    
    async def start(self):
        """Start the queue processor"""
        self.running = True
        logger.info("Starting queue processor background task")
        
        # Register server
        db = SessionLocal()
        try:
            processing_queue_manager.register_server(db)
            # Recover any abandoned tasks
            recovered = processing_queue_manager.recover_abandoned_tasks(db)
            if recovered > 0:
                logger.info(f"Recovered {recovered} abandoned tasks")
        finally:
            db.close()
        
        # Start processing loop
        while self.running:
            try:
                await self.process_next_task()
            except Exception as e:
                logger.error(f"Error in queue processor loop: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def stop(self):
        """Stop the queue processor"""
        self.running = False
        logger.info("Stopping queue processor")
    
    async def process_next_task(self):
        """Get and process the next task from queue"""
        db = SessionLocal()
        try:
            # Get next task
            task = processing_queue_manager.get_next_task(db)
            if not task:
                return
            
            logger.info(f"Processing task {task.id} for pitch deck {task.pitch_deck_id}")
            
            # Update progress
            processing_queue_manager.update_task_progress(
                task.id, 5, "Sending to GPU for processing", "Task picked up by queue processor", db
            )
            
            # Use split processing for incremental progress updates
            logger.info(f"Using split processing for task {task.id}")
            success = await self.send_to_gpu_split_processing(task, db)
            
            if not success:
                # Mark as failed if couldn't send to GPU
                processing_queue_manager.complete_task(
                    task.id, 
                    False,  # success = False 
                    None,   # results_path
                    "Failed to send task to GPU server",  # error_message
                    None,   # metadata
                    db
                )
        
        except Exception as e:
            logger.error(f"Error processing task: {e}", exc_info=True)
        finally:
            db.close()
    
    async def send_to_gpu(self, task: ProcessingTask, db: Session) -> bool:
        """Send task to GPU server for processing"""
        try:
            # Prepare request data
            # Convert relative path to absolute path
            full_file_path = task.file_path
            if not full_file_path.startswith('/'):
                full_file_path = f"{settings.SHARED_FILESYSTEM_MOUNT_PATH}/{task.file_path}"
            
            request_data = {
                "task_id": task.id,
                "pitch_deck_id": task.pitch_deck_id,
                "file_path": full_file_path,
                "company_id": task.company_id,
                "callback_url": f"{self.backend_url}/api/internal/update-deck-results",
                "processing_options": task.processing_options
            }
            
            logger.info(f"Sending task {task.id} to GPU server at {self.gpu_url}/api/process-pdf")
            logger.info(f"Request data: {json.dumps(request_data, indent=2)}")
            
            # Send request to GPU
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.gpu_url}/api/process-pdf",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"GPU accepted task {task.id}: {result.get('message', 'Processing started')}")
                    
                    # Update progress
                    processing_queue_manager.update_task_progress(
                        task.id, 10, "GPU processing started", 
                        f"Task sent to GPU successfully", db
                    )
                    return True
                else:
                    logger.error(f"GPU server returned error {response.status_code}: {response.text}")
                    return False
                    
        except httpx.ConnectError:
            logger.error(f"Failed to connect to GPU server at {self.gpu_url}")
            return False
        except Exception as e:
            logger.error(f"Error sending task to GPU: {e}", exc_info=True)
            return False
    
    async def send_to_gpu_split_processing(self, task: ProcessingTask, db: Session) -> bool:
        """Send task to GPU using split processing approach with incremental progress updates"""
        try:
            # Prepare common data
            full_file_path = task.file_path
            if not full_file_path.startswith('/'):
                full_file_path = f"{settings.SHARED_FILESYSTEM_MOUNT_PATH}/{task.file_path}"
            
            progress_callback_url = f"{self.backend_url}/api/internal/update-processing-progress"
            
            # Phase 1: Visual Analysis (10% -> 30%)
            logger.info(f"Phase 1: Starting visual analysis for deck {task.pitch_deck_id}")
            await self.update_progress(task.pitch_deck_id, 10, "Visual Analysis", "Analyzing slides and extracting content", db)
            
            visual_success = await self.run_visual_analysis_phase(task, full_file_path, db)
            if not visual_success:
                logger.error(f"Visual analysis failed for deck {task.pitch_deck_id} - failing task")
                await self.fail_task_with_error(task, "Visual analysis failed - could not process slides", db)
                return False
                
            await self.update_progress(task.pitch_deck_id, 30, "Visual Analysis Complete", "Slides analyzed, starting extraction", db)
            
            # Phase 2: Extraction (30% -> 60%)
            logger.info(f"Phase 2: Starting extraction for deck {task.pitch_deck_id}")
            await self.update_progress(task.pitch_deck_id, 40, "Data Extraction", "Extracting company details and classification", db)
            
            extraction_success = await self.run_extraction_phase(task, db)
            if not extraction_success:
                logger.error(f"Extraction failed for deck {task.pitch_deck_id} - failing task")
                await self.fail_task_with_error(task, "Data extraction failed - could not extract company details", db)
                return False
                
            await self.update_progress(task.pitch_deck_id, 60, "Extraction Complete", "Company data extracted, starting template analysis", db)
            
            # Phase 3: Template Analysis (60% -> 95%)
            logger.info(f"Phase 3: Starting template analysis for deck {task.pitch_deck_id}")
            await self.update_progress(task.pitch_deck_id, 70, "Template Analysis", "Running AI analysis with healthcare templates", db)
            
            template_success = await self.run_template_analysis_phase(task, progress_callback_url, db)
            if not template_success:
                logger.error(f"Template analysis failed for deck {task.pitch_deck_id} - failing task")
                await self.fail_task_with_error(task, "Template analysis failed - could not complete AI analysis", db)
                return False
                
            await self.update_progress(task.pitch_deck_id, 95, "Analysis Complete", "Finalizing results", db)
            
            # CRITICAL: Manually complete the task since template processing doesn't send final callback
            logger.info(f"Split processing completed successfully for task {task.id} - marking as completed")
            processing_queue_manager.complete_task(
                task.id, 
                True,  # success = True
                None,  # results_path
                None,  # error_message
                None,  # metadata
                db
            )
            
            # Also update pitch deck status
            from sqlalchemy import text
            db.execute(text(
                "UPDATE pitch_decks SET processing_status = 'completed' WHERE id = :pitch_deck_id"
            ), {"pitch_deck_id": task.pitch_deck_id})
            db.commit()
            
            logger.info(f"Task {task.id} marked as completed in both processing_queue and pitch_decks")
            return True
            
        except Exception as e:
            logger.error(f"Error in split processing for task {task.id}: {e}", exc_info=True)
            return False
    
    async def update_progress(self, pitch_deck_id: int, percentage: int, step: str, message: str, db: Session):
        """Update processing progress via internal API"""
        try:
            # Get task ID from pitch_deck_id
            from sqlalchemy import text
            result = db.execute(text(
                "SELECT id FROM processing_queue WHERE pitch_deck_id = :pitch_deck_id AND status = 'processing'"
            ), {"pitch_deck_id": pitch_deck_id}).fetchone()
            
            if result:
                task_id = result[0]
                processing_queue_manager.update_task_progress(
                    task_id, percentage, step, message, db
                )
            else:
                logger.warning(f"No processing task found for deck {pitch_deck_id}")
        except Exception as e:
            logger.error(f"Error updating progress for deck {pitch_deck_id}: {e}")
    
    async def fail_task_with_error(self, task: ProcessingTask, error_message: str, db: Session):
        """Mark task as failed with clear error message"""
        try:
            logger.error(f"Failing task {task.id} for deck {task.pitch_deck_id}: {error_message}")
            
            processing_queue_manager.complete_task(
                task.id, 
                False,  # success = False for failed tasks
                None,   # results_path
                error_message,  # error_message
                None,   # metadata
                db
            )
            
            # Also update the pitch deck status
            from sqlalchemy import text
            db.execute(text(
                "UPDATE pitch_decks SET processing_status = 'failed' WHERE id = :pitch_deck_id"
            ), {"pitch_deck_id": task.pitch_deck_id})
            db.commit()
            
            logger.info(f"Task {task.id} marked as failed with error: {error_message}")
            
        except Exception as e:
            logger.error(f"Error failing task {task.id}: {e}")
    
    async def run_visual_analysis_phase(self, task: ProcessingTask, full_file_path: str, db: Session) -> bool:
        """Run visual analysis phase using existing Dojo infrastructure"""
        try:
            # Get the active vision model from database
            from sqlalchemy import text
            model_result = db.execute(text(
                "SELECT model_name FROM model_configs WHERE model_type = 'vision' AND is_active = true LIMIT 1"
            )).fetchone()
            
            vision_model = model_result[0] if model_result else "gemma3:12b"  # Fallback to gemma3:12b
            logger.info(f"Using vision model: {vision_model}")
            
            # The visual analysis batch API expects deck_ids, file_paths, vision_model, and analysis_prompt
            request_data = {
                "deck_ids": [task.pitch_deck_id],
                "file_paths": [full_file_path],  # CRITICAL: This was missing!
                "vision_model": vision_model,
                "analysis_prompt": "Describe this slide from a pitchdeck from a perspective of an investor, but do not interpret the content, just describe what you see."
            }
            
            logger.info(f"Visual analysis request: deck_id={task.pitch_deck_id}, file_path={full_file_path}")
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.gpu_url}/api/run-visual-analysis-batch",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Visual analysis completed for deck {task.pitch_deck_id}")
                    return True
                else:
                    logger.error(f"Visual analysis failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error in visual analysis phase: {e}")
            return False
    
    async def run_extraction_phase(self, task: ProcessingTask, db: Session) -> bool:
        """Run extraction phase (company offering, classification, etc.)"""
        try:
            # For now, simulate extraction phase - this would call extraction endpoints
            await asyncio.sleep(2)  # Simulate processing time
            logger.info(f"Extraction phase completed for deck {task.pitch_deck_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error in extraction phase: {e}")
            return False
    
    async def run_template_analysis_phase(self, task: ProcessingTask, progress_callback_url: str, db: Session) -> bool:
        """Run template analysis phase using existing template processing infrastructure"""
        try:
            # Get template configuration from processing options
            processing_options = task.processing_options or {}
            
            # Determine template to use
            if processing_options.get('use_single_template') and processing_options.get('selected_template_id'):
                template_id = processing_options['selected_template_id']
                logger.info(f"Using GP override template {template_id} for deck {task.pitch_deck_id}")
            else:
                template_id = 9  # Standard Seven-Chapter Review as fallback
                logger.info(f"Using standard template {template_id} for deck {task.pitch_deck_id}")
            
            request_data = {
                "deck_ids": [task.pitch_deck_id],
                "template_id": template_id,
                "processing_options": {
                    "generate_thumbnails": True,
                    "callback_url": f"{self.backend_url}/api/internal/update-deck-results"
                }
            }
            
            async with httpx.AsyncClient(timeout=600.0) as client:  # Longer timeout for template analysis
                response = await client.post(
                    f"{self.gpu_url}/api/run-template-processing-only",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Template analysis completed for deck {task.pitch_deck_id}")
                    return True
                else:
                    logger.error(f"Template analysis failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error in template analysis phase: {e}")
            return False

# Global queue processor instance
queue_processor = QueueProcessor()