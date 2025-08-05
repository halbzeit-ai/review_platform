"""
Internal API endpoints for GPU processing communication
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
import logging

from ..db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])

class DeckResultsUpdateRequest(BaseModel):
    pitch_deck_id: int
    results_file_path: str
    processing_status: str

@router.post("/update-deck-results")
async def update_deck_results(
    request: DeckResultsUpdateRequest,
    db: Session = Depends(get_db)
):
    """Internal endpoint for GPU processing to update deck results"""
    try:
        logger.info(f"🔍 DEBUG: Received update request for deck {request.pitch_deck_id}")
        logger.info(f"🔍 DEBUG: Results file: {request.results_file_path}")
        logger.info(f"🔍 DEBUG: Status: {request.processing_status}")
        
        # Check if the deck exists first
        check_query = text("SELECT id, file_name FROM pitch_decks WHERE id = :pitch_deck_id")
        check_result = db.execute(check_query, {"pitch_deck_id": request.pitch_deck_id})
        deck = check_result.fetchone()
        
        if deck:
            logger.info(f"🔍 DEBUG: Found deck {deck[0]}: {deck[1]}")
        else:
            logger.error(f"🔍 DEBUG: No deck found with ID {request.pitch_deck_id}")
            # List all existing decks for debugging
            all_decks = db.execute(text("SELECT id, file_name FROM pitch_decks ORDER BY id")).fetchall()
            logger.error(f"🔍 DEBUG: Available decks: {[(d[0], d[1]) for d in all_decks]}")
        
        # Update the pitch_decks table
        update_query = text("""
            UPDATE pitch_decks 
            SET results_file_path = :results_file_path, processing_status = :processing_status
            WHERE id = :pitch_deck_id
        """)
        
        result = db.execute(update_query, {
            "results_file_path": request.results_file_path,
            "processing_status": request.processing_status,
            "pitch_deck_id": request.pitch_deck_id
        })
        
        logger.info(f"🔍 DEBUG: Pitch decks update affected {result.rowcount} rows")
        
        # CRITICAL FIX: Also update the processing_queue table
        queue_update_query = text("""
            UPDATE processing_queue 
            SET status = :queue_status, 
                completed_at = CURRENT_TIMESTAMP,
                results_file_path = :results_file_path,
                progress_percentage = 100,
                current_step = 'Analysis Complete',
                progress_message = 'PDF analysis completed successfully'
            WHERE pitch_deck_id = :pitch_deck_id 
            AND status = 'processing'
        """)
        
        # Map processing status to queue status
        queue_status = "completed" if request.processing_status == "completed" else "failed"
        
        queue_result = db.execute(queue_update_query, {
            "queue_status": queue_status,
            "results_file_path": request.results_file_path,
            "pitch_deck_id": request.pitch_deck_id
        })
        
        logger.info(f"🔍 DEBUG: Processing queue update affected {queue_result.rowcount} rows")
        
        db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Pitch deck {request.pitch_deck_id} not found"
            )
        
        logger.info(f"Updated deck {request.pitch_deck_id}: {request.results_file_path} -> {request.processing_status}")
        
        return {
            "success": True,
            "message": f"Updated deck {request.pitch_deck_id} successfully",
            "pitch_deck_id": request.pitch_deck_id,
            "results_file_path": request.results_file_path,
            "processing_status": request.processing_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating deck results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update deck results: {str(e)}"
        )

class ProcessingProgressUpdateRequest(BaseModel):
    pitch_deck_id: int
    progress_percentage: int
    current_step: str
    progress_message: str
    phase: str  # 'visual_analysis', 'extraction', 'template_analysis'

@router.post("/update-processing-progress")
async def update_processing_progress(
    request: ProcessingProgressUpdateRequest,
    db: Session = Depends(get_db)
):
    """Internal endpoint for GPU to send incremental progress updates during processing"""
    try:
        logger.info(f"📊 Progress update for deck {request.pitch_deck_id}: {request.progress_percentage}% - {request.current_step}")
        
        # Update the processing_queue table with incremental progress
        progress_query = text("""
            UPDATE processing_queue 
            SET progress_percentage = :progress_percentage,
                current_step = :current_step,
                progress_message = :progress_message
            WHERE pitch_deck_id = :pitch_deck_id 
            AND status = 'processing'
        """)
        
        result = db.execute(progress_query, {
            "progress_percentage": request.progress_percentage,
            "current_step": request.current_step,
            "progress_message": request.progress_message,
            "pitch_deck_id": request.pitch_deck_id
        })
        
        db.commit()
        logger.info(f"📊 Progress update applied to {result.rowcount} queue entries")
        
        if result.rowcount == 0:
            logger.warning(f"📊 No processing queue entry found for deck {request.pitch_deck_id}")
        
        return {
            "success": True,
            "message": f"Progress updated for deck {request.pitch_deck_id}",
            "pitch_deck_id": request.pitch_deck_id,
            "progress_percentage": request.progress_percentage,
            "current_step": request.current_step
        }
        
    except Exception as e:
        logger.error(f"Error updating processing progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update processing progress: {str(e)}"
        )