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
from ..db.models import User, PitchDeck
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
        
        # Save file to shared volume
        file_path = volume_storage.save_upload(
            file.file, 
            file.filename, 
            current_user.company_name
        )
        
        # Create PitchDeck record in database
        from ..api.projects import get_company_id_from_user
        company_id = get_company_id_from_user(current_user)
        
        pitch_deck = PitchDeck(
            user_id=current_user.id,
            company_id=company_id,
            file_name=file.filename,
            file_path=file_path,
            processing_status="queued"  # Start as queued
        )
        db.add(pitch_deck)
        db.commit()
        db.refresh(pitch_deck)
        
        # Get user's template configuration (for GPs)
        template_config = {}
        if current_user.role == "gp":
            try:
                template_config_query = text("""
                    SELECT use_single_template, selected_template_id 
                    FROM template_configurations 
                    WHERE user_id = :user_id
                """)
                config_result = db.execute(template_config_query, {"user_id": current_user.id}).fetchone()
                if config_result:
                    template_config = {
                        "use_single_template": config_result[0],
                        "selected_template_id": config_result[1]
                    }
                    logger.info(f"Using template config for user {current_user.email}: {template_config}")
            except Exception as e:
                logger.warning(f"Could not load template config for user {current_user.id}: {e}")

        # Add to robust processing queue
        processing_options = {
            "generate_thumbnails": True,
            "generate_feedback": True,
            "user_id": current_user.id,
            "upload_timestamp": pitch_deck.created_at.isoformat()
        }
        processing_options.update(template_config)  # Add template config if available
        
        task_id = processing_queue_manager.add_task(
            pitch_deck_id=pitch_deck.id,
            file_path=file_path,
            company_id=company_id,
            task_type="pdf_analysis",
            priority=TaskPriority.NORMAL,
            processing_options=processing_options,
            db=db
        )
        
        if not task_id:
            # Fallback to old processing if queue fails
            logger.warning(f"Queue system failed for deck {pitch_deck.id}, falling back to direct processing")
            pitch_deck.processing_status = "processing"
            db.commit()
            
            # Trigger direct processing as fallback
            from .documents import trigger_gpu_processing
            import asyncio
            asyncio.create_task(trigger_gpu_processing(pitch_deck.id, file_path, company_id))
        
        logger.info(f"Document uploaded: {file.filename} for user {current_user.email}, task_id: {task_id}")
        
        return {
            "message": "Document uploaded successfully",
            "filename": file.filename,
            "pitch_deck_id": pitch_deck.id,
            "file_path": file_path,
            "processing_status": "queued",
            "task_id": task_id
        }
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processing-progress/{pitch_deck_id}")
async def get_processing_progress_robust(
    pitch_deck_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get processing progress with robust queue system"""
    try:
        # Get pitch deck info
        pitch_deck = db.query(PitchDeck).filter(PitchDeck.id == pitch_deck_id).first()
        if not pitch_deck:
            raise HTTPException(status_code=404, detail="Pitch deck not found")
        
        # Check if user has access to this pitch deck
        if current_user.role == "startup" and pitch_deck.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get progress from queue system first
        queue_progress = processing_queue_manager.get_task_progress(pitch_deck_id, db)
        
        if queue_progress:
            # Task is actively managed by queue system
            return {
                "pitch_deck_id": pitch_deck_id,
                "file_name": pitch_deck.file_name,
                "processing_status": pitch_deck.processing_status,
                "queue_progress": queue_progress,
                "source": "queue_system",
                "created_at": pitch_deck.created_at.isoformat() if pitch_deck.created_at else None
            }
        
        # Fallback: check if completed or use legacy GPU progress
        if pitch_deck.processing_status == "completed":
            return {
                "pitch_deck_id": pitch_deck_id,
                "file_name": pitch_deck.file_name,
                "processing_status": "completed",
                "queue_progress": {
                    "progress_percentage": 100,
                    "current_step": "Analysis Complete",
                    "message": "PDF analysis completed successfully",
                    "status": "completed"
                },
                "source": "completed",
                "created_at": pitch_deck.created_at.isoformat() if pitch_deck.created_at else None
            }
        
        # Final fallback: try legacy GPU progress endpoint
        try:
            from ..services.gpu_http_client import gpu_http_client
            gpu_progress = gpu_http_client.get_processing_progress(pitch_deck_id)
            
            return {
                "pitch_deck_id": pitch_deck_id,
                "file_name": pitch_deck.file_name,
                "processing_status": pitch_deck.processing_status,
                "gpu_progress": gpu_progress,
                "source": "legacy_gpu",
                "created_at": pitch_deck.created_at.isoformat() if pitch_deck.created_at else None
            }
        except Exception as gpu_error:
            logger.warning(f"GPU progress check failed for deck {pitch_deck_id}: {gpu_error}")
            
            # Return basic status if all else fails
            return {
                "pitch_deck_id": pitch_deck_id,
                "file_name": pitch_deck.file_name,
                "processing_status": pitch_deck.processing_status,
                "queue_progress": {
                    "progress_percentage": 0 if pitch_deck.processing_status == "processing" else 100,
                    "current_step": "Processing" if pitch_deck.processing_status == "processing" else "Unknown",
                    "message": "Status unknown - please check back later",
                    "status": pitch_deck.processing_status
                },
                "source": "database_only",
                "created_at": pitch_deck.created_at.isoformat() if pitch_deck.created_at else None
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing progress for pitch deck {pitch_deck_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get processing progress")

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

# Keep legacy endpoints for backward compatibility
from .documents import get_processing_results, get_document_thumbnail

@router.get("/results/{pitch_deck_id}")
async def get_processing_results_compat(
    pitch_deck_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Legacy compatibility endpoint"""
    return await get_processing_results(pitch_deck_id, current_user, db)

@router.get("/{document_id}/thumbnail/slide/{slide_number}")
async def get_document_thumbnail_compat(
    document_id: int,
    slide_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Legacy compatibility endpoint"""
    return await get_document_thumbnail(document_id, slide_number, db, current_user)