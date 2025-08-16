"""
Robust Documents API with Persistent Task Queue

This replaces the fragile in-memory processing with a persistent queue system
that survives server restarts and handles failures gracefully.
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.volume_storage import volume_storage
from ..core.config import settings
from ..db.models import User, ProjectDocument, ProjectMember
from ..db.database import get_db
from ..services.processing_queue import processing_queue_manager, TaskPriority
from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload")
async def upload_document_robust(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload document with robust processing queue"""
    if current_user.role != "startup":
        raise HTTPException(status_code=403, detail="Only startups can upload documents")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Check if volume is mounted
        if not volume_storage.is_volume_mounted():
            raise HTTPException(status_code=503, detail="Storage volume is not available")
        
        # Get the project that the user belongs to (project-centric architecture)
        project_query = text("""
            SELECT p.id, p.company_id, p.project_name
            FROM projects p
            JOIN project_members pm ON p.id = pm.project_id
            WHERE pm.user_id = :user_id AND p.is_active = TRUE
            ORDER BY p.created_at DESC
            LIMIT 1
        """)
        project_result = db.execute(project_query, {"user_id": current_user.id}).fetchone()
        
        if not project_result:
            raise HTTPException(status_code=403, detail="User must be a member of an active project to upload documents")
        
        project_id, company_id, project_name = project_result
        logger.info(f"User {current_user.email} uploading to project {project_id} ({project_name}) with company_id: {company_id}")
        
        # Save file to shared volume
        file_path = volume_storage.save_upload(
            file.file, 
            file.filename, 
            current_user.company_name
        )
        
        # Create ProjectDocument - clean architecture
        project_document = ProjectDocument(
            project_id=project_id,
            document_type="pitch_deck",
            file_name=file.filename,
            file_path=file_path,
            original_filename=file.filename,
            uploaded_by=current_user.id,
            processing_status="queued"
        )
        db.add(project_document)
        db.commit()
        db.refresh(project_document)
        
        # Get template configuration from ANY GP in this project (system-wide override)
        template_config = {}
        try:
            # Find any GP in this project who has template override configured
            gp_template_query = text("""
                SELECT tc.use_single_template, tc.selected_template_id, u.email
                FROM template_configurations tc
                JOIN users u ON tc.user_id = u.id
                JOIN project_members pm ON u.id = pm.user_id
                WHERE pm.project_id = :project_id 
                AND u.role = 'gp' 
                AND tc.use_single_template = true
                AND tc.selected_template_id IS NOT NULL
                ORDER BY tc.created_at DESC
                LIMIT 1
            """)
            config_result = db.execute(gp_template_query, {"project_id": project_id}).fetchone()
            if config_result:
                template_config = {
                    "use_single_template": config_result[0],
                    "selected_template_id": config_result[1]
                }
                logger.info(f"Using system-wide GP template override from {config_result[2]}: {template_config}")
            else:
                logger.info(f"No GP template override found for project {project_id} - will use classification-based selection")
        except Exception as e:
            logger.warning(f"Could not load GP template config for project {project_id}: {e}")

        # Add to robust processing queue
        processing_options = {
            "generate_thumbnails": True,
            "generate_feedback": True,
            "user_id": current_user.id,
            "upload_timestamp": project_document.upload_date.isoformat(),
            "project_id": project_id  # Include project_id for new architecture
        }
        processing_options.update(template_config)  # Add template config if available
        
        # Use new 4-layer processing pipeline architecture
        pipeline_created = processing_queue_manager.add_document_processing_pipeline(
            document_id=project_document.id,
            file_path=file_path,
            company_id=company_id,
            priority=TaskPriority.NORMAL,
            processing_options=processing_options,
            db=db
        )
        
        task_id = project_document.id if pipeline_created else None
        
        if not task_id:
            # Fallback to direct processing if queue fails
            logger.warning(f"Queue system failed for document {project_document.id}, falling back to direct processing")
            project_document.processing_status = "processing"
            db.commit()
            
            # TODO: Update trigger_gpu_processing to work with project_documents
            logger.error("Direct processing fallback not yet implemented for project_documents")
            raise HTTPException(status_code=500, detail="Processing system temporarily unavailable")
        
        logger.info(f"Document uploaded: {file.filename} for user {current_user.email}, task_id: {task_id}")
        
        return {
            "message": "Document uploaded successfully",
            "filename": file.filename,
            "document_id": project_document.id,
            "project_id": project_id,
            "file_path": file_path,
            "processing_status": "queued",
            "task_id": task_id
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processing-progress/{document_id}")
async def get_processing_progress_robust(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get processing progress with robust queue system"""
    try:
        # Get document info from project_documents (clean architecture)
        document = db.query(ProjectDocument).filter(ProjectDocument.id == document_id).first()
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Check if user has access to this document (through project membership)
        if current_user.role == "startup":
            # Check project membership
            project_member = db.query(ProjectMember).filter(
                ProjectMember.project_id == document.project_id,
                ProjectMember.user_id == current_user.id
            ).first()
            if not project_member:
                raise HTTPException(status_code=403, detail="Access denied")
        
        # Get progress from queue system - MUST work, no fallbacks
        queue_progress = processing_queue_manager.get_task_progress(document_id, db)
        
        if queue_progress:
            # Task is actively managed by queue system
            return {
                "document_id": document_id,
                "file_name": document.file_name,
                "processing_status": document.processing_status,
                "queue_progress": queue_progress,
                "source": "queue_system",
                "created_at": document.upload_date.isoformat() if document.upload_date else None
            }
        
        # FAIL HARD: No fallbacks - queue system MUST work
        logger.error(f"❌ QUEUE SYSTEM FAILURE: No progress found for document {document_id}")
        logger.error(f"📊 Document status: {document.processing_status}")
        logger.error(f"📅 Upload date: {document.upload_date}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Queue system failure: No progress tracking found for document {document_id}. Check processing queue."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing progress for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get processing progress")

@router.get("/failure-details/{document_id}")
async def get_document_failure_details(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed failure information for a document"""
    try:
        # Check if user has access to this document
        access_query = text("""
            SELECT pd.id, pd.processing_status, p.project_name
            FROM project_documents pd
            JOIN projects p ON pd.project_id = p.id
            JOIN project_members pm ON p.id = pm.project_id
            WHERE pd.id = :document_id 
            AND (pm.user_id = :user_id OR :is_gp = true)
        """)
        result = db.execute(access_query, {
            "document_id": document_id,
            "user_id": current_user.id,
            "is_gp": current_user.role == "gp"
        }).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found or access denied")
        
        doc_id, doc_status, project_name = result
        
        # Get all failed tasks for this document
        failed_tasks_query = text("""
            SELECT 
                pq.id as task_id,
                pq.task_type,
                pq.status,
                pq.last_error,
                pq.created_at,
                pq.started_at,
                pq.completed_at,
                pq.retry_count,
                pq.current_step,
                pq.progress_message
            FROM processing_queue pq
            WHERE pq.document_id = :document_id
            AND pq.status IN ('failed', 'retry')
            ORDER BY pq.created_at
        """)
        
        failed_tasks = db.execute(failed_tasks_query, {"document_id": document_id}).fetchall()
        
        # Format the failure information
        failure_details = {
            "document_id": document_id,
            "project_name": project_name,
            "overall_status": doc_status,
            "failed_tasks": [],
            "can_retry": doc_status in ["failed", "error"],
            "failure_summary": None
        }
        
        for task in failed_tasks:
            task_info = {
                "task_id": task.task_id,
                "task_type": task.task_type,
                "status": task.status,
                "error_message": task.last_error or "No error message recorded",
                "failed_at": task.completed_at.isoformat() if task.completed_at else None,
                "retry_count": task.retry_count,
                "last_step": task.current_step,
                "progress_message": task.progress_message
            }
            failure_details["failed_tasks"].append(task_info)
        
        # Generate failure summary
        if failure_details["failed_tasks"]:
            first_failure = failure_details["failed_tasks"][0]
            failure_details["failure_summary"] = f"Processing failed at {first_failure['task_type']} step: {first_failure['error_message']}"
        elif doc_status == "failed":
            failure_details["failure_summary"] = "Document processing failed but no specific error was recorded"
        
        return failure_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting failure details for document {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get failure details")

@router.post("/retry-document/{document_id}")
async def retry_failed_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retry processing for a failed document"""
    try:
        # Check if user has access to this document
        access_query = text("""
            SELECT pd.id, pd.processing_status, pd.file_path, pd.project_id, p.company_id
            FROM project_documents pd
            JOIN projects p ON pd.project_id = p.id
            JOIN project_members pm ON p.id = pm.project_id
            WHERE pd.id = :document_id 
            AND (pm.user_id = :user_id OR :is_gp = true)
        """)
        result = db.execute(access_query, {
            "document_id": document_id,
            "user_id": current_user.id,
            "is_gp": current_user.role == "gp"
        }).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Document not found or access denied")
        
        doc_id, doc_status, file_path, project_id, company_id = result
        
        if doc_status not in ["failed", "error"]:
            raise HTTPException(status_code=400, detail=f"Document is not in failed state (current: {doc_status})")
        
        # Delete all existing tasks for this document
        delete_query = text("""
            DELETE FROM processing_queue 
            WHERE document_id = :document_id
        """)
        db.execute(delete_query, {"document_id": document_id})
        
        # Reset document status
        update_doc_query = text("""
            UPDATE project_documents 
            SET processing_status = 'queued'
            WHERE id = :document_id
        """)
        db.execute(update_doc_query, {"document_id": document_id})
        
        # Create new 4-layer processing pipeline
        processing_options = {
            "generate_thumbnails": True,
            "generate_feedback": True,
            "user_id": current_user.id,
            "project_id": project_id,
            "is_retry": True
        }
        
        pipeline_created = processing_queue_manager.add_document_processing_pipeline(
            document_id=document_id,
            file_path=file_path,
            company_id=company_id,
            priority=TaskPriority.HIGH,  # Give retry higher priority
            processing_options=processing_options,
            db=db
        )
        
        if not pipeline_created:
            raise HTTPException(status_code=500, detail="Failed to create retry pipeline")
        
        db.commit()
        
        return {
            "success": True,
            "message": "Document queued for retry processing",
            "document_id": document_id,
            "new_status": "queued"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying document {document_id}: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to retry document")

@router.get("/queue-stats")
async def get_queue_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get processing queue statistics (GP only)"""
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        stats = processing_queue_manager.get_queue_stats(db)
        return stats
    except Exception as e:
        logger.error(f"Error getting queue stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get queue statistics")

@router.post("/admin/recover-tasks")
async def recover_abandoned_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Recover abandoned processing tasks (GP only)"""
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        recovered_count = processing_queue_manager.recover_abandoned_tasks(db)
        return {
            "message": f"Recovered {recovered_count} abandoned tasks",
            "recovered_count": recovered_count
        }
    except Exception as e:
        logger.error(f"Error recovering abandoned tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to recover abandoned tasks")

@router.post("/admin/retry-failed-tasks")
async def retry_failed_tasks(
    max_age_hours: int = 24,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retry failed processing tasks (GP only)"""
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Access denied")
    
    try:
        retried_count = processing_queue_manager.retry_failed_tasks(db, max_age_hours)
        return {
            "message": f"Scheduled {retried_count} failed tasks for retry",
            "retried_count": retried_count
        }
    except Exception as e:
        logger.error(f"Error retrying failed tasks: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry failed tasks")

# CLEAN ARCHITECTURE: Legacy compatibility endpoints removed - no backward compatibility needed