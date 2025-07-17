
from fastapi import APIRouter, HTTPException, UploadFile, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from ..core.volume_storage import volume_storage
from ..core.config import settings
from ..db.models import User, PitchDeck
from ..db.database import get_db
from .auth import get_current_user
import uuid
import logging
import os
import json
import glob

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

async def trigger_gpu_processing(pitch_deck_id: int, file_path: str):
    """Background task to trigger HTTP-based GPU processing"""
    from ..services.gpu_http_client import gpu_http_client
    from ..db.database import SessionLocal
    
    logger.info(f"BACKGROUND TASK START: HTTP-based GPU processing triggered for pitch deck {pitch_deck_id} at {file_path}")
    
    # Create database session for background task
    db = SessionLocal()
    try:
        # Update status to processing
        pitch_deck = db.query(PitchDeck).filter(PitchDeck.id == pitch_deck_id).first()
        if pitch_deck:
            pitch_deck.processing_status = "processing"
            db.commit()
            logger.info(f"Updated pitch deck {pitch_deck_id} status to 'processing'")
        
        logger.info(f"Calling gpu_http_client.process_pdf for pitch deck {pitch_deck_id}")
        results = await gpu_http_client.process_pdf(pitch_deck_id, file_path)
        
        if results.get("success"):
            logger.info(f"HTTP-based GPU processing completed successfully for pitch deck {pitch_deck_id}")
            logger.info(f"Results file: {results.get('results_file')}")
            
            # Update status to completed
            if pitch_deck:
                pitch_deck.processing_status = "completed"
                db.commit()
                logger.info(f"Updated pitch deck {pitch_deck_id} status to 'completed'")
        else:
            logger.error(f"HTTP-based GPU processing failed for pitch deck {pitch_deck_id}: {results.get('error')}")
            
            # Update status to failed
            if pitch_deck:
                pitch_deck.processing_status = "failed"
                db.commit()
                logger.info(f"Updated pitch deck {pitch_deck_id} status to 'failed'")
            
    except Exception as e:
        logger.error(f"BACKGROUND TASK EXCEPTION for pitch deck {pitch_deck_id}: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        
        # Update status to failed on exception
        try:
            pitch_deck = db.query(PitchDeck).filter(PitchDeck.id == pitch_deck_id).first()
            if pitch_deck:
                pitch_deck.processing_status = "failed"
                db.commit()
                logger.info(f"Updated pitch deck {pitch_deck_id} status to 'failed' due to exception")
        except Exception as db_error:
            logger.error(f"Failed to update database status: {db_error}")
    finally:
        db.close()

@router.post("/upload")
async def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
        # Use the same company_id generation logic as in projects.py
        from ..api.projects import get_company_id_from_user
        company_id = get_company_id_from_user(current_user)
        pitch_deck = PitchDeck(
            user_id=current_user.id,
            company_id=company_id,
            file_name=file.filename,
            file_path=file_path,
            processing_status="processing"  # Start with processing for better UX
        )
        db.add(pitch_deck)
        db.commit()
        db.refresh(pitch_deck)
        
        # Trigger GPU processing in background
        background_tasks.add_task(trigger_gpu_processing, pitch_deck.id, file_path)
        
        logger.info(f"Document uploaded: {file.filename} for user {current_user.email}")
        
        return {
            "message": "Document uploaded successfully",
            "filename": file.filename,
            "pitch_deck_id": pitch_deck.id,
            "file_path": file_path,
            "processing_status": "processing"  # Return processing status immediately
        }
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/processing-status/{pitch_deck_id}")
async def get_processing_status(
    pitch_deck_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get processing status for a pitch deck"""
    pitch_deck = db.query(PitchDeck).filter(PitchDeck.id == pitch_deck_id).first()
    if not pitch_deck:
        raise HTTPException(status_code=404, detail="Pitch deck not found")
    
    # Check if user owns this deck or is a GP
    user_company_id = current_user.email.split('@')[0]
    if (pitch_deck.user_id != current_user.id and 
        pitch_deck.company_id != user_company_id and 
        current_user.role != "gp"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return {
        "pitch_deck_id": pitch_deck_id,
        "processing_status": pitch_deck.processing_status,
        "file_name": pitch_deck.file_name,
        "created_at": pitch_deck.created_at
    }

@router.get("/results/{pitch_deck_id}")
async def get_processing_results(
    pitch_deck_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get AI processing results for a pitch deck"""
    pitch_deck = db.query(PitchDeck).filter(PitchDeck.id == pitch_deck_id).first()
    if not pitch_deck:
        raise HTTPException(status_code=404, detail="Pitch deck not found")
    
    # Check if user owns this deck or is a GP
    user_company_id = current_user.email.split('@')[0]
    if (pitch_deck.user_id != current_user.id and 
        pitch_deck.company_id != user_company_id and 
        current_user.role != "gp"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    if pitch_deck.processing_status != "completed":
        raise HTTPException(status_code=400, detail="Processing not completed yet")
    
    # Get results from database first
    logger.info(f"Checking pitch deck {pitch_deck_id} for stored results")
    logger.info(f"Pitch deck attributes: {dir(pitch_deck)}")
    
    # Check if the column exists
    if hasattr(pitch_deck, 'ai_analysis_results') and pitch_deck.ai_analysis_results:
        try:
            results = json.loads(pitch_deck.ai_analysis_results)
            logger.info(f"Found stored results for pitch deck {pitch_deck_id}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse stored results for pitch deck {pitch_deck_id}")
            results = None
    else:
        logger.info(f"No stored results found for pitch deck {pitch_deck_id}")
        results = None
    
    # If no results in database, try to find and load from file system
    if not results:
        logger.info(f"No results in database for pitch deck {pitch_deck_id}, checking file system")
        
        # Find the result file using job format: job_{pitch_deck_id}_*_results.json
        results_dir = f"{settings.SHARED_FILESYSTEM_MOUNT_PATH}/results"
        pattern = f"{results_dir}/job_{pitch_deck_id}_*_results.json"
        result_files = glob.glob(pattern)
        
        if result_files:
            # Use the most recent result file
            result_file = max(result_files, key=os.path.getctime)
            logger.info(f"Found result file: {result_file}")
            
            try:
                with open(result_file, 'r') as f:
                    results = json.load(f)
                
                # Store results in database for future use
                pitch_deck.ai_analysis_results = json.dumps(results)
                db.commit()
                logger.info(f"Loaded and stored results for pitch deck {pitch_deck_id}")
                
            except Exception as e:
                logger.error(f"Error reading result file {result_file}: {e}")
                raise HTTPException(status_code=500, detail=f"Error reading results: {str(e)}")
        else:
            logger.error(f"No result files found for pitch deck {pitch_deck_id}")
            raise HTTPException(status_code=404, detail="Results not found")
    
    return {
        "pitch_deck_id": pitch_deck_id,
        "file_name": pitch_deck.file_name,
        "processing_status": pitch_deck.processing_status,
        "results": results
    }
