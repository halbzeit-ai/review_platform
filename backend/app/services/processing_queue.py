"""
Robust Processing Queue System

This module provides a persistent, restart-resilient task queue system for PDF processing.
Tasks are stored in PostgreSQL and survive server restarts, with automatic retry and recovery.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import uuid
import socket

from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_
from ..db.database import SessionLocal, get_db
from ..db.models import ProcessingQueue, ProcessingProgress, ProcessingServer, TaskDependency
from ..core.config import settings

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing" 
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"

class TaskPriority(Enum):
    NORMAL = 1
    HIGH = 2
    URGENT = 3

@dataclass
class ProcessingTask:
    """Represents a processing task"""
    id: Optional[int]
    document_id: int  # Clean architecture - uses project_documents.id
    task_type: str
    status: TaskStatus
    priority: TaskPriority
    file_path: str
    company_id: str
    processing_options: Dict[str, Any]
    progress_percentage: int = 0
    current_step: Optional[str] = None
    progress_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    results_file_path: Optional[str] = None
    last_error: Optional[str] = None

class ProcessingQueueManager:
    """Manages the persistent processing queue system"""
    
    def __init__(self, server_type: str = "cpu"):
        self.server_id = self._generate_server_id()
        self.server_type = server_type
        self.max_concurrent_tasks = int(os.getenv("MAX_CONCURRENT_TASKS", "3"))
        self.heartbeat_interval = 30  # seconds
        self.lock_duration = timedelta(minutes=30)
        self._running_tasks: Dict[int, asyncio.Task] = {}
        
        logger.info(f"ProcessingQueueManager initialized: server_id={self.server_id}, type={server_type}")
    
    def _generate_server_id(self) -> str:
        """Generate unique server identifier"""
        hostname = socket.gethostname()
        process_id = os.getpid()
        return f"{hostname}-{process_id}-{uuid.uuid4().hex[:8]}"
    
    def register_server(self, db: Session) -> None:
        """Register this server instance in the database"""
        try:
            # Clean up old server instances (older than 1 hour)
            cleanup_query = text("""
                DELETE FROM processing_servers 
                WHERE last_heartbeat < CURRENT_TIMESTAMP - INTERVAL '1 hour'
            """)
            db.execute(cleanup_query)
            
            # Register or update this server
            upsert_query = text("""
                INSERT INTO processing_servers (
                    id, server_type, status, last_heartbeat, 
                    max_concurrent_tasks, current_load, capabilities
                ) VALUES (
                    :server_id, :server_type, 'active', CURRENT_TIMESTAMP,
                    :max_tasks, 0, :capabilities
                )
                ON CONFLICT (id) DO UPDATE SET
                    status = 'active',
                    last_heartbeat = CURRENT_TIMESTAMP,
                    max_concurrent_tasks = :max_tasks,
                    current_load = 0,
                    capabilities = :capabilities
            """)
            
            capabilities = {
                "pdf_analysis": True,
                "gpu_available": self.server_type == "gpu",
                "max_concurrent": self.max_concurrent_tasks
            }
            
            db.execute(upsert_query, {
                "server_id": self.server_id,
                "server_type": self.server_type,
                "max_tasks": self.max_concurrent_tasks,
                "capabilities": json.dumps(capabilities)
            })
            db.commit()
            
            logger.info(f"Server {self.server_id} registered successfully")
            
        except Exception as e:
            logger.error(f"Failed to register server: {e}")
            db.rollback()
    
    def add_task(
        self, 
        document_id: int,
        file_path: str,
        company_id: str,
        task_type: str = "pdf_analysis",
        priority: TaskPriority = TaskPriority.NORMAL,
        processing_options: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> Optional[int]:
        """Add a new processing task to the queue"""
        
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
            
        try:
            # Check if task already exists for this document
            existing_check = text("""
                SELECT id FROM processing_queue 
                WHERE document_id = :document_id 
                AND status IN ('queued', 'processing', 'retry')
                LIMIT 1
            """)
            
            existing = db.execute(existing_check, {"document_id": document_id}).fetchone()
            if existing:
                logger.info(f"Task already exists for document {document_id}: {existing[0]}")
                return existing[0]
            
            # Insert new task
            insert_query = text("""
                INSERT INTO processing_queue (
                    document_id, task_type, status, priority,
                    file_path, company_id, processing_options,
                    created_at
                ) VALUES (
                    :document_id, :task_type, 'queued', :priority,
                    :file_path, :company_id, :processing_options,
                    CURRENT_TIMESTAMP
                ) RETURNING id
            """)
            
            result = db.execute(insert_query, {
                "document_id": document_id,
                "task_type": task_type,
                "priority": priority.value,
                "file_path": file_path,
                "company_id": company_id,
                "processing_options": json.dumps(processing_options or {})
            })
            
            task_id = result.fetchone()[0]
            
            # Update project document to reference this task
            update_doc_query = text("""
                UPDATE project_documents 
                SET processing_status = 'processing'
                WHERE id = :document_id
            """)
            
            db.execute(update_doc_query, {"document_id": document_id})
            
            db.commit()
            
            logger.info(f"Added processing task {task_id} for document {document_id}")
            return task_id
            
        except Exception as e:
            logger.error(f"Failed to add processing task: {e}")
            db.rollback()
            return None
        finally:
            if should_close:
                db.close()
    
    def add_document_processing_pipeline(
        self, 
        document_id: int,
        file_path: str,
        company_id: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        processing_options: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> bool:
        """Create complete 4-layer processing pipeline for a document with proper dependencies"""
        
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
            
        try:
            logger.info(f"Creating 4-layer processing pipeline for document {document_id}")
            
            # Layer 1: Visual Analysis (Vision Container)
            visual_task_id = self.add_task(
                document_id=document_id,
                file_path=file_path,
                company_id=company_id,
                task_type="visual_analysis",
                priority=priority,
                processing_options=processing_options,
                db=db
            )
            
            if not visual_task_id:
                logger.error(f"Failed to create visual_analysis task for document {document_id}")
                return False
                
            # Layer 2: Slide Feedback (Vision Container) - can run parallel to visual_analysis
            feedback_task_id = self.add_task(
                document_id=document_id,
                file_path=file_path,
                company_id=company_id,
                task_type="slide_feedback",
                priority=priority,
                processing_options=processing_options,  # No dependency - can run parallel
                db=db
            )
            
            if not feedback_task_id:
                logger.error(f"Failed to create slide_feedback task for document {document_id}")
                return False
                
            # Layer 3: Extractions and Template (Text Container) - depends on visual_analysis
            extraction_task_id = self.add_task(
                document_id=document_id,
                file_path=file_path,
                company_id=company_id,
                task_type="extractions_and_template",
                priority=priority,
                processing_options={**(processing_options or {}), "depends_on": visual_task_id},
                db=db
            )
            
            if not extraction_task_id:
                logger.error(f"Failed to create extractions_and_template task for document {document_id}")
                return False
                
            # Layer 4: Specialized Analysis Tasks (Text Container) - depends on extractions_and_template
            specialized_types = ["specialized_clinical", "specialized_regulatory", "specialized_science"]
            specialized_task_ids = []
            
            for task_type in specialized_types:
                specialized_task_id = self.add_task(
                    document_id=document_id,
                    file_path=file_path,
                    company_id=company_id,
                    task_type=task_type,
                    priority=priority,
                    processing_options={**(processing_options or {}), "depends_on": extraction_task_id},
                    db=db
                )
                
                if specialized_task_id:
                    specialized_task_ids.append(specialized_task_id)
                    logger.info(f"✅ Created {task_type} task {specialized_task_id}")
                else:
                    logger.error(f"❌ Failed to create {task_type} task")
            
            db.commit()
            
            logger.info(f"🎉 Successfully created 4-layer pipeline for document {document_id}:")
            logger.info(f"   Layer 1 (Vision): visual_analysis task {visual_task_id} (no dependencies)")
            logger.info(f"   Layer 2 (Vision): slide_feedback task {feedback_task_id} (parallel to Layer 1)")
            logger.info(f"   Layer 3 (Text): extractions_and_template task {extraction_task_id} (depends on visual_analysis)")
            logger.info(f"   Layer 4 (Text): {len(specialized_task_ids)} specialized analysis tasks (depend on extractions_and_template)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create processing pipeline for document {document_id}: {e}")
            db.rollback()
            return False
        finally:
            if should_close:
                db.close()
    
    def get_next_task(self, db: Session) -> Optional[ProcessingTask]:
        """Get the next available task for processing"""
        try:
            # Use the PostgreSQL function to atomically get and lock a task
            # Updated capabilities for 4-layer container architecture
            capabilities_dict = {
                "visual_analysis": True,           # Vision Container
                "slide_feedback": True,            # Vision Container  
                "extractions_and_template": True, # Text Container
                "specialized_clinical": True,     # Text Container
                "specialized_regulatory": True,   # Text Container
                "specialized_science": True,      # Text Container
                "pdf_analysis": True              # Legacy compatibility
            }
            logger.debug("About to call get_next_processing_task function")
            result = db.execute(text("""
                SELECT * FROM get_next_processing_task(:server_id, :capabilities)
            """), {
                "server_id": self.server_id,
                "capabilities": json.dumps(capabilities_dict)
            }).fetchone()
            
            if not result:
                return None
            
            logger.debug(f"Got result from get_next_processing_task: {result}")
            task_id, document_id, task_type, file_path, company_id, processing_options = result
            logger.debug(f"processing_options type: {type(processing_options)}, value: {processing_options}")
            
            # Get full task details
            task_query = text("""
                SELECT 
                    id, document_id, task_type, status, priority,
                    file_path, company_id, processing_options,
                    progress_percentage, current_step, progress_message,
                    retry_count, max_retries, created_at, started_at,
                    results_file_path, last_error
                FROM processing_queue
                WHERE id = :task_id
            """)
            
            logger.debug("About to execute task details query")
            task_row = db.execute(task_query, {"task_id": task_id}).fetchone()
            if not task_row:
                return None
            
            logger.debug(f"Got task_row: {task_row}")
            logger.debug(f"task_row[7] (processing_options) type: {type(task_row[7])}, value: {task_row[7]}")
            
            # Ensure processing_options is a dict (handle both dict and string cases)
            processing_opts = task_row[7]
            if isinstance(processing_opts, str):
                # If it's a string, parse it as JSON
                processing_opts = json.loads(processing_opts)
            elif processing_opts is None:
                # If it's None, use empty dict
                processing_opts = {}
            # If it's already a dict, use it as-is
            
            logger.debug("About to create ProcessingTask object")
            return ProcessingTask(
                id=task_row[0],
                document_id=task_row[1],
                task_type=task_row[2],
                status=TaskStatus(task_row[3]),
                priority=TaskPriority(task_row[4]),
                file_path=task_row[5],
                company_id=task_row[6],
                processing_options=processing_opts,
                progress_percentage=task_row[8] or 0,
                current_step=task_row[9],
                progress_message=task_row[10],
                retry_count=task_row[11] or 0,
                max_retries=task_row[12] or 3,
                created_at=task_row[13],
                started_at=task_row[14],
                results_file_path=task_row[15],
                last_error=task_row[16]
            )
            
        except Exception as e:
            logger.error(f"Failed to get next task: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None
    
    def update_task_progress(
        self,
        task_id: int,
        progress_percentage: int,
        current_step: Optional[str] = None,
        message: Optional[str] = None,
        db: Optional[Session] = None
    ) -> bool:
        """Update task progress"""
        
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
            
        try:
            result = db.execute(text("""
                SELECT update_task_progress(:task_id, :progress, :step, :message, :step_data)
            """), {
                "task_id": task_id,
                "progress": progress_percentage,
                "step": current_step,
                "message": message,
                "step_data": json.dumps({})
            })
            
            success = result.fetchone()[0]
            db.commit()
            
            if success:
                logger.debug(f"Updated task {task_id} progress: {progress_percentage}% - {current_step}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to update task progress: {e}")
            db.rollback()
            return False
        finally:
            if should_close:
                db.close()
    
    def complete_task(
        self,
        task_id: int,
        success: bool,
        results_path: Optional[str] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        db: Optional[Session] = None
    ) -> bool:
        """Mark task as completed or failed"""
        
        if db is None:
            db = SessionLocal()
            should_close = True
        else:
            should_close = False
            
        try:
            result = db.execute(text("""
                SELECT complete_task(:task_id, :success, :results_path, :error_message, :metadata)
            """), {
                "task_id": task_id,
                "success": success,
                "results_path": results_path,
                "error_message": error_message,
                "metadata": json.dumps(metadata or {})
            })
            
            completed = result.fetchone()[0]
            db.commit()
            
            if completed:
                status = "completed" if success else "failed"
                logger.info(f"Task {task_id} marked as {status}")
                
                # Remove from running tasks
                if task_id in self._running_tasks:
                    del self._running_tasks[task_id]
            
            return completed
            
        except Exception as e:
            logger.error(f"Failed to complete task: {e}")
            db.rollback()
            return False
        finally:
            if should_close:
                db.close()
    
    # OLD MONOLITHIC METHOD REMOVED - Now using add_document_processing_pipeline() 
    # which creates all 4 tasks with proper dependencies from the start
    def get_task_progress(self, document_id: int, db: Session) -> Optional[Dict[str, Any]]:
        """Get current progress for a document (aggregated across 4-layer pipeline)"""
        try:
            # Get all tasks for this document
            query = text("""
                SELECT 
                    pq.task_type,
                    pq.progress_percentage,
                    pq.current_step,
                    pq.progress_message,
                    pq.status,
                    pq.started_at,
                    pq.retry_count,
                    pq.created_at
                FROM processing_queue pq
                WHERE pq.document_id = :document_id
                ORDER BY pq.created_at ASC
            """)
            
            results = db.execute(query, {"document_id": document_id}).fetchall()
            
            if not results:
                return None
            
            # Calculate overall progress based on 4-layer pipeline
            tasks = {}
            for row in results:
                task_type, progress, step, message, status, started_at, retry_count, created_at = row
                tasks[task_type] = {
                    "progress": progress or 0,
                    "step": step,
                    "message": message,
                    "status": status,
                    "started_at": started_at,
                    "retry_count": retry_count
                }
            
            # Calculate overall progress based on task completion
            # Each task represents 25% of total progress
            total_progress = 0
            overall_status = "queued"
            current_message = "Initializing processing pipeline"
            current_step = "Queued"
            
            # Task order and weights
            task_order = ["visual_analysis", "slide_feedback", "extractions_and_template", "specialized_clinical", "specialized_regulatory", "specialized_science"]
            task_weights = {"visual_analysis": 20, "slide_feedback": 20, "extractions_and_template": 30, "specialized_clinical": 10, "specialized_regulatory": 10, "specialized_science": 10}
            
            for task_type in task_order:
                if task_type in tasks:
                    task = tasks[task_type]
                    task_weight = task_weights.get(task_type, 10)
                    
                    if task["status"] == "completed":
                        total_progress += task_weight
                    elif task["status"] == "processing":
                        # Add partial progress based on task's internal progress
                        task_progress = task["progress"] or 0
                        total_progress += (task_weight * task_progress / 100)
                        overall_status = "processing"
                        current_message = task["message"] or f"Processing {task_type}"
                        current_step = task["step"] or f"Processing {task_type}"
                        break  # Show current processing task
                    elif task["status"] in ["queued", "retry"]:
                        overall_status = "processing" if overall_status != "queued" else "queued"
                        if overall_status == "queued":
                            current_message = f"Queued: {task_type}"
                            current_step = "Queued for processing"
                        break
                    elif task["status"] == "failed":
                        overall_status = "failed"
                        current_message = task["message"] or f"Failed: {task_type}"
                        current_step = "Processing failed"
                        break
            
            # Check if all tasks are completed
            if total_progress >= 100:
                overall_status = "completed"
                current_message = "Document processing completed"
                current_step = "Completed"
            
            # Get earliest started_at time from all tasks
            earliest_start = None
            max_retry_count = 0
            for task in tasks.values():
                if task["started_at"] and (not earliest_start or task["started_at"] < earliest_start):
                    earliest_start = task["started_at"]
                max_retry_count = max(max_retry_count, task["retry_count"] or 0)
            
            return {
                "progress_percentage": min(int(total_progress), 100),
                "current_step": current_step,
                "message": current_message,
                "status": overall_status,
                "started_at": earliest_start.isoformat() if earliest_start else None,
                "retry_count": max_retry_count,
                "task_breakdown": tasks  # Debug info - shows individual task states
            }
            
        except Exception as e:
            logger.error(f"Failed to get task progress: {e}")
            return None
    
    def recover_abandoned_tasks(self, db: Session) -> int:
        """Recover tasks that were processing when server crashed"""
        try:
            # Clean up expired locks and reset tasks to queued
            result = db.execute(text("SELECT cleanup_expired_locks()"))
            cleaned_count = result.fetchone()[0]
            db.commit()
            
            if cleaned_count > 0:
                logger.info(f"Recovered {cleaned_count} abandoned processing tasks")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Failed to recover abandoned tasks: {e}")
            db.rollback()
            return 0
    
    def retry_failed_tasks(self, db: Session, max_age_hours: int = 24) -> int:
        """Retry failed tasks that haven't exceeded max retries"""
        try:
            query = text("""
                SELECT id FROM processing_queue
                WHERE status = 'failed'
                AND retry_count < max_retries
                AND created_at > CURRENT_TIMESTAMP - INTERVAL ':max_age hours'
            """)
            
            failed_tasks = db.execute(query, {"max_age": max_age_hours}).fetchall()
            
            retried_count = 0
            for (task_id,) in failed_tasks:
                result = db.execute(text("SELECT retry_failed_task(:task_id)"), {"task_id": task_id})
                if result.fetchone()[0]:
                    retried_count += 1
            
            db.commit()
            
            if retried_count > 0:
                logger.info(f"Scheduled {retried_count} failed tasks for retry")
            
            return retried_count
            
        except Exception as e:
            logger.error(f"Failed to retry tasks: {e}")
            db.rollback()
            return 0
    
    def get_queue_stats(self, db: Session) -> Dict[str, Any]:
        """Get processing queue statistics"""
        try:
            stats_query = text("""
                SELECT 
                    status,
                    COUNT(*) as count,
                    AVG(EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - created_at))) as avg_age_seconds
                FROM processing_queue
                WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
                GROUP BY status
            """)
            
            results = db.execute(stats_query).fetchall()
            
            stats = {
                "queue_stats": {row[0]: {"count": row[1], "avg_age_seconds": row[2]} for row in results},
                "server_id": self.server_id,
                "running_tasks": len(self._running_tasks),
                "max_concurrent": self.max_concurrent_tasks
            }
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get queue stats: {e}")
            return {"error": str(e)}
    
    async def heartbeat(self, db: Session) -> None:
        """Send heartbeat to indicate server is alive"""
        try:
            current_load = len(self._running_tasks)
            
            heartbeat_query = text("""
                UPDATE processing_servers 
                SET 
                    last_heartbeat = CURRENT_TIMESTAMP,
                    current_load = :current_load,
                    status = 'active'
                WHERE id = :server_id
            """)
            
            db.execute(heartbeat_query, {
                "server_id": self.server_id,
                "current_load": current_load
            })
            db.commit()
            
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")
            db.rollback()

# Global queue manager instance
processing_queue_manager = ProcessingQueueManager()