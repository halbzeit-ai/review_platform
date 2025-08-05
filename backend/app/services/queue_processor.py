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
            
            # Send to GPU
            success = await self.send_to_gpu(task, db)
            
            if not success:
                # Mark as failed if couldn't send to GPU
                processing_queue_manager.complete_task(
                    task.id, 
                    False, 
                    error_message="Failed to send task to GPU server",
                    db=db
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

# Global queue processor instance
queue_processor = QueueProcessor()