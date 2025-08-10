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

class SpecializedAnalysisRequest(BaseModel):
    pitch_deck_id: int
    specialized_analysis: dict  # e.g. {"clinical_validation": "...", "regulatory_pathway": "...", "scientific_hypothesis": "..."}

@router.post("/save-specialized-analysis")
async def save_specialized_analysis(
    request: SpecializedAnalysisRequest,
    db: Session = Depends(get_db)
):
    """Internal endpoint for GPU to save specialized analysis results"""
    try:
        logger.info(f"💾 Saving specialized analysis for deck {request.pitch_deck_id}")
        
        # First, delete any existing specialized analysis for this deck
        delete_query = text("DELETE FROM specialized_analysis_results WHERE pitch_deck_id = :pitch_deck_id")
        db.execute(delete_query, {"pitch_deck_id": request.pitch_deck_id})
        
        # Save each specialized analysis result
        saved_analyses = []
        for analysis_type, analysis_result in request.specialized_analysis.items():
            if analysis_result and analysis_result.strip():  # Only save non-empty results
                insert_query = text("""
                    INSERT INTO specialized_analysis_results 
                    (pitch_deck_id, analysis_type, analysis_result, created_at) 
                    VALUES (:pitch_deck_id, :analysis_type, :analysis_result, NOW())
                """)
                
                db.execute(insert_query, {
                    "pitch_deck_id": request.pitch_deck_id,
                    "analysis_type": analysis_type,
                    "analysis_result": analysis_result
                })
                
                saved_analyses.append(analysis_type)
                logger.info(f"✅ Saved {analysis_type} analysis for deck {request.pitch_deck_id}")
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Saved {len(saved_analyses)} specialized analyses for deck {request.pitch_deck_id}",
            "pitch_deck_id": request.pitch_deck_id,
            "saved_analyses": saved_analyses
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving specialized analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save specialized analysis: {str(e)}"
        )

class TemplateProcessingRequest(BaseModel):
    experiment_name: str
    pitch_deck_id: int
    template_processing_results: dict

@router.post("/save-template-processing")
async def save_template_processing(
    request: TemplateProcessingRequest,
    db: Session = Depends(get_db)
):
    """Internal endpoint for GPU to save template processing results for startup uploads"""
    try:
        logger.info(f"💾 Saving template processing results for deck {request.pitch_deck_id}")
        
        import json
        
        # First check if there's an existing extraction experiment for this deck
        existing_query = text("""
            SELECT id FROM extraction_experiments 
            WHERE pitch_deck_ids LIKE '%' || :deck_id || '%'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        existing_result = db.execute(existing_query, {"deck_id": str(request.pitch_deck_id)}).fetchone()
        
        if existing_result:
            # Update existing experiment with template processing results
            experiment_id = existing_result[0]
            logger.info(f"Updating existing extraction experiment {experiment_id} with template processing")
            
            update_query = text("""
                UPDATE extraction_experiments 
                SET template_processing_results_json = :template_results,
                    template_processing_completed_at = NOW()
                WHERE id = :experiment_id
            """)
            
            db.execute(update_query, {
                "template_results": json.dumps(request.template_processing_results),
                "experiment_id": experiment_id
            })
            
        else:
            # Create new extraction experiment entry
            logger.info(f"Creating new extraction experiment for deck {request.pitch_deck_id}")
            
            insert_query = text("""
                INSERT INTO extraction_experiments (
                    experiment_name, 
                    pitch_deck_ids, 
                    extraction_type,
                    text_model_used,
                    extraction_prompt,
                    results_json,
                    template_processing_results_json,
                    template_processing_completed_at,
                    created_at
                ) VALUES (
                    :experiment_name,
                    :pitch_deck_ids,
                    'startup_upload',
                    'auto',
                    'Automatic startup upload processing',
                    '{}',
                    :template_results,
                    NOW(),
                    NOW()
                )
            """)
            
            db.execute(insert_query, {
                "experiment_name": request.experiment_name,
                "pitch_deck_ids": f"{{{request.pitch_deck_id}}}",  # PostgreSQL array format
                "template_results": json.dumps(request.template_processing_results)
            })
        
        db.commit()
        
        logger.info(f"✅ Successfully saved template processing results for deck {request.pitch_deck_id}")
        
        return {
            "success": True,
            "message": f"Template processing results saved for deck {request.pitch_deck_id}",
            "pitch_deck_id": request.pitch_deck_id,
            "experiment_name": request.experiment_name
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error saving template processing results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save template processing results: {str(e)}"
        )