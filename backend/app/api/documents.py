
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
    """Background task to trigger file-based GPU processing"""
    from ..services.file_based_processing import file_based_gpu_service
    
    logger.info(f"BACKGROUND TASK START: File-based GPU processing triggered for pitch deck {pitch_deck_id} at {file_path}")
    
    try:
        logger.info(f"Calling file_based_gpu_service.process_pdf_direct for pitch deck {pitch_deck_id}")
        results = await file_based_gpu_service.process_pdf_direct(pitch_deck_id, file_path)
        logger.info(f"File-based GPU processing completed successfully for pitch deck {pitch_deck_id}")
        logger.info(f"Results summary: {results.get('summary', 'No summary available')}")
    except Exception as e:
        logger.error(f"BACKGROUND TASK EXCEPTION for pitch deck {pitch_deck_id}: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

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
        pitch_deck = PitchDeck(
            user_id=current_user.id,
            file_name=file.filename,
            file_path=file_path,
            processing_status="pending"
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
            "processing_status": "pending"
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
    if pitch_deck.user_id != current_user.id and current_user.role != "gp":
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
    if pitch_deck.user_id != current_user.id and current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Access denied")
    
    if pitch_deck.processing_status != "completed":
        raise HTTPException(status_code=400, detail="Processing not completed yet")
    
    # Get results from volume storage - use flat filename format
    flat_filename = pitch_deck.file_path.replace('/', '_').replace('.pdf', '_results.json')
    results_path = f"results/{flat_filename}"
    results = volume_storage.get_results(results_path)
    
    if not results:
        raise HTTPException(status_code=404, detail="Results not found")
    
    return {
        "pitch_deck_id": pitch_deck_id,
        "file_name": pitch_deck.file_name,
        "processing_status": pitch_deck.processing_status,
        "results": results
    }
