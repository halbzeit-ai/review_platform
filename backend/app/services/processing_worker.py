"""
Processing Worker Service

This service runs continuously and processes tasks from the robust queue system.
It handles task execution, progress updates, and error recovery.
"""

import asyncio
import logging
from typing import Optional
import signal
import sys
from datetime import datetime

import sys
import os
from pathlib import Path

# Add backend directory to Python path for absolute imports
backend_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_path))

from app.db.database import SessionLocal
from app.services.processing_queue import processing_queue_manager, ProcessingTask, TaskStatus
from app.services.gpu_http_client import gpu_http_client
from sqlalchemy import text

logger = logging.getLogger(__name__)

class ProcessingWorker:
    """Worker service that processes tasks from the queue"""
    
    def __init__(self, server_type: str = "cpu"):
        self.server_type = server_type
        self.running = False
        self.current_tasks = {}
        self.poll_interval = 5  # seconds
        self.heartbeat_interval = 30  # seconds
        
        # Setup shared logging
        from app.core.logging_config import setup_shared_logging
        self.shared_logger = setup_shared_logging("processing_worker")
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info(f"ProcessingWorker initialized: server_type={server_type}")
        self.shared_logger.info(f"ProcessingWorker initialized: server_type={server_type}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Shutdown signal received: {signum}")
        self.shared_logger.info(f"Shutdown signal received: {signum}")
        self.running = False
    
    async def start(self):
        """Start the worker service"""
        logger.info("Starting ProcessingWorker...")
        self.shared_logger.info("Starting ProcessingWorker...")
        self.running = True
        
        # Register server and recover any abandoned tasks
        with SessionLocal() as db:
            processing_queue_manager.register_server(db)
            recovered = processing_queue_manager.recover_abandoned_tasks(db)
            if recovered > 0:
                logger.info(f"Recovered {recovered} abandoned tasks on startup")
                self.shared_logger.info(f"Recovered {recovered} abandoned tasks on startup")
        
        # Start background tasks
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        processing_task = asyncio.create_task(self._processing_loop())
        
        try:
            # Wait for tasks to complete
            await asyncio.gather(heartbeat_task, processing_task)
        except asyncio.CancelledError:
            logger.info("Worker tasks cancelled")
        except Exception as e:
            logger.error(f"Worker error: {e}")
        finally:
            logger.info("ProcessingWorker stopped")
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeats"""
        while self.running:
            try:
                with SessionLocal() as db:
                    await processing_queue_manager.heartbeat(db)
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
    
    async def _processing_loop(self):
        """Main processing loop"""
        while self.running:
            try:
                # Check if we can take on more tasks
                if len(self.current_tasks) >= processing_queue_manager.max_concurrent_tasks:
                    await asyncio.sleep(self.poll_interval)
                    continue
                
                # Get next task from queue
                with SessionLocal() as db:
                    task = processing_queue_manager.get_next_task(db)
                
                if task:
                    # Start processing task
                    task_coroutine = self._process_task(task)
                    task_future = asyncio.create_task(task_coroutine)
                    self.current_tasks[task.id] = task_future
                    
                    logger.info(f"Started processing task {task.id} for pitch deck {task.pitch_deck_id}")
                    self.shared_logger.info(f"Started processing task {task.id} for pitch deck {task.pitch_deck_id}")
                else:
                    # No tasks available, wait before checking again
                    await asyncio.sleep(self.poll_interval)
                
                # Clean up completed tasks
                completed_task_ids = []
                for task_id, future in self.current_tasks.items():
                    if future.done():
                        completed_task_ids.append(task_id)
                        try:
                            await future  # Get any exceptions
                        except Exception as e:
                            logger.error(f"Task {task_id} failed: {e}")
                
                for task_id in completed_task_ids:
                    del self.current_tasks[task_id]
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Processing loop error: {e}")
                await asyncio.sleep(5)
    
    async def _process_task(self, task: ProcessingTask):
        """Process a single task"""
        db = SessionLocal()
        try:
            logger.info(f"Processing task {task.id}: {task.task_type} for pitch deck {task.pitch_deck_id}")
            self.shared_logger.info(f"Processing task {task.id}: {task.task_type} for pitch deck {task.pitch_deck_id}")
            
            # Update progress to starting
            processing_queue_manager.update_task_progress(
                task.id, 5, "Starting analysis", "Initializing PDF processing...", db
            )
            
            if task.task_type == "pdf_analysis":
                await self._process_pdf_analysis(task, db)
            else:
                raise ValueError(f"Unknown task type: {task.task_type}")
            
        except Exception as e:
            logger.error(f"Task {task.id} failed: {e}")
            
            # Mark task as failed
            processing_queue_manager.complete_task(
                task.id, 
                success=False, 
                error_message=str(e),
                db=db
            )
            
            # Check if we should retry
            if task.retry_count < task.max_retries:
                with SessionLocal() as retry_db:
                    retry_db.execute(text("SELECT retry_failed_task(:task_id)"), {"task_id": task.id})
                    retry_db.commit()
                    logger.info(f"Task {task.id} scheduled for retry ({task.retry_count + 1}/{task.max_retries})")
            
        finally:
            db.close()
    
    async def _process_pdf_analysis(self, task: ProcessingTask, db):
        """Process PDF analysis task"""
        
        # Update progress
        processing_queue_manager.update_task_progress(
            task.id, 10, "Connecting to GPU", "Establishing connection to processing server...", db
        )
        
        # Call GPU processing
        results = await gpu_http_client.process_pdf(
            task.pitch_deck_id,
            task.file_path,
            task.company_id
        )
        
        if results.get("success"):
            # Update progress
            processing_queue_manager.update_task_progress(
                task.id, 90, "Finalizing results", "Processing completed, saving results...", db
            )
            
            # Complete task successfully
            processing_queue_manager.complete_task(
                task.id,
                success=True,
                results_path=results.get("results_path"),
                metadata={
                    "results_file": results.get("results_file"),
                    "processing_time": results.get("processing_time"),
                    "gpu_server": results.get("gpu_server")
                },
                db=db
            )
            
            logger.info(f"Task {task.id} completed successfully")
            self.shared_logger.info(f"Task {task.id} completed successfully")
            
        else:
            # Processing failed
            error_message = results.get("error", "GPU processing failed")
            raise Exception(error_message)

async def run_worker(server_type: str = "cpu"):
    """Run the processing worker"""
    worker = ProcessingWorker(server_type)
    await worker.start()

async def main():
    """Main entry point for the processing worker service"""
    import sys
    server_type = sys.argv[1] if len(sys.argv) > 1 else "cpu"
    
    # Import the shared logging configuration
    from app.core.logging_config import setup_shared_logging
    
    # Setup shared filesystem logging
    shared_logger = setup_shared_logging("processing_worker")
    
    # Also configure basic logging for console output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    logger.info(f"Starting Processing Worker Service (server_type={server_type})")
    shared_logger.info(f"Processing Worker Service started: server_type={server_type}")
    await run_worker(server_type)

if __name__ == "__main__":
    asyncio.run(main())