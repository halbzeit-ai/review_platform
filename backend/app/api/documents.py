
from fastapi import APIRouter, HTTPException, UploadFile, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
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
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

async def create_project_from_pitch_deck(pitch_deck: PitchDeck, db: Session):
    """Create a project automatically from a successfully processed pitch deck"""
    try:
        # Check if project already exists for this company
        existing_project = db.execute(text("""
            SELECT id FROM projects 
            WHERE company_id = :company_id AND is_active = TRUE
            LIMIT 1
        """), {"company_id": pitch_deck.company_id}).fetchone()
        
        if existing_project:
            logger.info(f"Project already exists for company {pitch_deck.company_id}, adding deck as document")
            project_id = existing_project[0]
        else:
            # Extract data from results file if available
            company_offering = None
            funding_sought = None
            classification_data = None
            
            if pitch_deck.results_file_path:
                try:
                    results_path = pitch_deck.results_file_path
                    if not results_path.startswith('/'):
                        results_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, results_path)
                    
                    if os.path.exists(results_path):
                        with open(results_path, 'r') as f:
                            results_data = json.load(f)
                            
                        # Extract relevant information
                        company_offering = results_data.get("company_offering", "")[:2000]  # Limit length
                        funding_sought = results_data.get("funding_sought", "")
                        classification_data = results_data.get("classification", {})
                        
                        logger.info(f"Extracted data from results: offering={bool(company_offering)}, funding={bool(funding_sought)}")
                        
                except Exception as e:
                    logger.warning(f"Could not extract data from results file: {e}")
            
            # Create project
            project_name = f"{pitch_deck.company_id} - Initial Review"
            
            project_insert = text("""
                INSERT INTO projects (
                    company_id, project_name, funding_round, funding_sought, 
                    company_offering, project_metadata, is_test, is_active,
                    created_at, updated_at
                )
                VALUES (:company_id, :project_name, :funding_round, :funding_sought,
                        :company_offering, :metadata, FALSE, TRUE,
                        :created_at, :updated_at)
                RETURNING id
            """)
            
            metadata = {
                "created_from_pitch_deck": True,
                "pitch_deck_id": pitch_deck.id,
                "original_filename": pitch_deck.file_name,
                "auto_created": True,
                "created_at": datetime.utcnow().isoformat()
            }
            
            if classification_data:
                metadata["classification"] = classification_data
            
            project_result = db.execute(project_insert, {
                "company_id": pitch_deck.company_id,
                "project_name": project_name,
                "funding_round": "initial",
                "funding_sought": funding_sought or "TBD",
                "company_offering": company_offering or "Analysis in progress",
                "metadata": json.dumps(metadata),
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            
            project_id = project_result.fetchone()[0]
            logger.info(f"Created project {project_id} for company {pitch_deck.company_id}")
        
        # Add pitch deck as project document
        deck_doc_insert = text("""
            INSERT INTO project_documents (
                project_id, document_type, file_name, file_path,
                original_filename, processing_status, uploaded_by,
                upload_date, is_active
            )
            VALUES (:project_id, 'pitch_deck', :file_name, :file_path,
                    :original_filename, 'completed', :uploaded_by,
                    :upload_date, TRUE)
        """)
        
        db.execute(deck_doc_insert, {
            "project_id": project_id,
            "file_name": pitch_deck.file_name,
            "file_path": pitch_deck.file_path,
            "original_filename": pitch_deck.file_name,
            "uploaded_by": pitch_deck.user_id,
            "upload_date": datetime.utcnow()
        })
        
        # Add results file if available
        if pitch_deck.results_file_path:
            results_doc_insert = text("""
                INSERT INTO project_documents (
                    project_id, document_type, file_name, file_path,
                    original_filename, processing_status, uploaded_by,
                    upload_date, is_active
                )
                VALUES (:project_id, 'analysis_results', :file_name, :file_path,
                        :original_filename, 'completed', :uploaded_by,
                        :upload_date, TRUE)
            """)
            
            results_filename = f"{pitch_deck.company_id}_analysis_results.json"
            db.execute(results_doc_insert, {
                "project_id": project_id,
                "file_name": results_filename,
                "file_path": pitch_deck.results_file_path,
                "original_filename": results_filename,
                "uploaded_by": pitch_deck.user_id,
                "upload_date": datetime.utcnow()
            })
            
            logger.info(f"Added documents to project {project_id}")
        
        db.commit()
        logger.info(f"Successfully created/updated project for pitch deck {pitch_deck.id}")
        
    except Exception as e:
        logger.error(f"Failed to create project from pitch deck {pitch_deck.id}: {e}")
        db.rollback()

async def trigger_gpu_processing(pitch_deck_id: int, file_path: str, company_id: str):
    """Background task to trigger HTTP-based GPU processing"""
    from ..services.gpu_http_client import gpu_http_client
    from ..db.database import SessionLocal
    
    logger.info(f"BACKGROUND TASK START: HTTP-based GPU processing triggered for pitch deck {pitch_deck_id} at {file_path} for company {company_id}")
    
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
        results = await gpu_http_client.process_pdf(pitch_deck_id, file_path, company_id)
        
        if results.get("success"):
            logger.info(f"HTTP-based GPU processing completed successfully for pitch deck {pitch_deck_id}")
            logger.info(f"Results file: {results.get('results_file')}")
            
            # Update status to completed
            if pitch_deck:
                pitch_deck.processing_status = "completed"
                # Store results file path if provided
                if results.get("results_path"):
                    pitch_deck.results_file_path = results.get("results_path")
                db.commit()
                logger.info(f"Updated pitch deck {pitch_deck_id} status to 'completed'")
                
                # Auto-create project from successful pitch deck processing
                await create_project_from_pitch_deck(pitch_deck, db)
            
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
        background_tasks.add_task(trigger_gpu_processing, pitch_deck.id, file_path, company_id)
        
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
    from ..api.projects import get_company_id_from_user
    user_company_id = get_company_id_from_user(current_user)
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
    from ..api.projects import get_company_id_from_user
    user_company_id = get_company_id_from_user(current_user)
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
                
                # Extract and store the startup name if available
                startup_name = results.get("startup_name")
                if startup_name:
                    pitch_deck.ai_extracted_startup_name = startup_name
                    logger.info(f"Extracted startup name from results: {startup_name}")
                
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
        "ai_extracted_startup_name": pitch_deck.ai_extracted_startup_name,
        "results": results
    }

@router.get("/processing-progress/{pitch_deck_id}")
async def get_processing_progress(
    pitch_deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get real-time processing progress for a pitch deck"""
    try:
        # Get pitch deck info
        pitch_deck = db.query(PitchDeck).filter(PitchDeck.id == pitch_deck_id).first()
        if not pitch_deck:
            raise HTTPException(status_code=404, detail="Pitch deck not found")
        
        # Check if user has access to this pitch deck
        if current_user.role == "startup" and pitch_deck.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")
        
        # Get progress from GPU server
        from ..services.gpu_http_client import gpu_http_client
        progress_info = gpu_http_client.get_processing_progress(pitch_deck_id)
        
        return {
            "pitch_deck_id": pitch_deck_id,
            "file_name": pitch_deck.file_name,
            "processing_status": pitch_deck.processing_status,
            "gpu_progress": progress_info,
            "created_at": pitch_deck.created_at.isoformat() if pitch_deck.created_at else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing progress for pitch deck {pitch_deck_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get processing progress")


@router.get("/test-endpoint")
async def test_endpoint():
    """Test endpoint without authentication"""
    logger.info("=== TEST ENDPOINT CALLED ===")
    return {"status": "success", "message": "Test endpoint works"}

@router.get("/{document_id}/thumbnail/slide/{slide_number}")
async def get_document_thumbnail(
    document_id: int,
    slide_number: int,
    db: Session = Depends(get_db)
):
    """Get thumbnail image for a specific slide of a document"""
    logger.info(f"=== THUMBNAIL REQUEST START (NO AUTH): document_id={document_id}, slide_number={slide_number} ===")
    try:
        # Get document info from project_documents table
        doc_query = text("""
            SELECT pd.id, pd.project_id, pd.file_name, pd.file_path, 
                   p.company_id
            FROM project_documents pd
            JOIN projects p ON pd.project_id = p.id
            WHERE pd.id = :document_id AND pd.is_active = TRUE
        """)
        
        doc_result = db.execute(doc_query, {"document_id": document_id}).fetchone()
        
        if not doc_result:
            logger.info(f"Document {document_id} not found in project_documents, trying pitch_decks table")
            # Fallback: try to get from pitch_decks table
            pitch_deck_query = text("""
                SELECT pd.id, pd.company_id, pd.file_name, pd.file_path
                FROM pitch_decks pd
                WHERE pd.id = :document_id
            """)
            
            pitch_deck_result = db.execute(pitch_deck_query, {"document_id": document_id}).fetchone()
            
            if not pitch_deck_result:
                logger.error(f"Document {document_id} not found in either project_documents or pitch_decks tables")
                raise HTTPException(
                    status_code=404,
                    detail="Document not found"
                )
            
            logger.info(f"Found document {document_id} in pitch_decks table")
            deck_id, company_id, file_name, file_path = pitch_deck_result
            deck_name = os.path.splitext(file_name)[0] if file_name else str(deck_id)
        else:
            logger.info(f"Found document {document_id} in project_documents table")
            doc_id, project_id, file_name, file_path, company_id = doc_result
            deck_name = os.path.splitext(file_name)[0] if file_name else str(doc_id)
        
        # TEMPORARY: Skip access control for debugging
        logger.info(f"Skipping access control for debugging - document_id={document_id}, company_id={company_id}")
        
        # Try to find slide image files in multiple possible locations
        # Clean deck name for filesystem path
        import string
        import re
        safe_deck_name = "".join(c for c in deck_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_deck_name = re.sub(r'\s+', '_', safe_deck_name)
        
        possible_locations = [
            # Project-based structure with original deck name
            os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", company_id, "analysis", deck_name),
            # Project-based structure with safe deck name
            os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", company_id, "analysis", safe_deck_name),
            # Original results-based structure (might exist from legacy processing)
            os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "results", f"job_{document_id}_{deck_name}"),
            # Original results-based structure with safe name
            os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "results", f"job_{document_id}_{safe_deck_name}"),
        ]
        
        # Look for slide image files (try different naming patterns)
        # Based on GPU processing code: slide_{page_number + 1}.jpg (no zero-padding)
        slide_patterns = [
            f"slide_{slide_number}.jpg",  # Primary pattern from GPU processing
            f"slide_{slide_number}.png",
            f"slide_{slide_number:02d}.jpg",  # Zero-padded version
            f"slide_{slide_number:02d}.png",
            f"page_{slide_number}.jpg",
            f"page_{slide_number}.png",
            f"page_{slide_number:02d}.jpg",
            f"page_{slide_number:02d}.png"
        ]
        
        image_path = None
        found_location = None
        
        for location in possible_locations:
            logger.info(f"Checking location: {location}")
            if os.path.exists(location):
                for pattern in slide_patterns:
                    potential_path = os.path.join(location, pattern)
                    if os.path.exists(potential_path):
                        image_path = potential_path
                        found_location = location
                        logger.info(f"Found slide image at: {image_path}")
                        break
                if image_path:
                    break
            else:
                logger.debug(f"Location does not exist: {location}")
        
        if not image_path:
            # Log what we actually found in the existing directories
            for location in possible_locations:
                if os.path.exists(location):
                    try:
                        files_in_dir = os.listdir(location)
                        logger.warning(f"No slide image found for slide {slide_number} in {location}. Files present: {files_in_dir}")
                    except Exception as e:
                        logger.error(f"Could not list directory {location}: {e}")
            
            raise HTTPException(
                status_code=404,
                detail=f"Thumbnail for slide {slide_number} not found"
            )
        
        # Serve the image file
        from fastapi.responses import FileResponse
        return FileResponse(
            image_path,
            media_type="image/png",
            headers={"Cache-Control": "max-age=3600"}
        )
        
    except HTTPException as he:
        logger.error(f"HTTP Exception in thumbnail endpoint: status={he.status_code}, detail={he.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error serving thumbnail for document {document_id}, slide {slide_number}: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve thumbnail"
        )
