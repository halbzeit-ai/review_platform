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
        
        db.commit()
        logger.info(f"🔍 DEBUG: Update affected {result.rowcount} rows")
        
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