"""
Dojo API Endpoints
Handles training data uploads and management for GPs
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
import os
import zipfile
import shutil
import logging
from pathlib import Path
import uuid
import json
from datetime import datetime
from sqlalchemy import func, text

from ..db.database import get_db
from ..db.models import User, PitchDeck
from .auth import get_current_user

# Import for extraction testing functionality
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dojo", tags=["dojo"])

# Dojo configuration
DOJO_PATH = "/mnt/CPU-GPU/dojo"
MAX_ZIP_SIZE = 1024 * 1024 * 1024  # 1GB
ALLOWED_EXTENSIONS = {'.pdf'}

def ensure_dojo_directory():
    """Ensure dojo directory exists"""
    os.makedirs(DOJO_PATH, exist_ok=True)
    logger.info(f"Dojo directory ensured at: {DOJO_PATH}")

async def extract_dojo_zip_only(zip_file_path: str, uploaded_by: int, db: Session):
    """Extract dojo zip file and create database entries (no AI processing)"""
    try:
        logger.info(f"Extracting dojo zip file: {zip_file_path}")
        
        # Extract zip file
        extract_dir = os.path.join(DOJO_PATH, f"extract_{uuid.uuid4().hex}")
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Find all PDF files in extracted content
        pdf_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(pdf_files)} PDF files in dojo upload")
        
        # Process each PDF file (create DB entries only, no AI processing)
        processed_count = 0
        for pdf_path in pdf_files:
            try:
                # Generate unique filename
                original_name = os.path.basename(pdf_path)
                unique_name = f"{uuid.uuid4().hex}_{original_name}"
                
                # Move to dojo directory
                final_path = os.path.join(DOJO_PATH, unique_name)
                shutil.move(pdf_path, final_path)
                
                # Create database record (ready for manual processing)
                pitch_deck = PitchDeck(
                    user_id=uploaded_by,
                    company_id="dojo",
                    file_name=original_name,
                    file_path=f"dojo/{unique_name}",
                    data_source="dojo",
                    processing_status="pending"  # Ready for manual AI processing
                )
                db.add(pitch_deck)
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing PDF {pdf_path}: {e}")
                continue
        
        # Commit all database changes
        db.commit()
        
        # Clean up
        shutil.rmtree(extract_dir, ignore_errors=True)
        os.remove(zip_file_path)
        
        logger.info(f"Successfully extracted {processed_count} PDF files from dojo upload")
        
    except Exception as e:
        logger.error(f"Error extracting dojo zip file: {e}")
        # Clean up on error
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)

async def process_dojo_zip(zip_file_path: str, uploaded_by: int, db: Session):
    """Background task to process uploaded dojo zip file"""
    try:
        logger.info(f"Processing dojo zip file: {zip_file_path}")
        
        # Extract zip file
        extract_dir = os.path.join(DOJO_PATH, f"extract_{uuid.uuid4().hex}")
        os.makedirs(extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Find all PDF files in extracted content
        pdf_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(pdf_files)} PDF files in dojo upload")
        
        # Process each PDF file
        processed_count = 0
        for pdf_path in pdf_files:
            try:
                # Generate unique filename
                original_name = os.path.basename(pdf_path)
                unique_name = f"{uuid.uuid4().hex}_{original_name}"
                
                # Move to dojo directory
                final_path = os.path.join(DOJO_PATH, unique_name)
                shutil.move(pdf_path, final_path)
                
                # Create database record
                pitch_deck = PitchDeck(
                    user_id=uploaded_by,
                    company_id="dojo",
                    file_name=original_name,
                    file_path=f"dojo/{unique_name}",
                    data_source="dojo",
                    processing_status="pending"
                )
                db.add(pitch_deck)
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing PDF {pdf_path}: {e}")
                continue
        
        # Commit all database changes
        db.commit()
        
        # Clean up
        shutil.rmtree(extract_dir, ignore_errors=True)
        os.remove(zip_file_path)
        
        logger.info(f"Successfully processed {processed_count} PDF files from dojo upload")
        
    except Exception as e:
        logger.error(f"Error processing dojo zip file: {e}")
        # Clean up on error
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)

@router.post("/upload")
async def upload_dojo_zip(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload and process dojo training data zip file"""
    try:
        # Only GPs can upload dojo data
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can upload dojo training data"
            )
        
        # Validate file
        if not file.filename.lower().endswith('.zip'):
            raise HTTPException(
                status_code=400,
                detail="Only ZIP files are allowed"
            )
        
        # Check file size
        file_size = 0
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_ZIP_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum limit of {MAX_ZIP_SIZE // (1024*1024)} MB"
            )
        
        # Ensure dojo directory exists
        ensure_dojo_directory()
        
        # Save uploaded file temporarily
        temp_file_path = os.path.join(DOJO_PATH, f"temp_{uuid.uuid4().hex}.zip")
        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(content)
        
        # Extract ZIP file immediately (but don't do AI processing)
        background_tasks.add_task(
            extract_dojo_zip_only,
            temp_file_path,
            current_user.id,
            db
        )
        
        logger.info(f"Dojo zip upload initiated by {current_user.email}: {file.filename} ({file_size} bytes)")
        
        return {
            "message": "Dojo training data uploaded successfully",
            "filename": file.filename,
            "size": file_size,
            "status": "extracting"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading dojo zip file: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to upload dojo training data"
        )

@router.get("/files")
async def list_dojo_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all dojo training files"""
    try:
        # Only GPs can view dojo data
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can view dojo training data"
            )
        
        # Get all dojo files from database
        dojo_files = db.query(PitchDeck).filter(
            PitchDeck.data_source == "dojo"
        ).order_by(PitchDeck.created_at.desc()).all()
        
        files_data = []
        for file in dojo_files:
            files_data.append({
                "id": file.id,
                "filename": file.file_name,
                "file_path": file.file_path,
                "processing_status": file.processing_status,
                "ai_extracted_startup_name": file.ai_extracted_startup_name,
                "created_at": file.created_at.isoformat() if file.created_at else None,
                "has_results": bool(file.ai_analysis_results)
            })
        
        return {
            "files": files_data,
            "total_count": len(files_data),
            "directory": DOJO_PATH
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing dojo files: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list dojo training data"
        )

@router.delete("/files/{file_id}")
async def delete_dojo_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a dojo training file"""
    try:
        # Only GPs can delete dojo data
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can delete dojo training data"
            )
        
        # Find the file
        dojo_file = db.query(PitchDeck).filter(
            PitchDeck.id == file_id,
            PitchDeck.data_source == "dojo"
        ).first()
        
        if not dojo_file:
            raise HTTPException(
                status_code=404,
                detail="Dojo file not found"
            )
        
        # Delete physical file
        if dojo_file.file_path:
            full_path = os.path.join("/mnt/CPU-GPU", dojo_file.file_path)
            if os.path.exists(full_path):
                os.remove(full_path)
        
        # Delete database record
        db.delete(dojo_file)
        db.commit()
        
        logger.info(f"Deleted dojo file {file_id}: {dojo_file.file_name}")
        
        return {
            "message": "Dojo file deleted successfully",
            "file_id": file_id,
            "filename": dojo_file.file_name
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting dojo file {file_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete dojo file"
        )

@router.get("/stats")
async def get_dojo_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get dojo training data statistics"""
    try:
        # Only GPs can view dojo stats
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can view dojo statistics"
            )
        
        # Get counts using separate queries (SQLAlchemy compatibility)
        total_files = db.query(PitchDeck).filter(PitchDeck.data_source == "dojo").count()
        processed_files = db.query(PitchDeck).filter(
            PitchDeck.data_source == "dojo",
            PitchDeck.processing_status == 'completed'
        ).count()
        pending_files = db.query(PitchDeck).filter(
            PitchDeck.data_source == "dojo",
            PitchDeck.processing_status == 'pending'
        ).count()
        failed_files = db.query(PitchDeck).filter(
            PitchDeck.data_source == "dojo",
            PitchDeck.processing_status == 'failed'
        ).count()
        
        # Debug: Log actual records to understand the issue
        all_dojo_files = db.query(PitchDeck).filter(PitchDeck.data_source == "dojo").all()
        logger.info(f"Debug dojo stats: Found {len(all_dojo_files)} dojo files")
        for file in all_dojo_files:
            logger.info(f"  File: {file.file_name} | Status: {file.processing_status} | ID: {file.id}")
        
        return {
            "total_files": total_files,
            "processed_files": processed_files,
            "pending_files": pending_files,
            "failed_files": failed_files,
            "directory": DOJO_PATH
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting dojo stats: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get dojo statistics"
        )


# ==================== EXTRACTION TESTING FUNCTIONALITY ====================

class ExtractionSampleRequest(BaseModel):
    sample_size: int = 10

class VisualAnalysisRequest(BaseModel):
    deck_ids: List[int]
    vision_model: str
    analysis_prompt: str

class ExtractionTestRequest(BaseModel):
    experiment_name: str
    deck_ids: List[int]
    text_model: str
    extraction_prompt: str
    use_cached_visual: bool = True

@router.post("/extraction-test/sample")
async def create_extraction_sample(
    request: ExtractionSampleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a random sample of dojo decks for extraction testing"""
    try:
        # Only GPs can create extraction test samples
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can create extraction test samples"
            )
        
        # Get random sample of dojo files
        sample_decks = db.query(PitchDeck).filter(
            PitchDeck.data_source == "dojo"
        ).order_by(func.random()).limit(request.sample_size).all()
        
        if not sample_decks:
            raise HTTPException(
                status_code=404,
                detail="No dojo files available for sampling"
            )
        
        sample_data = []
        for deck in sample_decks:
            # Check if visual analysis is cached
            visual_cache_exists = db.execute(text(
                "SELECT COUNT(*) FROM visual_analysis_cache WHERE pitch_deck_id = :deck_id"
            ), {"deck_id": deck.id}).scalar()
            
            sample_data.append({
                "id": deck.id,
                "filename": deck.file_name,
                "file_path": deck.file_path,
                "processing_status": deck.processing_status,
                "has_visual_cache": visual_cache_exists > 0,
                "created_at": deck.created_at.isoformat() if deck.created_at else None
            })
        
        logger.info(f"Created extraction test sample of {len(sample_data)} decks for {current_user.email}")
        
        return {
            "sample": sample_data,
            "sample_size": len(sample_data),
            "requested_size": request.sample_size
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating extraction sample: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to create extraction test sample"
        )

@router.post("/extraction-test/run-visual-analysis")
async def run_visual_analysis_batch(
    request: VisualAnalysisRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Run visual analysis on sample decks and cache results"""
    try:
        # Only GPs can run visual analysis
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can run visual analysis"
            )
        
        # Validate deck IDs exist and are dojo files
        decks = db.query(PitchDeck).filter(
            PitchDeck.id.in_(request.deck_ids),
            PitchDeck.data_source == "dojo"
        ).all()
        
        if len(decks) != len(request.deck_ids):
            raise HTTPException(
                status_code=400,
                detail="Some deck IDs not found or not dojo files"
            )
        
        # Check which decks already have cached analysis
        cached_count = 0
        new_analysis_needed = []
        
        for deck in decks:
            cache_exists = db.execute(text(
                "SELECT id FROM visual_analysis_cache WHERE pitch_deck_id = :deck_id AND vision_model_used = :model AND prompt_used = :prompt"
            ), {"deck_id": deck.id, "model": request.vision_model, "prompt": request.analysis_prompt}).scalar()
            
            if cache_exists:
                cached_count += 1
            else:
                new_analysis_needed.append(deck)
        
        # Start background task for visual analysis
        if new_analysis_needed:
            background_tasks.add_task(
                process_visual_analysis_batch,
                [deck.id for deck in new_analysis_needed],
                request.vision_model,
                request.analysis_prompt,
                db
            )
        
        logger.info(f"Visual analysis batch started: {len(new_analysis_needed)} new, {cached_count} cached")
        
        return {
            "message": "Visual analysis batch initiated",
            "total_decks": len(request.deck_ids),
            "cached_count": cached_count,
            "new_analysis_count": len(new_analysis_needed),
            "status": "processing" if new_analysis_needed else "all_cached"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running visual analysis batch: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to run visual analysis batch"
        )

@router.post("/extraction-test/run-offering-extraction")
async def test_offering_extraction(
    request: ExtractionTestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Test company offering extraction with different models/prompts"""
    try:
        # Only GPs can run extraction tests
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can run extraction tests"
            )
        
        # Validate deck IDs exist and are dojo files
        decks = db.query(PitchDeck).filter(
            PitchDeck.id.in_(request.deck_ids),
            PitchDeck.data_source == "dojo"
        ).all()
        
        if len(decks) != len(request.deck_ids):
            raise HTTPException(
                status_code=400,
                detail="Some deck IDs not found or not dojo files"
            )
        
        extraction_results = []
        
        for deck in decks:
            try:
                # Get visual analysis (cached or fresh)
                visual_analysis = None
                if request.use_cached_visual:
                    # Try to get cached visual analysis
                    cache_result = db.execute(text(
                        "SELECT analysis_result_json FROM visual_analysis_cache WHERE pitch_deck_id = :deck_id ORDER BY created_at DESC LIMIT 1"
                    ), {"deck_id": deck.id}).fetchone()
                    
                    if cache_result:
                        visual_analysis = json.loads(cache_result[0])
                
                if not visual_analysis:
                    # TODO: Integrate with GPU pipeline to get fresh visual analysis
                    # For now, we'll create a placeholder
                    visual_analysis = {
                        "visual_analysis_results": [
                            {"page_number": 1, "description": "Visual analysis not available", "deck_name": deck.file_name}
                        ]
                    }
                
                # TODO: Integrate with GPU pipeline for offering extraction
                # For now, create placeholder extraction result
                offering_result = f"[PLACEHOLDER] Company offering extracted using {request.text_model} for {deck.file_name}"
                
                extraction_results.append({
                    "deck_id": deck.id,
                    "filename": deck.file_name,
                    "offering_extraction": offering_result,
                    "visual_analysis_used": len(visual_analysis.get("visual_analysis_results", [])) > 0
                })
                
            except Exception as e:
                logger.error(f"Error extracting offering for deck {deck.id}: {e}")
                extraction_results.append({
                    "deck_id": deck.id,
                    "filename": deck.file_name,
                    "offering_extraction": f"Error: {str(e)}",
                    "visual_analysis_used": False
                })
        
        # Store experiment results
        experiment_data = {
            "experiment_name": request.experiment_name,
            "extraction_type": "company_offering",
            "text_model_used": request.text_model,
            "extraction_prompt": request.extraction_prompt,
            "results": extraction_results,
            "total_decks": len(extraction_results),
            "successful_extractions": len([r for r in extraction_results if not r["offering_extraction"].startswith("Error:")]),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Save experiment to database
        db.execute(text(
            "INSERT INTO extraction_experiments (experiment_name, pitch_deck_ids, extraction_type, text_model_used, extraction_prompt, results_json) VALUES (:name, :deck_ids, :type, :model, :prompt, :results)"
        ), {
            "name": request.experiment_name,
            "deck_ids": request.deck_ids,
            "type": "company_offering", 
            "model": request.text_model,
            "prompt": request.extraction_prompt,
            "results": json.dumps(experiment_data)
        })
        db.commit()
        
        logger.info(f"Extraction test completed: {request.experiment_name}")
        
        return experiment_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running extraction test: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to run extraction test"
        )

@router.get("/extraction-test/experiments")
async def get_extraction_experiments(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all extraction experiments for comparison"""
    try:
        # Only GPs can view extraction experiments
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can view extraction experiments"
            )
        
        experiments = db.execute(text(
            "SELECT id, experiment_name, extraction_type, text_model_used, created_at, results_json FROM extraction_experiments ORDER BY created_at DESC"
        )).fetchall()
        
        experiment_data = []
        for exp in experiments:
            results_data = json.loads(exp[5]) if exp[5] else {}
            experiment_data.append({
                "id": exp[0],
                "experiment_name": exp[1],
                "extraction_type": exp[2], 
                "text_model_used": exp[3],
                "created_at": exp[4].isoformat(),
                "total_decks": results_data.get("total_decks", 0),
                "successful_extractions": results_data.get("successful_extractions", 0)
            })
        
        return {
            "experiments": experiment_data,
            "total_experiments": len(experiment_data)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting extraction experiments: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get extraction experiments"
        )

async def process_visual_analysis_batch(deck_ids: List[int], vision_model: str, analysis_prompt: str, db: Session):
    """Background task to process visual analysis for multiple decks"""
    try:
        logger.info(f"Starting visual analysis batch for {len(deck_ids)} decks")
        
        for deck_id in deck_ids:
            deck = db.query(PitchDeck).filter(PitchDeck.id == deck_id).first()
            if not deck:
                continue
            
            try:
                # TODO: Integrate with actual GPU pipeline
                # For now, create placeholder analysis result
                analysis_result = {
                    "visual_analysis_results": [
                        {
                            "page_number": 1,
                            "slide_image_path": f"/path/to/{deck.file_name}_page_1.jpg",
                            "description": f"[PLACEHOLDER] Visual analysis of {deck.file_name} using {vision_model}",
                            "deck_name": deck.file_name
                        }
                    ]
                }
                
                # Cache the visual analysis result
                db.execute(text(
                    "INSERT INTO visual_analysis_cache (pitch_deck_id, analysis_result_json, vision_model_used, prompt_used) VALUES (:deck_id, :result, :model, :prompt) ON CONFLICT (pitch_deck_id, vision_model_used, prompt_used) DO UPDATE SET analysis_result_json = :result, created_at = CURRENT_TIMESTAMP"
                ), {
                    "deck_id": deck_id,
                    "result": json.dumps(analysis_result),
                    "model": vision_model,
                    "prompt": analysis_prompt
                })
                
                logger.info(f"Cached visual analysis for deck {deck_id}")
                
            except Exception as e:
                logger.error(f"Error processing visual analysis for deck {deck_id}: {e}")
                continue
        
        db.commit()
        logger.info(f"Visual analysis batch completed for {len(deck_ids)} decks")
        
    except Exception as e:
        logger.error(f"Error in visual analysis batch processing: {e}")