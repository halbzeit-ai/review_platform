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
import glob
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

# In-memory progress tracking for current deck processing
progress_tracker = {
    "step2": {
        "current_deck": "", 
        "status": "idle", 
        "progress": 0, 
        "total": 0,
        "start_time": None,
        "completion_time": None,
        "processing_times": [],
        "current_deck_start_time": None
    },
    "step3": {"current_deck": "", "status": "idle", "progress": 0, "total": 0}, 
    "step4": {"current_deck": "", "current_chapter": "", "status": "idle", "progress": 0, "total": 0}
}

# Dojo configuration
# Use environment-aware path from settings with unified structure
from ..core.config import settings
import hashlib

DOJO_BASE_PATH = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", "dojo")
DOJO_UPLOADS_PATH = os.path.join(DOJO_BASE_PATH, "uploads")
DOJO_ANALYSIS_PATH = os.path.join(DOJO_BASE_PATH, "analysis")
DOJO_EXPORTS_PATH = os.path.join(DOJO_BASE_PATH, "exports")
MAX_ZIP_SIZE = 1024 * 1024 * 1024  # 1GB
ALLOWED_EXTENSIONS = {'.pdf'}

def ensure_dojo_directories():
    """Ensure unified dojo directory structure exists"""
    os.makedirs(DOJO_UPLOADS_PATH, exist_ok=True)
    os.makedirs(DOJO_ANALYSIS_PATH, exist_ok=True)
    os.makedirs(DOJO_EXPORTS_PATH, exist_ok=True)
    logger.info(f"Dojo directories ensured at: {DOJO_BASE_PATH}")

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def check_duplicate_file(db: Session, file_name: str, file_hash: str) -> Optional[int]:
    """Check if file already exists by name or hash. Returns pitch_deck_id if found."""
    existing = db.query(PitchDeck).filter(
        PitchDeck.data_source == "dojo",
        (PitchDeck.file_name == file_name) | (PitchDeck.file_hash == file_hash)
    ).first()
    return existing.id if existing else None

async def extract_dojo_zip_only(zip_file_path: str, uploaded_by: int, db: Session, original_filename: str = None):
    """Extract dojo zip file and create database entries (no AI processing)"""
    try:
        logger.info(f"Extracting dojo zip file: {zip_file_path}")
        
        # Get original ZIP filename for database storage
        zip_filename = original_filename if original_filename else os.path.basename(zip_file_path)
        
        # Extract zip file
        extract_dir = os.path.join(DOJO_BASE_PATH, f"extract_{uuid.uuid4().hex}")
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
                
                # Move to dojo uploads directory
                final_path = os.path.join(DOJO_UPLOADS_PATH, unique_name)
                shutil.move(pdf_path, final_path)
                
                # Create database record (ready for manual processing)
                pitch_deck = PitchDeck(
                    user_id=uploaded_by,
                    company_id="dojo",
                    file_name=original_name,
                    file_path=f"projects/dojo/uploads/{unique_name}",
                    data_source="dojo",
                    zip_filename=zip_filename,
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

async def process_dojo_zip(zip_file_path: str, uploaded_by: int, db: Session, original_filename: str = None):
    """Background task to process uploaded dojo zip file"""
    try:
        logger.info(f"Processing dojo zip file: {zip_file_path}")
        
        # Get original ZIP filename for database storage
        zip_filename = original_filename if original_filename else os.path.basename(zip_file_path)
        
        # Extract zip file
        extract_dir = os.path.join(DOJO_BASE_PATH, f"extract_{uuid.uuid4().hex}")
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
                
                # Move to dojo uploads directory
                final_path = os.path.join(DOJO_UPLOADS_PATH, unique_name)
                shutil.move(pdf_path, final_path)
                
                # Create database record
                pitch_deck = PitchDeck(
                    user_id=uploaded_by,
                    company_id="dojo",
                    file_name=original_name,
                    file_path=f"projects/dojo/uploads/{unique_name}",
                    data_source="dojo",
                    zip_filename=zip_filename,
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
        
        # Ensure dojo directories exist
        ensure_dojo_directories()
        
        # Save uploaded file temporarily
        temp_file_path = os.path.join(DOJO_BASE_PATH, f"temp_{uuid.uuid4().hex}.zip")
        with open(temp_file_path, 'wb') as temp_file:
            temp_file.write(content)
        
        # Extract ZIP file immediately (but don't do AI processing)
        background_tasks.add_task(
            extract_dojo_zip_only,
            temp_file_path,
            current_user.id,
            db,
            file.filename  # Pass original filename
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

@router.post("/upload-enhanced")
async def upload_dojo_zip_enhanced(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload dojo training data with enhanced duplicate detection"""
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
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_ZIP_SIZE:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size is {MAX_ZIP_SIZE // (1024*1024)}MB"
            )
        
        # Ensure dojo directories exist
        ensure_dojo_directories()
        
        # Save uploaded file temporarily
        temp_path = os.path.join(DOJO_BASE_PATH, f"temp_{uuid.uuid4().hex}_{file.filename}")
        with open(temp_path, "wb") as f:
            f.write(content)
        
        # Import enhanced extraction function
        from .dojo_enhanced import extract_dojo_zip_enhanced
        
        # Process ZIP file with enhanced duplicate detection
        result = await extract_dojo_zip_enhanced(
            zip_file_path=temp_path,
            uploaded_by=current_user.id,
            db=db,
            dojo_uploads_path=DOJO_UPLOADS_PATH,
            original_filename=file.filename
        )
        
        return result.to_dict()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in enhanced dojo upload: {e}")
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
                "zip_filename": file.zip_filename,
                "created_at": file.created_at.isoformat() if file.created_at else None,
                "has_results": bool(file.ai_analysis_results)
            })
        
        return {
            "files": files_data,
            "total_count": len(files_data),
            "directory": DOJO_BASE_PATH
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing dojo files: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to list dojo training data"
        )

@router.delete("/files/{file_id:int}")
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
            full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, dojo_file.file_path)
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

@router.delete("/files/all")
async def delete_all_dojo_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete all dojo PDF files from filesystem and database"""
    try:
        # Only GPs can delete all dojo data
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can delete all dojo training data"
            )
        
        # Find all dojo files
        dojo_files = db.query(PitchDeck).filter(
            PitchDeck.data_source == "dojo"
        ).all()
        
        logger.info(f"Found {len(dojo_files)} dojo files to delete")
        
        # Collect deck IDs before deletion for cache cleanup
        dojo_deck_ids = [f.id for f in dojo_files]
        
        deleted_count = 0
        deleted_files = []
        errors = []
        
        # Clear visual analysis cache BEFORE deleting the files
        if dojo_deck_ids:
            try:
                # Simple approach - delete one by one
                for deck_id in dojo_deck_ids:
                    db.execute(text("""
                        DELETE FROM visual_analysis_cache 
                        WHERE pitch_deck_id = :deck_id
                    """), {"deck_id": deck_id})
                logger.info(f"Cleared visual analysis cache for {len(dojo_deck_ids)} decks")
            except Exception as e:
                logger.warning(f"Failed to clear visual analysis cache: {e}")
                db.rollback()
                # Continue despite cache cleanup failure  # Important: rollback failed transaction
                # Continue anyway, this is not critical
        
        # Track additional cleanup stats
        deleted_images = 0
        deleted_results = 0
        deleted_projects = 0
        
        # FIRST: Delete ALL actual files in dojo directory (regardless of DB paths)
        try:
            import glob
            dojo_filesystem_files = glob.glob(os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "dojo", "*.pdf"))
            filesystem_deleted = 0
            for file_path in dojo_filesystem_files:
                try:
                    os.remove(file_path)
                    filesystem_deleted += 1
                    logger.info(f"Deleted filesystem file: {file_path}")
                except Exception as e:
                    logger.warning(f"Could not delete {file_path}: {e}")
            
            logger.info(f"Deleted {filesystem_deleted} files from filesystem")
        except Exception as e:
            logger.warning(f"Error during filesystem cleanup: {e}")
        
        for dojo_file in dojo_files:
            try:
                deck_id = dojo_file.id
                deck_name = os.path.splitext(dojo_file.file_name)[0] if dojo_file.file_name else str(deck_id)
                
                # 1. Delete original PDF file
                if dojo_file.file_path:
                    full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, dojo_file.file_path)
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        logger.info(f"Deleted PDF: {full_path}")
                    else:
                        logger.warning(f"PDF not found: {full_path}")
                
                # 2. Delete slide images from analysis directories
                analysis_base = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects")
                possible_image_dirs = [
                    os.path.join(analysis_base, "dojo", "analysis", deck_name),
                    os.path.join(analysis_base, "dojo", "analysis", deck_name.replace(' ', '_')),
                    os.path.join(analysis_base, "dojo", "analysis", f"job_{deck_id}_{deck_name}"),
                ]
                
                # Also check for UUID-prefixed directories in dojo analysis
                dojo_analysis_path = os.path.join(analysis_base, "dojo", "analysis")
                if os.path.exists(dojo_analysis_path):
                    try:
                        for dir_name in os.listdir(dojo_analysis_path):
                            if deck_name in dir_name or str(deck_id) in dir_name:
                                possible_image_dirs.append(os.path.join(dojo_analysis_path, dir_name))
                    except Exception as e:
                        logger.warning(f"Could not scan dojo analysis directory: {e}")
                
                for image_dir in possible_image_dirs:
                    if os.path.exists(image_dir):
                        try:
                            shutil.rmtree(image_dir)
                            deleted_images += 1
                            logger.info(f"Deleted image directory: {image_dir}")
                        except Exception as e:
                            logger.warning(f"Failed to delete image directory {image_dir}: {e}")
                
                # 3. Delete analysis results files
                results_dir = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "results")
                if os.path.exists(results_dir):
                    try:
                        # Look for job_<deck_id>_* files
                        result_patterns = [
                            os.path.join(results_dir, f"job_{deck_id}_*"),
                            os.path.join(results_dir, f"*_{deck_id}_*"),
                        ]
                        
                        for pattern in result_patterns:
                            for result_file in glob.glob(pattern):
                                try:
                                    os.remove(result_file)
                                    deleted_results += 1
                                    logger.info(f"Deleted result file: {result_file}")
                                except Exception as e:
                                    logger.warning(f"Failed to delete result file {result_file}: {e}")
                    except Exception as e:
                        logger.warning(f"Error scanning results directory: {e}")
                
                # Store info before deletion
                deleted_files.append({
                    "id": dojo_file.id,
                    "filename": dojo_file.file_name,
                    "file_path": dojo_file.file_path
                })
                
                # Delete database record
                db.delete(dojo_file)
                deleted_count += 1
                
            except Exception as e:
                error_msg = f"Failed to delete file {dojo_file.id} ({dojo_file.file_name}): {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)
        
        # 4. Clean up project documents that reference dojo decks
        try:
            # Find project documents that reference the deleted dojo files
            project_docs_result = db.execute(text("""
                DELETE FROM project_documents 
                WHERE file_path IN (
                    SELECT file_path FROM pitch_decks WHERE data_source = 'dojo'
                ) OR document_type = 'pitch_deck' AND file_name IN (
                    SELECT file_name FROM pitch_decks WHERE data_source = 'dojo'  
                )
            """))
            deleted_projects = project_docs_result.rowcount
            logger.info(f"Cleaned up {deleted_projects} project document references")
        except Exception as e:
            logger.warning(f"Failed to clean up project documents: {e}")
            db.rollback()
            deleted_projects = 0
        
        # 5. Clean up extraction experiment references
        try:
            # Remove any extraction experiments that reference the deleted decks
            # Simplified approach - just clear experiments that contain dojo deck references
            exp_cleanup_result = db.execute(text("""
                UPDATE extraction_experiments 
                SET template_processing_results_json = NULL
                WHERE template_processing_results_json LIKE '%"deck_id":%'
                AND template_processing_results_json LIKE '%"data_source": "dojo"%'
            """))
            logger.info(f"Cleaned up extraction experiment references")
        except Exception as e:
            logger.warning(f"Failed to clean up extraction experiments: {e}")
            db.rollback()
        
        # Commit all deletions
        try:
            db.commit()
        except Exception as e:
            logger.error(f"Failed to commit deletions: {e}")
            db.rollback()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to commit deletions: {str(e)}"
            )
        
        logger.info(f"Comprehensive dojo cleanup complete: {deleted_count} files, {deleted_images} image dirs, {deleted_results} result files, {deleted_projects} project docs")
        
        return {
            "message": f"Successfully deleted {deleted_count} dojo files and all related data",
            "deleted_count": deleted_count,
            "deleted_files": deleted_files,
            "deleted_images": deleted_images,
            "deleted_results": deleted_results,
            "deleted_projects": deleted_projects,
            "errors": errors if errors else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting all dojo files: {e}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete all dojo files: {str(e)}"
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
            "directory": DOJO_BASE_PATH
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
    existing_ids: Optional[List[int]] = None  # Re-check status for existing deck IDs
    cached_only: bool = False  # Filter to only decks with cached visual analysis

class VisualAnalysisRequest(BaseModel):
    deck_ids: List[int]
    vision_model: str
    analysis_prompt: Optional[str] = None  # Optional: will be fetched from database if not provided

class ExtractionTestRequest(BaseModel):
    experiment_name: str
    deck_ids: List[int]
    text_model: str
    extraction_prompt: Optional[str] = None  # Optional, will be looked up from database
    use_cached_visual: bool = True

class SaveExtractionExperimentRequest(BaseModel):
    experiment_name: str
    deck_ids: List[int]
    results: Dict[str, Any]  # Changed from List to Dict to handle comprehensive results
    experiment_type: str

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
        
        # Get sample of dojo files - either existing IDs or random sample
        if request.existing_ids:
            # Re-check status for existing deck IDs
            sample_decks = db.query(PitchDeck).filter(
                PitchDeck.id.in_(request.existing_ids),
                PitchDeck.data_source == "dojo"
            ).all()
        else:
            # Get random sample of dojo files
            if request.cached_only:
                # Only get decks that have cached visual analysis
                # Use a subquery to get distinct deck IDs first, then join with main table
                sample_deck_ids = db.execute(text("""
                    SELECT DISTINCT pd.id FROM pitch_decks pd
                    INNER JOIN visual_analysis_cache vac ON pd.id = vac.pitch_deck_id
                    WHERE pd.data_source = 'dojo'
                """)).fetchall()
                
                if sample_deck_ids:
                    # Get the actual deck IDs as a list
                    deck_ids = [row[0] for row in sample_deck_ids]
                    
                    # Now get random sample from these IDs using SQLAlchemy ORM
                    sample_decks = db.query(PitchDeck).filter(
                        PitchDeck.id.in_(deck_ids)
                    ).order_by(func.random()).limit(request.sample_size).all()
                else:
                    sample_decks = []
            else:
                # Get random sample from all dojo files
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

@router.get("/extraction-test/cached-count")
async def get_cached_decks_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get count of dojo decks with cached visual analysis"""
    try:
        # Only GPs can access cached count
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can access cached decks count"
            )
        
        # Count decks with cached visual analysis
        cached_count = db.execute(text("""
            SELECT COUNT(DISTINCT pd.id) FROM pitch_decks pd
            INNER JOIN visual_analysis_cache vac ON pd.id = vac.pitch_deck_id
            WHERE pd.data_source = 'dojo'
        """)).scalar()
        
        logger.info(f"Cached decks count requested by {current_user.email}: {cached_count}")
        
        return {
            "cached_count": cached_count,
            "total_dojo_decks": db.query(PitchDeck).filter(PitchDeck.data_source == "dojo").count()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting cached decks count: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get cached decks count"
        )

@router.get("/extraction-test/progress")
async def get_processing_progress(
    current_user: User = Depends(get_current_user)
):
    """Get current processing progress for all steps with enhanced timing data"""
    try:
        # Only GPs can access progress
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can access processing progress"
            )
        
        # Enhance step2 progress with calculated timing data
        step2_data = progress_tracker["step2"].copy()
        if step2_data["processing_times"]:
            # Calculate average processing time
            avg_time = sum(step2_data["processing_times"]) / len(step2_data["processing_times"])
            step2_data["average_processing_time"] = avg_time
            
            # Calculate total processing time if completed
            if step2_data.get("start_time") and step2_data.get("completion_time"):
                step2_data["total_processing_time"] = step2_data["completion_time"] - step2_data["start_time"]
            elif step2_data.get("start_time"):
                import time
                step2_data["total_processing_time"] = time.time() - step2_data["start_time"]
        
        # Enhance step3 progress with calculated timing data
        step3_data = progress_tracker["step3"].copy()
        if step3_data.get("start_time"):
            # Calculate total processing time if completed
            if step3_data.get("completion_time"):
                step3_data["total_processing_time"] = step3_data["completion_time"] - step3_data["start_time"]
                # Calculate average time per extraction type (5 types)
                step3_data["average_processing_time"] = step3_data["total_processing_time"] / 5
            else:
                import time
                step3_data["total_processing_time"] = time.time() - step3_data["start_time"]
                step3_data["average_processing_time"] = step3_data["total_processing_time"] / max(step3_data.get("progress", 1), 1)
        
        enhanced_tracker = progress_tracker.copy()
        enhanced_tracker["step2"] = step2_data
        enhanced_tracker["step3"] = step3_data
        
        return enhanced_tracker
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting processing progress: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get processing progress"
        )

@router.post("/extraction-test/update-progress")
async def update_processing_progress(
    step: str,
    current_deck: str = "",
    status: str = "idle",
    progress: int = 0,
    total: int = 0,
    current_user: User = Depends(get_current_user)
):
    """Update current processing progress - called by GPU instance"""
    try:
        # Only GPs can update progress
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can update processing progress"
            )
        
        if step in progress_tracker:
            progress_tracker[step]["current_deck"] = current_deck
            progress_tracker[step]["status"] = status
            if progress > 0:
                progress_tracker[step]["progress"] = progress
            if total > 0:
                progress_tracker[step]["total"] = total
            logger.info(f"Updated progress for {step}: {current_deck} ({status}) - {progress}/{total}")
        
        return {"success": True}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating processing progress: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to update processing progress"
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
        
        # Get analysis prompt from database if not provided
        analysis_prompt = request.analysis_prompt
        if not analysis_prompt:
            prompt_result = db.execute(text(
                "SELECT prompt_text FROM pipeline_prompts WHERE stage_name = 'image_analysis' AND is_active = TRUE LIMIT 1"
            )).fetchone()
            
            if prompt_result:
                analysis_prompt = prompt_result[0]
            else:
                # No fallback - fail explicitly
                raise HTTPException(
                    status_code=500,
                    detail="image_analysis prompt not found in pipeline_prompts table. Please add this prompt with stage_name='image_analysis'."
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
            ), {"deck_id": deck.id, "model": request.vision_model, "prompt": analysis_prompt}).scalar()
            
            if cache_exists:
                cached_count += 1
            else:
                new_analysis_needed.append(deck)
        
        # Start background task for visual analysis
        if new_analysis_needed:
            background_tasks.add_task(
                process_visual_analysis_batch,
                [deck.id for deck in new_analysis_needed],
                request.vision_model
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

class ClearCacheRequest(BaseModel):
    deck_ids: List[int]

@router.post("/extraction-test/clear-cache")
async def clear_visual_analysis_cache(
    request: ClearCacheRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear visual analysis cache for specified decks"""
    try:
        # Only GPs can clear cache
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can clear visual analysis cache"
            )
        
        if not request.deck_ids:
            raise HTTPException(
                status_code=400,
                detail="deck_ids is required"
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
        
        # Clear ALL cache entries for these decks (regardless of model/prompt combination)
        deleted_count = 0
        for deck_id in request.deck_ids:
            result = db.execute(text(
                "DELETE FROM visual_analysis_cache WHERE pitch_deck_id = :deck_id"
            ), {"deck_id": deck_id})
            deleted_count += result.rowcount
            logger.info(f"Cleared {result.rowcount} cache entries for deck {deck_id}")
        
        db.commit()
        
        logger.info(f"Cleared visual analysis cache for {len(request.deck_ids)} decks, deleted {deleted_count} cache entries")
        
        return {
            "message": f"Cleared visual analysis cache for {len(request.deck_ids)} decks",
            "cleared_decks": len(request.deck_ids),
            "deleted_cache_entries": deleted_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing visual analysis cache: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to clear visual analysis cache"
        )

@router.post("/extraction-test/clear-all-cache")
async def clear_all_visual_analysis_cache(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Clear ALL visual analysis cache entries (not just current sample)"""
    try:
        # Only GPs can clear cache
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can clear visual analysis cache"
            )
        
        # Get count before deletion for reporting
        count_result = db.execute(text("SELECT COUNT(*) FROM visual_analysis_cache")).fetchone()
        total_entries = count_result[0] if count_result else 0
        
        # Clear ALL cache entries
        result = db.execute(text("DELETE FROM visual_analysis_cache"))
        deleted_count = result.rowcount
        
        db.commit()
        
        logger.info(f"Cleared ALL visual analysis cache: {deleted_count} entries deleted")
        
        return {
            "message": f"Cleared all visual analysis cache entries",
            "deleted_cache_entries": deleted_count,
            "total_entries_before": total_entries
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error clearing all visual analysis cache: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to clear all visual analysis cache"
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
        
        # Use GPU pipeline for offering extraction
        from ..services.gpu_http_client import gpu_http_client
        
        # Collect cached visual analysis for context
        deck_visual_data = {}
        for deck in decks:
            if request.use_cached_visual:
                cache_result = db.execute(text(
                    "SELECT analysis_result_json FROM visual_analysis_cache WHERE pitch_deck_id = :deck_id ORDER BY created_at DESC LIMIT 1"
                ), {"deck_id": deck.id}).fetchone()
                
                if cache_result:
                    deck_visual_data[deck.id] = json.loads(cache_result[0])
                else:
                    logger.warning(f"No cached visual analysis found for deck {deck.id}")
        
        # Update progress tracker - start step 3 processing
        import time
        start_time = time.time()
        progress_tracker["step3"]["status"] = "processing"
        progress_tracker["step3"]["current_deck"] = "Starting offering extraction..."
        progress_tracker["step3"]["progress"] = 0
        progress_tracker["step3"]["total"] = len(decks)
        progress_tracker["step3"]["start_time"] = start_time
        progress_tracker["step3"]["processing_times"] = []
        
        # Get extraction prompt from database if not provided
        extraction_prompt = request.extraction_prompt
        if not extraction_prompt:
            prompt_result = db.execute(text(
                "SELECT prompt_text FROM pipeline_prompts WHERE stage_name = 'offering_extraction' LIMIT 1"
            )).fetchone()
            
            if not prompt_result:
                raise HTTPException(
                    status_code=500,
                    detail="offering_extraction prompt not found in pipeline_prompts table. Please add this prompt with stage_name='offering_extraction'."
                )
            
            extraction_prompt = prompt_result[0]
        
        # Call GPU pipeline for offering extraction
        gpu_result = await gpu_http_client.run_offering_extraction(
            deck_ids=request.deck_ids,
            text_model=request.text_model,
            extraction_prompt=extraction_prompt,
            use_cached_visual=request.use_cached_visual
        )
        
        if gpu_result.get("success"):
            logger.info("GPU offering extraction completed successfully")
            extraction_results = gpu_result.get("extraction_results", [])
            
            # Enhance results with local deck information
            for i, result in enumerate(extraction_results):
                deck_id = result.get("deck_id")
                if deck_id:
                    deck = next((d for d in decks if d.id == deck_id), None)
                    if deck:
                        result["filename"] = deck.file_name
                        # Update progress
                        progress_tracker["step3"]["current_deck"] = f"Processing {deck.file_name}"
                        progress_tracker["step3"]["progress"] = i + 1
                        # Check if visual analysis was available
                        result["visual_analysis_used"] = deck_id in deck_visual_data
        else:
            logger.error(f"GPU offering extraction failed: {gpu_result.get('error', 'Unknown error')}")
            # Fallback to placeholder results
            extraction_results = []
            for deck in decks:
                extraction_results.append({
                    "deck_id": deck.id,
                    "filename": deck.file_name,
                    "offering_extraction": f"Error: GPU processing failed - {gpu_result.get('error', 'Unknown error')}",
                    "visual_analysis_used": False
                })
        
        # Store experiment results
        experiment_data = {
            "experiment_name": request.experiment_name,
            "extraction_type": "company_offering",
            "text_model_used": request.text_model,
            "extraction_prompt": extraction_prompt,
            "results": extraction_results,
            "total_decks": len(extraction_results),
            "successful_extractions": len([r for r in extraction_results if not r["offering_extraction"].startswith("Error:")]),
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Save experiment to database and get the ID
        result = db.execute(text(
            "INSERT INTO extraction_experiments (experiment_name, pitch_deck_ids, extraction_type, text_model_used, extraction_prompt, results_json, created_at) VALUES (:name, :deck_ids, :type, :model, :prompt, :results, CURRENT_TIMESTAMP) RETURNING id"
        ), {
            "name": request.experiment_name,
            "deck_ids": request.deck_ids,
            "type": "company_offering", 
            "model": request.text_model,
            "prompt": extraction_prompt,
            "results": json.dumps(experiment_data)
        })
        experiment_id = result.fetchone()[0]
        db.commit()
        
        logger.info(f"Extraction test completed: {request.experiment_name} (ID: {experiment_id})")
        
        # Update progress tracker - step 3 completed successfully
        progress_tracker["step3"]["status"] = "completed"
        progress_tracker["step3"]["current_deck"] = "Offering extraction completed"
        progress_tracker["step3"]["progress"] = len(decks)
        
        # Add experiment_id to response
        response_data = experiment_data.copy()
        response_data["experiment_id"] = experiment_id
        return response_data
        
    except HTTPException:
        # Update progress tracker - step 3 error
        progress_tracker["step3"]["status"] = "error"
        progress_tracker["step3"]["current_deck"] = "GPU processing failed"
        progress_tracker["step3"]["progress"] = 0
        raise
    except Exception as e:
        logger.error(f"Error running extraction test: {e}")
        # Update progress tracker - step 3 error
        progress_tracker["step3"]["status"] = "error" 
        progress_tracker["step3"]["current_deck"] = "Processing error occurred"
        progress_tracker["step3"]["progress"] = 0
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
            "SELECT id, experiment_name, extraction_type, text_model_used, created_at, results_json, classification_enabled, classification_completed_at, company_name_completed_at, funding_amount_completed_at, deck_date_completed_at FROM extraction_experiments ORDER BY created_at DESC"
        )).fetchall()
        
        experiment_data = []
        for exp in experiments:
            results_data = json.loads(exp[5]) if exp[5] else {}
            
            # Calculate average response length from results
            average_response_length = 0
            if results_data.get("results"):
                successful_results = [
                    result for result in results_data["results"] 
                    if result.get("offering_extraction") and 
                    not result["offering_extraction"].startswith("Error:")
                ]
                if successful_results:
                    total_length = sum(len(result["offering_extraction"]) for result in successful_results)
                    average_response_length = round(total_length / len(successful_results))
            
            experiment_data.append({
                "id": exp[0],
                "experiment_name": exp[1],
                "extraction_type": exp[2], 
                "text_model_used": exp[3],
                "created_at": exp[4].isoformat() if exp[4] else None,
                "total_decks": results_data.get("total_decks", 0),
                "successful_extractions": results_data.get("successful_extractions", 0),
                "classification_enabled": bool(exp[6]) if exp[6] is not None else False,
                "classification_completed_at": exp[7].isoformat() if exp[7] else None,
                "company_name_completed_at": exp[8].isoformat() if exp[8] else None,
                "funding_amount_completed_at": exp[9].isoformat() if exp[9] else None,
                "deck_date_completed_at": exp[10].isoformat() if exp[10] else None,
                "average_response_length": average_response_length
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

@router.get("/extraction-test/experiments/{experiment_id}")
async def get_experiment_details(
    experiment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed results for a specific extraction experiment"""
    try:
        # Only GPs can view extraction experiment details
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can view extraction experiment details"
            )
        
        experiment = db.execute(text("""
            SELECT id, experiment_name, extraction_type, text_model_used, extraction_prompt, 
                   created_at, results_json, pitch_deck_ids, classification_enabled, 
                   classification_results_json, classification_completed_at, company_name_results_json, 
                   company_name_completed_at, funding_amount_results_json, funding_amount_completed_at,
                   deck_date_results_json, deck_date_completed_at
            FROM extraction_experiments 
            WHERE id = :exp_id
        """), {"exp_id": experiment_id}).fetchone()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail="Experiment not found"
            )
        
        # Parse results JSON
        results_data = json.loads(experiment[6]) if experiment[6] else {}
        
        # Get deck information for the experiment
        deck_ids_raw = experiment[7]  # pitch_deck_ids array from PostgreSQL
        # Parse PostgreSQL array format {65,68,61,58,51,71,60,50,62,64} to Python list
        if isinstance(deck_ids_raw, str) and deck_ids_raw.startswith('{') and deck_ids_raw.endswith('}'):
            deck_ids = [int(x.strip()) for x in deck_ids_raw[1:-1].split(',') if x.strip()]
        elif isinstance(deck_ids_raw, list):
            deck_ids = deck_ids_raw  # Already a list
        else:
            deck_ids = []
        decks = db.query(PitchDeck).filter(PitchDeck.id.in_(deck_ids)).all()
        deck_info = {}
        for deck in decks:
            # Extract page count from visual_analysis_cache
            page_count = None
            try:
                # Query visual_analysis_cache for this deck
                cache_result = db.execute(text("""
                    SELECT analysis_result_json 
                    FROM visual_analysis_cache 
                    WHERE pitch_deck_id = :deck_id
                    ORDER BY created_at DESC
                    LIMIT 1
                """), {"deck_id": deck.id}).fetchone()
                
                if cache_result and cache_result[0]:
                    analysis_data = json.loads(cache_result[0])
                    # Page count is the length of visual_analysis_results array
                    visual_results = analysis_data.get("visual_analysis_results", [])
                    if isinstance(visual_results, list):
                        page_count = len(visual_results)
            except Exception as e:
                logger.debug(f"Could not get page count for deck {deck.id}: {e}")
            
            deck_info[deck.id] = {
                "filename": deck.file_name, 
                "company_name": deck.ai_extracted_startup_name,
                "page_count": page_count
            }
        
        # Parse classification results if available
        classification_data = {}
        classification_results = []
        logger.info(f"Checking classification for experiment {experiment_id}: enabled={experiment[8]}, has_data={bool(experiment[9])}")
        if experiment[8] and experiment[9]:  # classification_enabled and classification_results_json
            try:
                # Parse classification results - it's stored as an array directly
                classification_results = json.loads(experiment[9])
                if not isinstance(classification_results, list):
                    classification_results = []
                logger.info(f"Parsed {len(classification_results)} classification results")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse classification results for experiment {experiment_id}: {e}")
        
        # Create a lookup for classification results by deck_id
        classification_lookup = {}
        for result in classification_results:
            deck_id = result.get("deck_id")
            classification = result.get("classification_result", {})
            if deck_id:
                classification_lookup[deck_id] = classification
        
        # Enhance results with deck information and classification data
        enhanced_results = []
        for result in results_data.get("results", []):
            deck_id = result.get("deck_id")
            enhanced_result = {
                **result,
                "deck_info": deck_info.get(deck_id, {"filename": f"deck_{deck_id}", "company_name": None})
            }
            
            # Add classification data if available
            if deck_id in classification_lookup:
                classification = classification_lookup[deck_id]
                enhanced_result.update({
                    "primary_sector": classification.get("primary_sector"),
                    "secondary_sector": classification.get("secondary_sector"),
                    "confidence_score": classification.get("confidence_score"),
                    "classification_reasoning": classification.get("reasoning"),
                    "subcategory": classification.get("subcategory"),
                    "keywords_matched": classification.get("keywords_matched"),
                    "recommended_template": classification.get("recommended_template"),
                    "classification_error": classification.get("error")
                })
            
            enhanced_results.append(enhanced_result)
        
        # Parse company name extraction results if available
        company_name_data = {}
        if experiment[11]:  # company_name_results_json
            try:
                company_name_data = json.loads(experiment[11])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse company name results for experiment {experiment_id}")

        # Parse funding amount extraction results if available
        funding_amount_data = {}
        if experiment[13]:  # funding_amount_results_json
            try:
                funding_amount_data = json.loads(experiment[13])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse funding amount results for experiment {experiment_id}")

        # Parse deck date extraction results if available
        deck_date_data = {}
        if experiment[15]:  # deck_date_results_json
            try:
                deck_date_data = json.loads(experiment[15])
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse deck date results for experiment {experiment_id}")

        experiment_details = {
            "id": experiment[0],
            "experiment_name": experiment[1],
            "extraction_type": experiment[2],
            "text_model_used": experiment[3],
            "extraction_prompt": experiment[4],
            "created_at": experiment[5].isoformat() if experiment[5] else None,
            "total_decks": results_data.get("total_decks", 0),
            "successful_extractions": results_data.get("successful_extractions", 0),
            "results": enhanced_results,
            "deck_ids": deck_ids,
            "classification_enabled": bool(experiment[8]),
            "classification_completed_at": experiment[10].isoformat() if experiment[10] else None,
            "classification_statistics": {},  # TODO: Calculate statistics if needed
            "classification_results_json": json.dumps(classification_lookup) if classification_lookup else None,
            "company_name_completed_at": experiment[12].isoformat() if experiment[12] else None,
            "company_name_statistics": company_name_data.get("statistics", {}) if company_name_data else {},
            "company_name_results": company_name_data.get("company_name_results", []) if company_name_data else [],
            "funding_amount_completed_at": experiment[14].isoformat() if experiment[14] else None,
            "funding_amount_statistics": funding_amount_data.get("statistics", {}) if funding_amount_data else {},
            "funding_amount_results": funding_amount_data.get("funding_amount_results", []) if funding_amount_data else [],
            "deck_date_completed_at": experiment[16].isoformat() if experiment[16] else None,
            "deck_date_statistics": deck_date_data.get("statistics", {}) if deck_date_data else {},
            "deck_date_results": deck_date_data.get("deck_date_results", []) if deck_date_data else []
        }
        
        return experiment_details
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting experiment details for {experiment_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get experiment details"
        )

@router.delete("/extraction-test/experiments")
async def delete_extraction_experiments(
    experiment_ids: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete multiple extraction experiments"""
    try:
        # Only GPs can delete extraction experiments
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can delete extraction experiments"
            )
        
        if not experiment_ids:
            raise HTTPException(
                status_code=400,
                detail="No experiment IDs provided"
            )
        
        # Delete experiments
        deleted_count = 0
        for experiment_id in experiment_ids:
            result = db.execute(text(
                "DELETE FROM extraction_experiments WHERE id = :experiment_id"
            ), {"experiment_id": experiment_id})
            
            if result.rowcount > 0:
                deleted_count += 1
        
        db.commit()
        
        logger.info(f"Deleted {deleted_count} extraction experiments by user {current_user.id}")
        
        return {
            "success": True,
            "deleted_count": deleted_count,
            "message": f"Successfully deleted {deleted_count} experiment(s)"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting extraction experiments: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to delete experiments"
        )

# ==================== CLASSIFICATION ENRICHMENT ====================

class ClassificationEnrichmentRequest(BaseModel):
    experiment_id: int
    classification_model: Optional[str] = None  # Optional: use default if not specified

@router.post("/extraction-test/run-classification")
async def enrich_experiment_with_classification(
    request: ClassificationEnrichmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enrich existing extraction experiment with startup classifications"""
    try:
        # Only GPs can run classification enrichment
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can run classification enrichment"
            )
        
        # Get the experiment
        experiment = db.execute(text("""
            SELECT id, experiment_name, extraction_type, text_model_used, 
                   extraction_prompt, created_at, results_json, pitch_deck_ids,
                   classification_enabled, classification_results_json,
                   classification_completed_at
            FROM extraction_experiments 
            WHERE id = :experiment_id
        """), {"experiment_id": request.experiment_id}).fetchone()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail="Experiment not found"
            )
        
        # Parse existing results
        results_data = json.loads(experiment[6]) if experiment[6] else {}
        results = results_data.get("results", [])
        
        if not results:
            raise HTTPException(
                status_code=400,
                detail="Experiment has no extraction results to classify"
            )
        
        # Check if classification already completed
        if experiment[8] and experiment[10]:  # classification_enabled and classification_completed_at
            logger.info(f"Experiment {request.experiment_id} already has classification results")
            existing_classification = json.loads(experiment[9]) if experiment[9] else {}
            return {
                "message": "Classification already completed",
                "experiment_id": request.experiment_id,
                "classification_results": existing_classification.get("classification_results", []),
                "completed_at": experiment[10].isoformat() if experiment[10] else None,
                "statistics": existing_classification.get("statistics", {})
            }
        
        # Update progress tracker - start classification
        progress_tracker["step3"]["status"] = "processing"
        progress_tracker["step3"]["current_deck"] = "Starting classification..."
        progress_tracker["step3"]["progress"] = 1
        progress_tracker["step3"]["total"] = 5
        
        # Initialize startup classifier
        from ..services.startup_classifier import StartupClassifier
        classifier = StartupClassifier(db)
        
        # Process each result for classification
        classification_results = []
        successful_classifications = 0
        
        for result in results:
            deck_id = result.get("deck_id")
            company_offering = result.get("offering_extraction", "")
            
            # Skip if extraction failed
            if not company_offering or company_offering.startswith("Error:") or company_offering.startswith("No visual analysis"):
                classification_results.append({
                    "deck_id": deck_id,
                    "filename": result.get("filename", f"deck_{deck_id}"),
                    "company_offering": company_offering,
                    "classification": None,
                    "confidence_score": 0.0,
                    "primary_sector": None,
                    "secondary_sector": None,
                    "error": "No valid company offering to classify"
                })
                continue
            
            try:
                # Run classification
                classification = await classifier.classify(company_offering)
                
                # Check if classification was successful (has primary_sector)
                if classification.get("primary_sector") and classification.get("primary_sector") != "unknown":
                    successful_classifications += 1
                    classification_results.append({
                        "deck_id": deck_id,
                        "filename": result.get("filename", f"deck_{deck_id}"),
                        "company_offering": company_offering,
                        "classification": classification,
                        "confidence_score": classification.get("confidence_score", 0.0),
                        "primary_sector": classification.get("primary_sector"),
                        "secondary_sector": classification.get("secondary_sector"),
                        "keywords_matched": classification.get("keywords_matched", []),
                        "reasoning": classification.get("reasoning", ""),
                        "error": None
                    })
                else:
                    classification_results.append({
                        "deck_id": deck_id,
                        "filename": result.get("filename", f"deck_{deck_id}"),
                        "company_offering": company_offering,
                        "classification": None,
                        "confidence_score": 0.0,
                        "primary_sector": None,
                        "secondary_sector": None,
                        "reasoning": classification.get("reasoning", "Classification failed"),
                        "error": classification.get("reasoning", "Classification failed")
                    })
                    
            except Exception as e:
                logger.error(f"Error classifying deck {deck_id}: {e}")
                classification_results.append({
                    "deck_id": deck_id,
                    "filename": result.get("filename", f"deck_{deck_id}"),
                    "company_offering": company_offering,
                    "classification": None,
                    "confidence_score": 0.0,
                    "primary_sector": None,
                    "secondary_sector": None,
                    "error": f"Classification error: {str(e)}"
                })
        
        # Calculate statistics
        sector_distribution = {}
        total_confidence = 0
        for result in classification_results:
            if result["primary_sector"]:
                sector = result["primary_sector"]
                sector_distribution[sector] = sector_distribution.get(sector, 0) + 1
                total_confidence += result["confidence_score"]
        
        avg_confidence = total_confidence / successful_classifications if successful_classifications > 0 else 0
        
        statistics = {
            "total_decks": len(classification_results),
            "successful_classifications": successful_classifications,
            "failed_classifications": len(classification_results) - successful_classifications,
            "success_rate": successful_classifications / len(classification_results) if classification_results else 0,
            "average_confidence": round(avg_confidence, 3),
            "sector_distribution": sector_distribution
        }
        
        # Format classification results for frontend (keyed by deck_id)
        classification_by_deck = {}
        for result in classification_results:
            deck_id = result["deck_id"]
            classification_by_deck[str(deck_id)] = {
                "primary_sector": result.get("primary_sector"),
                "secondary_sector": result.get("secondary_sector"),
                "confidence_score": result.get("confidence_score", 0.0),
                "reasoning": result.get("reasoning", ""),
                "keywords_matched": result.get("keywords_matched", []),
                "classification_error": result.get("error")
            }
        
        # Store classification results
        classification_data = {
            "classification_results": classification_results,
            "classification_by_deck": classification_by_deck,
            "statistics": statistics,
            "model_used": request.classification_model or classifier.classification_model,
            "classified_at": datetime.utcnow().isoformat()
        }
        
        # Update experiment with classification results
        db.execute(text("""
            UPDATE extraction_experiments 
            SET classification_enabled = TRUE,
                classification_results_json = :classification_results,
                classification_model_used = :model_used,
                classification_completed_at = CURRENT_TIMESTAMP
            WHERE id = :experiment_id
        """), {
            "experiment_id": request.experiment_id,
            "classification_results": json.dumps(classification_data),  # Store full data including statistics
            "model_used": request.classification_model or classifier.classification_model
        })
        
        db.commit()
        
        logger.info(f"Classification enrichment completed for experiment {request.experiment_id}: {successful_classifications}/{len(classification_results)} successful")
        
        # Update progress tracker - classification completed
        progress_tracker["step3"]["current_deck"] = "Classification completed"
        progress_tracker["step3"]["progress"] = 2
        
        return {
            "message": "Classification enrichment completed successfully",
            "experiment_id": request.experiment_id,
            "classification_results": classification_results,
            "statistics": statistics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running classification enrichment: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to run classification enrichment"
        )

class CompanyNameExtractionRequest(BaseModel):
    experiment_id: int

class FundingAmountExtractionRequest(BaseModel):
    experiment_id: int

class DeckDateExtractionRequest(BaseModel):
    experiment_id: int

class TemplateProcessingRequest(BaseModel):
    deck_ids: List[int]  # Direct deck IDs from current sample
    template_id: Optional[int] = None  # Optional: use default if not specified
    text_model: Optional[str] = None  # Text model to use for template processing
    generate_thumbnails: bool = True

@router.post("/extraction-test/run-company-name-extraction")
async def enrich_experiment_with_company_names(
    request: CompanyNameExtractionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enrich existing extraction experiment with company name extraction"""
    try:
        # Only GPs can run company name extraction
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can run company name extraction"
            )
        
        # Get the experiment
        experiment = db.execute(text("""
            SELECT id, experiment_name, extraction_type, text_model_used, 
                   extraction_prompt, created_at, results_json, pitch_deck_ids
            FROM extraction_experiments 
            WHERE id = :experiment_id
        """), {"experiment_id": request.experiment_id}).fetchone()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail="Experiment not found"
            )
        
        # Parse existing results
        results_data = json.loads(experiment[6]) if experiment[6] else {}
        results = results_data.get("results", [])
        
        if not results:
            raise HTTPException(
                status_code=400,
                detail="Experiment has no extraction results to extract company names from"
            )
        
        # Get the company name extraction prompt from pipeline_prompts
        prompt_result = db.execute(text(
            "SELECT prompt_text FROM pipeline_prompts WHERE stage_name = 'startup_name_extraction' LIMIT 1"
        )).fetchone()
        
        if not prompt_result:
            raise HTTPException(
                status_code=500,
                detail="startup_name_extraction prompt not found in pipeline_prompts table. Please add this prompt with stage_name='startup_name_extraction'."
            )
        
        startup_name_prompt = prompt_result[0]
        
        # Update progress tracker - start company name extraction
        progress_tracker["step3"]["status"] = "processing"
        progress_tracker["step3"]["current_deck"] = "Starting company name extraction..."
        progress_tracker["step3"]["progress"] = 2
        progress_tracker["step3"]["total"] = 5
        
        # Use GPU pipeline for company name extraction
        from ..services.gpu_http_client import gpu_http_client
        
        # Collect deck IDs for GPU processing
        deck_ids_raw = experiment[7]  # pitch_deck_ids array from PostgreSQL
        # Parse PostgreSQL array format {65,68,61,58,51,71,60,50,62,64} to Python list
        if isinstance(deck_ids_raw, str) and deck_ids_raw.startswith('{') and deck_ids_raw.endswith('}'):
            deck_ids = [int(x.strip()) for x in deck_ids_raw[1:-1].split(',') if x.strip()]
        elif isinstance(deck_ids_raw, list):
            deck_ids = deck_ids_raw  # Already a list
        else:
            deck_ids = []
        
        # Call GPU pipeline for company name extraction using the same visual analysis
        gpu_result = await gpu_http_client.run_offering_extraction(
            deck_ids=deck_ids,
            text_model=experiment[3],  # text_model_used
            extraction_prompt=startup_name_prompt,
            use_cached_visual=True
        )
        
        # Process GPU results
        company_name_results = []
        successful_extractions = 0
        
        if gpu_result.get("success"):
            logger.info("GPU company name extraction completed successfully")
            extraction_results = gpu_result.get("extraction_results", [])
            
            for result in extraction_results:
                deck_id = result.get("deck_id")
                company_name = result.get("offering_extraction", "")  # GPU returns this field
                
                # Skip if extraction failed
                if not company_name or company_name.startswith("Error:"):
                    company_name_results.append({
                        "deck_id": deck_id,
                        "filename": result.get("filename", f"deck_{deck_id}"),
                        "company_name": None,
                        "error": company_name or "Company name extraction failed"
                    })
                    continue
                
                successful_extractions += 1
                company_name_results.append({
                    "deck_id": deck_id,
                    "filename": result.get("filename", f"deck_{deck_id}"),
                    "company_name": company_name.strip(),
                    "error": None
                })
                
                # Update the PitchDeck record with extracted company name
                db.execute(text(
                    "UPDATE pitch_decks SET ai_extracted_startup_name = :company_name WHERE id = :deck_id"
                ), {
                    "company_name": company_name.strip(),
                    "deck_id": deck_id
                })
        else:
            logger.error(f"GPU company name extraction failed: {gpu_result.get('error', 'Unknown error')}")
            # Create error results for all decks
            for deck_id in deck_ids:
                company_name_results.append({
                    "deck_id": deck_id,
                    "filename": f"deck_{deck_id}",
                    "company_name": None,
                    "error": f"GPU processing failed: {gpu_result.get('error', 'Unknown error')}"
                })
        
        # Create statistics
        statistics = {
            "total_decks": len(company_name_results),
            "successful_extractions": successful_extractions,
            "failed_extractions": len(company_name_results) - successful_extractions,
            "success_rate": successful_extractions / len(company_name_results) if company_name_results else 0
        }
        
        # Store company name extraction results in the experiment
        company_name_data = {
            "company_name_results": company_name_results,
            "statistics": statistics,
            "model_used": experiment[3],  # text_model_used
            "prompt_used": startup_name_prompt,
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        # Update experiment with company name extraction results
        db.execute(text("""
            UPDATE extraction_experiments 
            SET company_name_results_json = :company_name_results,
                company_name_completed_at = CURRENT_TIMESTAMP
            WHERE id = :experiment_id
        """), {
            "experiment_id": request.experiment_id,
            "company_name_results": json.dumps(company_name_data)
        })
        
        db.commit()
        
        logger.info(f"Company name extraction completed for experiment {request.experiment_id}: {successful_extractions}/{len(company_name_results)} successful")
        
        # Update progress tracker - company name extraction completed
        progress_tracker["step3"]["current_deck"] = "Company name extraction completed"
        progress_tracker["step3"]["progress"] = 3
        
        return {
            "message": "Company name extraction completed successfully",
            "experiment_id": request.experiment_id,
            "company_name_results": company_name_results,
            "statistics": statistics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running company name extraction: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to run company name extraction"
        )

@router.post("/extraction-test/run-funding-amount-extraction")
async def enrich_experiment_with_funding_amounts(
    request: FundingAmountExtractionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enrich existing extraction experiment with funding amount extraction"""
    try:
        # Only GPs can run funding amount extraction
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can run funding amount extraction"
            )
        
        # Get the experiment
        experiment = db.execute(text("""
            SELECT id, experiment_name, extraction_type, text_model_used, 
                   extraction_prompt, created_at, results_json, pitch_deck_ids
            FROM extraction_experiments 
            WHERE id = :experiment_id
        """), {"experiment_id": request.experiment_id}).fetchone()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail="Experiment not found"
            )
        
        # Parse existing results
        results_data = json.loads(experiment[6]) if experiment[6] else {}
        results = results_data.get("results", [])
        
        if not results:
            raise HTTPException(
                status_code=400,
                detail="Experiment has no extraction results to extract funding amounts from"
            )
        
        # Get the funding amount extraction prompt from pipeline_prompts
        prompt_result = db.execute(text(
            "SELECT prompt_text FROM pipeline_prompts WHERE stage_name = 'funding_amount_extraction' LIMIT 1"
        )).fetchone()
        
        if not prompt_result:
            raise HTTPException(
                status_code=500,
                detail="funding_amount_extraction prompt not found in pipeline_prompts table. Please add this prompt with stage_name='funding_amount_extraction'."
            )
        
        funding_amount_prompt = prompt_result[0]
        
        # Update progress tracker - start funding amount extraction
        progress_tracker["step3"]["status"] = "processing"
        progress_tracker["step3"]["current_deck"] = "Starting funding amount extraction..."
        progress_tracker["step3"]["progress"] = 3
        progress_tracker["step3"]["total"] = 5
        
        # Use GPU pipeline for funding amount extraction
        from ..services.gpu_http_client import gpu_http_client
        
        # Collect deck IDs for GPU processing
        deck_ids_raw = experiment[7]  # pitch_deck_ids array from PostgreSQL
        # Parse PostgreSQL array format {65,68,61,58,51,71,60,50,62,64} to Python list
        if isinstance(deck_ids_raw, str) and deck_ids_raw.startswith('{') and deck_ids_raw.endswith('}'):
            deck_ids = [int(x.strip()) for x in deck_ids_raw[1:-1].split(',') if x.strip()]
        elif isinstance(deck_ids_raw, list):
            deck_ids = deck_ids_raw  # Already a list
        else:
            deck_ids = []
        
        # Call GPU pipeline for funding amount extraction using the same visual analysis
        gpu_result = await gpu_http_client.run_offering_extraction(
            deck_ids=deck_ids,
            text_model=experiment[3],  # text_model_used
            extraction_prompt=funding_amount_prompt,
            use_cached_visual=True
        )
        
        # Process GPU results
        funding_amount_results = []
        successful_extractions = 0
        
        if gpu_result.get("success"):
            logger.info("GPU funding amount extraction completed successfully")
            extraction_results = gpu_result.get("extraction_results", [])
            
            for result in extraction_results:
                deck_id = result.get("deck_id")
                funding_amount = result.get("offering_extraction", "")  # GPU returns this field
                
                # Skip if extraction failed
                if not funding_amount or funding_amount.startswith("Error:"):
                    funding_amount_results.append({
                        "deck_id": deck_id,
                        "filename": result.get("filename", f"deck_{deck_id}"),
                        "funding_amount": None,
                        "error": funding_amount or "Funding amount extraction failed"
                    })
                    continue
                
                successful_extractions += 1
                funding_amount_results.append({
                    "deck_id": deck_id,
                    "filename": result.get("filename", f"deck_{deck_id}"),
                    "funding_amount": funding_amount.strip(),
                    "error": None
                })
        else:
            logger.error(f"GPU funding amount extraction failed: {gpu_result.get('error', 'Unknown error')}")
            # Create error results for all decks
            for deck_id in deck_ids:
                funding_amount_results.append({
                    "deck_id": deck_id,
                    "filename": f"deck_{deck_id}",
                    "funding_amount": None,
                    "error": f"GPU processing failed: {gpu_result.get('error', 'Unknown error')}"
                })
        
        # Create statistics
        statistics = {
            "total_decks": len(funding_amount_results),
            "successful_extractions": successful_extractions,
            "failed_extractions": len(funding_amount_results) - successful_extractions,
            "success_rate": successful_extractions / len(funding_amount_results) if funding_amount_results else 0
        }
        
        # Store funding amount extraction results in the experiment
        funding_amount_data = {
            "funding_amount_results": funding_amount_results,
            "statistics": statistics,
            "model_used": experiment[3],  # text_model_used
            "prompt_used": funding_amount_prompt,
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        # Update experiment with funding amount extraction results
        db.execute(text("""
            UPDATE extraction_experiments 
            SET funding_amount_results_json = :funding_amount_results,
                funding_amount_completed_at = CURRENT_TIMESTAMP
            WHERE id = :experiment_id
        """), {
            "experiment_id": request.experiment_id,
            "funding_amount_results": json.dumps(funding_amount_data)
        })
        
        db.commit()
        
        logger.info(f"Funding amount extraction completed for experiment {request.experiment_id}: {successful_extractions}/{len(funding_amount_results)} successful")
        
        # Update progress tracker - funding amount extraction completed
        progress_tracker["step3"]["current_deck"] = "Funding amount extraction completed"
        progress_tracker["step3"]["progress"] = 4
        
        return {
            "message": "Funding amount extraction completed successfully",
            "experiment_id": request.experiment_id,
            "funding_amount_results": funding_amount_results,
            "statistics": statistics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running funding amount extraction: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to run funding amount extraction"
        )

@router.post("/extraction-test/run-deck-date-extraction")
async def enrich_experiment_with_deck_dates(
    request: DeckDateExtractionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Enrich existing extraction experiment with deck date extraction"""
    try:
        # Only GPs can run deck date extraction
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can run deck date extraction"
            )
        
        # Get the experiment
        experiment = db.execute(text("""
            SELECT id, experiment_name, extraction_type, text_model_used, 
                   extraction_prompt, created_at, results_json, pitch_deck_ids
            FROM extraction_experiments 
            WHERE id = :experiment_id
        """), {"experiment_id": request.experiment_id}).fetchone()
        
        if not experiment:
            raise HTTPException(
                status_code=404,
                detail="Experiment not found"
            )
        
        # Parse existing results
        results_data = json.loads(experiment[6]) if experiment[6] else {}
        results = results_data.get("results", [])
        
        if not results:
            raise HTTPException(
                status_code=400,
                detail="Experiment has no extraction results to extract deck dates from"
            )
        
        # Get the deck date extraction prompt from pipeline_prompts
        prompt_result = db.execute(text(
            "SELECT prompt_text FROM pipeline_prompts WHERE stage_name = 'deck_date_extraction' LIMIT 1"
        )).fetchone()
        
        if not prompt_result:
            raise HTTPException(
                status_code=500,
                detail="deck_date_extraction prompt not found in pipeline_prompts table. Please add this prompt with stage_name='deck_date_extraction'."
            )
        
        deck_date_prompt = prompt_result[0]
        
        # Update progress tracker - start deck date extraction
        progress_tracker["step3"]["status"] = "processing"
        progress_tracker["step3"]["current_deck"] = "Starting deck date extraction..."
        progress_tracker["step3"]["progress"] = 4
        progress_tracker["step3"]["total"] = 5
        
        # Use GPU pipeline for deck date extraction
        from ..services.gpu_http_client import gpu_http_client
        
        # Collect deck IDs for GPU processing
        deck_ids_raw = experiment[7]  # pitch_deck_ids array from PostgreSQL
        # Parse PostgreSQL array format {65,68,61,58,51,71,60,50,62,64} to Python list
        if isinstance(deck_ids_raw, str) and deck_ids_raw.startswith('{') and deck_ids_raw.endswith('}'):
            deck_ids = [int(x.strip()) for x in deck_ids_raw[1:-1].split(',') if x.strip()]
        elif isinstance(deck_ids_raw, list):
            deck_ids = deck_ids_raw  # Already a list
        else:
            deck_ids = []
        
        # Call GPU pipeline for deck date extraction using the same visual analysis
        gpu_result = await gpu_http_client.run_offering_extraction(
            deck_ids=deck_ids,
            text_model=experiment[3],  # text_model_used
            extraction_prompt=deck_date_prompt,
            use_cached_visual=True
        )
        
        # Process GPU results
        deck_date_results = []
        successful_extractions = 0
        
        if gpu_result.get("success"):
            logger.info("GPU deck date extraction completed successfully")
            extraction_results = gpu_result.get("extraction_results", [])
            
            for result in extraction_results:
                deck_id = result.get("deck_id")
                deck_date = result.get("offering_extraction", "")  # GPU returns this field
                
                # Skip if extraction failed
                if not deck_date or deck_date.startswith("Error:"):
                    deck_date_results.append({
                        "deck_id": deck_id,
                        "filename": result.get("filename", f"deck_{deck_id}"),
                        "deck_date": None,
                        "error": deck_date or "Deck date extraction failed"
                    })
                    continue
                
                successful_extractions += 1
                deck_date_results.append({
                    "deck_id": deck_id,
                    "filename": result.get("filename", f"deck_{deck_id}"),
                    "deck_date": deck_date.strip(),
                    "error": None
                })
        else:
            logger.error(f"GPU deck date extraction failed: {gpu_result.get('error', 'Unknown error')}")
            # Create error results for all decks
            for deck_id in deck_ids:
                deck_date_results.append({
                    "deck_id": deck_id,
                    "filename": f"deck_{deck_id}",
                    "deck_date": None,
                    "error": f"GPU processing failed: {gpu_result.get('error', 'Unknown error')}"
                })
        
        # Create statistics
        statistics = {
            "total_decks": len(deck_date_results),
            "successful_extractions": successful_extractions,
            "failed_extractions": len(deck_date_results) - successful_extractions,
            "success_rate": successful_extractions / len(deck_date_results) if deck_date_results else 0
        }
        
        # Store deck date extraction results in the experiment
        deck_date_data = {
            "deck_date_results": deck_date_results,
            "statistics": statistics,
            "model_used": experiment[3],  # text_model_used
            "prompt_used": deck_date_prompt,
            "extracted_at": datetime.utcnow().isoformat()
        }
        
        # Update experiment with deck date extraction results
        db.execute(text("""
            UPDATE extraction_experiments 
            SET deck_date_results_json = :deck_date_results,
                deck_date_completed_at = CURRENT_TIMESTAMP
            WHERE id = :experiment_id
        """), {
            "experiment_id": request.experiment_id,
            "deck_date_results": json.dumps(deck_date_data)
        })
        
        db.commit()
        
        logger.info(f"Deck date extraction completed for experiment {request.experiment_id}: {successful_extractions}/{len(deck_date_results)} successful")
        
        # Update progress tracker - all extractions completed
        import time
        completion_time = time.time()
        progress_tracker["step3"]["status"] = "completed"
        progress_tracker["step3"]["current_deck"] = "All obligatory extractions completed"
        progress_tracker["step3"]["progress"] = 5
        progress_tracker["step3"]["completion_time"] = completion_time
        
        return {
            "message": "Deck date extraction completed successfully",
            "experiment_id": request.experiment_id,
            "deck_date_results": deck_date_results,
            "statistics": statistics
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running deck date extraction: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to run deck date extraction"
        )

@router.post("/extraction-test/run-template-processing")
async def run_template_processing_batch(
    request: TemplateProcessingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Process decks from current sample through template analysis pipeline with thumbnail generation"""
    try:
        # Only GPs can run template processing
        if current_user.role != "gp":
            raise HTTPException(
                status_code=403,
                detail="Only GPs can run template processing"
            )
        
        # Use deck IDs directly from the request (current sample)
        deck_ids = request.deck_ids
        
        if not deck_ids:
            raise HTTPException(
                status_code=400,
                detail="No deck IDs provided"
            )
        
        # Validate deck IDs exist and are dojo files
        decks = db.query(PitchDeck).filter(
            PitchDeck.id.in_(deck_ids),
            PitchDeck.data_source == "dojo"
        ).all()
        
        if len(decks) != len(deck_ids):
            raise HTTPException(
                status_code=400,
                detail="Some deck IDs not found or not dojo files"
            )
        
        # Check if companies have been added to the database
        # Template processing results won't show in gallery without proper company entries
        decks_without_companies = [deck.id for deck in decks if not deck.company_id]
        
        if decks_without_companies:
            raise HTTPException(
                status_code=400,
                detail=f"Template processing requires companies to be added first. "
                       f"Please use 'Add Dojo Companies' to add these decks to the database before running template processing. "
                       f"Decks without companies: {decks_without_companies}"
            )
        
        # Get template information if specified
        template_info = None
        if request.template_id:
            template_result = db.execute(text("""
                SELECT id, name, description FROM analysis_templates 
                WHERE id = :template_id AND is_active = true
            """), {"template_id": request.template_id}).fetchone()
            
            if not template_result:
                raise HTTPException(
                    status_code=404,
                    detail="Template not found"
                )
            
            template_info = {
                "id": template_result[0],
                "name": template_result[1],
                "prompt": template_result[2]  # Using description as prompt for now
            }
        else:
            # Use default template if none specified
            default_template = db.execute(text("""
                SELECT id, name, description FROM analysis_templates 
                WHERE is_default = true AND is_active = true
                LIMIT 1
            """)).fetchone()
            
            if default_template:
                template_info = {
                    "id": default_template[0],
                    "name": default_template[1],
                    "prompt": default_template[2]  # Using description as prompt for now
                }
        
        # Calculate total progress steps (decks × chapters)
        # Get template info to determine number of chapters
        total_chapters = 7  # Default assumption for standard template
        if template_info and template_info.get("id"):
            try:
                chapter_count_query = text("""
                    SELECT COUNT(*) FROM template_chapters 
                    WHERE template_id = :template_id
                """)
                chapter_result = db.execute(chapter_count_query, {"template_id": template_info["id"]}).fetchone()
                if chapter_result:
                    total_chapters = chapter_result[0]
                    logger.info(f"Template {template_info['id']} has {total_chapters} chapters")
            except Exception as e:
                logger.warning(f"Could not get chapter count, using default: {e}")
        
        # Update progress tracker - start step 4 processing
        progress_tracker["step4"]["status"] = "processing"
        progress_tracker["step4"]["current_deck"] = decks[0].file_name if decks else ""
        progress_tracker["step4"]["progress"] = 0
        progress_tracker["step4"]["total"] = len(decks) * total_chapters
        
        # Use GPU pipeline for template processing
        from ..services.gpu_http_client import gpu_http_client
        
        # Call NEW template-only GPU endpoint (no re-analysis, uses cached data)
        gpu_result = await gpu_http_client.run_template_processing_only(
            deck_ids=deck_ids,
            template_id=request.template_id if request.template_id else (template_info["id"] if template_info else None),
            text_model=request.text_model,
            generate_thumbnails=request.generate_thumbnails
        )
        
        # Process GPU results
        template_processing_results = []
        successful_processing = 0
        thumbnail_generation_success = 0
        
        if gpu_result.get("success"):
            logger.info("GPU template processing completed successfully")
            # New endpoint returns results differently
            processing_results = gpu_result.get("results", [])
            
            for result in processing_results:
                deck_id = result.get("deck_id")
                template_analysis = result.get("template_analysis", "")
                thumbnail_info = result.get("thumbnail_info", {})
                
                # Check if processing succeeded
                processing_success = not (template_analysis.startswith("Error:") if template_analysis else True)
                thumbnail_success = thumbnail_info.get("success", False) if request.generate_thumbnails else True
                
                if processing_success:
                    successful_processing += 1
                
                if thumbnail_success:
                    thumbnail_generation_success += 1
                
                # Find corresponding deck info
                deck = next((d for d in decks if d.id == deck_id), None)
                filename = deck.file_name if deck else f"deck_{deck_id}"
                
                template_processing_results.append({
                    "deck_id": deck_id,
                    "filename": filename,
                    "template_analysis": template_analysis,
                    "template_used": template_info["name"] if template_info else "Default",
                    "thumbnail_info": thumbnail_info,
                    "processing_success": processing_success,
                    "thumbnail_success": thumbnail_success,
                    "error": result.get("error")
                })
        else:
            logger.error(f"GPU template processing failed: {gpu_result.get('error', 'Unknown error')}")
            # Create error results for all decks
            for deck_id in deck_ids:
                deck = next((d for d in decks if d.id == deck_id), None)
                filename = deck.file_name if deck else f"deck_{deck_id}"
                
                template_processing_results.append({
                    "deck_id": deck_id,
                    "filename": filename,
                    "template_analysis": None,
                    "template_used": template_info["name"] if template_info else "Default",
                    "thumbnail_info": {"success": False, "error": "GPU processing failed"},
                    "processing_success": False,
                    "thumbnail_success": False,
                    "error": f"GPU processing failed: {gpu_result.get('error', 'Unknown error')}"
                })
        
        # Create statistics
        statistics = {
            "total_decks": len(template_processing_results),
            "successful_template_processing": successful_processing,
            "failed_template_processing": len(template_processing_results) - successful_processing,
            "template_processing_success_rate": successful_processing / len(template_processing_results) if template_processing_results else 0,
            "successful_thumbnail_generation": thumbnail_generation_success,
            "failed_thumbnail_generation": len(template_processing_results) - thumbnail_generation_success,
            "thumbnail_generation_success_rate": thumbnail_generation_success / len(template_processing_results) if template_processing_results else 0,
            "template_used": template_info["name"] if template_info else "Default",
            "thumbnails_requested": request.generate_thumbnails
        }
        
        # Store template processing results in the experiment
        template_processing_data = {
            "template_processing_results": template_processing_results,
            "statistics": statistics,
            "template_used": template_info,
            "thumbnails_generated": request.generate_thumbnails,
            "processed_at": datetime.utcnow().isoformat()
        }
        
        logger.info(f"Template processing completed for current sample: {successful_processing}/{len(template_processing_results)} successful template analyses, {thumbnail_generation_success}/{len(template_processing_results)} successful thumbnail generations")
        
        # Store template processing results in the database for each deck
        for result in template_processing_results:
            deck_id = result["deck_id"]
            
            # Store the template analysis result in the database
            if result.get("template_analysis") and result.get("processing_success"):
                try:
                    # Store the full template analysis in the template_processing_results_json column
                    # Also set results_file_path to indicate results are available
                    db.execute(text("""
                        UPDATE pitch_decks 
                        SET template_processing_results_json = :results_json,
                            results_file_path = :results_marker
                        WHERE id = :deck_id
                    """), {
                        "deck_id": deck_id,
                        "results_json": json.dumps({
                            "template_analysis": result["template_analysis"],
                            "template_used": result["template_used"],
                            "processed_at": datetime.utcnow().isoformat(),
                            "thumbnails": result.get("thumbnail_info", {}).get("thumbnails", [])
                        }),
                        "results_marker": f"template_processed_{deck_id}"
                    })
                    logger.info(f"Stored template processing results for deck {deck_id}")
                except Exception as e:
                    logger.error(f"Failed to store template results for deck {deck_id}: {e}")
            
            # Update the pitch_deck to indicate it has template processing results
            # Use a special marker in results_file_path to indicate template-processed results
            template_results_marker = f"template_processed"
            
            try:
                # First check if this is a project_document or pitch_deck
                project_doc_result = db.execute(text("""
                    SELECT pd.id FROM project_documents pd
                    WHERE pd.id = :deck_id AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
                """), {"deck_id": deck_id}).fetchone()
                
                if project_doc_result:
                    # This is a project_document - find the corresponding pitch_deck by filename
                    pitch_deck_result = db.execute(text("""
                        SELECT pd.id FROM pitch_decks pd
                        WHERE pd.file_name = :filename AND pd.data_source = 'dojo'
                        ORDER BY pd.created_at DESC LIMIT 1
                    """), {"filename": result["filename"]}).fetchone()
                    
                    if pitch_deck_result:
                        pitch_deck_id = pitch_deck_result[0]
                        # Update pitch_deck to indicate dojo experiment results available
                        db.execute(text("""
                            UPDATE pitch_decks 
                            SET results_file_path = :results_marker, processing_status = 'completed'
                            WHERE id = :pitch_deck_id
                        """), {
                            "results_marker": template_results_marker,
                            "pitch_deck_id": pitch_deck_id
                        })
                        logger.info(f"Marked pitch_deck {pitch_deck_id} as having dojo experiment results")
                else:
                    # This is already a pitch_deck ID, update directly
                    db.execute(text("""
                        UPDATE pitch_decks 
                        SET results_file_path = :results_marker, processing_status = 'completed'
                        WHERE id = :deck_id
                    """), {
                        "results_marker": template_results_marker,
                        "deck_id": deck_id
                    })
                    logger.info(f"Marked pitch_deck {deck_id} as having dojo experiment results")
                
            except Exception as e:
                logger.error(f"Failed to mark deck {deck_id} as having results: {e}")
                continue
        
        # Commit the results markers
        db.commit()
        logger.info(f"Marked {len(template_processing_results)} decks as having dojo experiment results")
        
        # Update progress tracker - step 4 completed successfully
        progress_tracker["step4"]["status"] = "completed"
        progress_tracker["step4"]["current_deck"] = "Template processing completed"
        progress_tracker["step4"]["progress"] = len(decks)
        
        return {
            "message": "Template processing completed successfully",
            "template_processing_results": template_processing_results,
            "statistics": statistics,
            "processed_decks": len(deck_ids)
        }
        
    except HTTPException:
        # Update progress tracker - step 4 error
        progress_tracker["step4"]["status"] = "error"
        progress_tracker["step4"]["current_deck"] = "GPU processing failed"
        progress_tracker["step4"]["progress"] = 0
        raise
    except Exception as e:
        logger.error(f"Error running template processing: {e}")
        # Update progress tracker - step 4 error
        progress_tracker["step4"]["status"] = "error"
        progress_tracker["step4"]["current_deck"] = "Processing error occurred"
        progress_tracker["step4"]["progress"] = 0
        raise HTTPException(
            status_code=500,
            detail="Failed to run template processing"
        )

# ==================== INTERNAL API FOR GPU COMMUNICATION ====================

@router.post("/internal/cache-visual-analysis")
async def cache_visual_analysis_from_gpu(
    request: dict,
    db: Session = Depends(get_db)
):
    """Internal endpoint for GPU to cache visual analysis results immediately"""
    try:
        pitch_deck_id = request.get("pitch_deck_id")
        analysis_result_json = request.get("analysis_result_json")
        vision_model_used = request.get("vision_model_used")
        prompt_used = request.get("prompt_used")
        
        if not pitch_deck_id:
            return {
                "success": False,
                "error": "pitch_deck_id is required"
            }
        
        if not analysis_result_json:
            return {
                "success": False,
                "error": "analysis_result_json is required"
            }
        
        logger.info(f"GPU caching visual analysis for deck {pitch_deck_id}")
        
        # Cache the visual analysis result
        db.execute(text(
            "INSERT INTO visual_analysis_cache (pitch_deck_id, analysis_result_json, vision_model_used, prompt_used) VALUES (:deck_id, :result, :model, :prompt) ON CONFLICT (pitch_deck_id, vision_model_used, prompt_used) DO UPDATE SET analysis_result_json = :result, created_at = CURRENT_TIMESTAMP"
        ), {
            "deck_id": pitch_deck_id,
            "result": analysis_result_json,
            "model": vision_model_used,
            "prompt": prompt_used
        })
        
        db.commit()
        
        logger.info(f"Successfully cached visual analysis for deck {pitch_deck_id}")
        
        return {
            "success": True,
            "message": f"Cached visual analysis for deck {pitch_deck_id}"
        }
        
    except Exception as e:
        logger.error(f"Error caching visual analysis from GPU: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/internal/get-cached-visual-analysis")
async def get_cached_visual_analysis_for_gpu(
    request: dict,
    db: Session = Depends(get_db)
):
    """Internal endpoint for GPU to retrieve cached visual analysis"""
    try:
        deck_ids = request.get("deck_ids", [])
        if not deck_ids:
            return {
                "success": False,
                "error": "deck_ids is required"
            }
        
        logger.info(f"GPU requesting cached visual analysis for {len(deck_ids)} decks: {deck_ids}")
        
        cached_analysis = {}
        for deck_id in deck_ids:
            try:
                cache_result = db.execute(text(
                    "SELECT analysis_result_json FROM visual_analysis_cache WHERE pitch_deck_id = :deck_id ORDER BY created_at DESC LIMIT 1"
                ), {"deck_id": deck_id}).fetchone()
                
                if cache_result:
                    cached_analysis[deck_id] = json.loads(cache_result[0])
                    logger.info(f"DEBUG: Found cached visual analysis for deck {deck_id}, keys: {list(cached_analysis[deck_id].keys())}")
                else:
                    logger.warning(f"DEBUG: No cached visual analysis found for deck {deck_id}")
                    
            except Exception as e:
                logger.error(f"Error retrieving cached visual analysis for deck {deck_id}: {e}")
                continue
        
        logger.info(f"Retrieved cached visual analysis for {len(cached_analysis)}/{len(deck_ids)} decks")
        
        return {
            "success": True,
            "cached_analysis": cached_analysis,
            "total_requested": len(deck_ids),
            "total_found": len(cached_analysis)
        }
        
    except Exception as e:
        logger.error(f"Error in get_cached_visual_analysis_for_gpu: {e}")
        return {
            "success": False,
            "error": str(e)
        }

async def process_visual_analysis_batch(deck_ids: List[int], vision_model: str):
    """Background task to process visual analysis for multiple decks individually with real-time progress"""
    import time
    try:
        logger.info(f"Starting individual visual analysis for {len(deck_ids)} decks using GPU pipeline")
        
        # Get fresh database connection for background task
        from ..db.database import get_db
        db = next(get_db())
        
        try:
            # Get analysis prompt from database 
            prompt_result = db.execute(text(
                "SELECT prompt_text FROM pipeline_prompts WHERE stage_name = 'image_analysis' AND is_active = TRUE LIMIT 1"
            )).fetchone()
            
            if prompt_result:
                analysis_prompt = prompt_result[0]
            else:
                # No fallback - fail explicitly
                raise HTTPException(
                    status_code=500,
                    detail="image_analysis prompt not found in pipeline_prompts table. Please add this prompt with stage_name='image_analysis'."
                )
            
            # Initialize progress tracker with timing
            start_time = time.time()
            progress_tracker["step2"]["status"] = "processing"
            progress_tracker["step2"]["current_deck"] = "Starting visual analysis..."
            progress_tracker["step2"]["progress"] = 0
            progress_tracker["step2"]["total"] = len(deck_ids)
            progress_tracker["step2"]["start_time"] = start_time
            progress_tracker["step2"]["completion_time"] = None
            progress_tracker["step2"]["processing_times"] = []
            progress_tracker["step2"]["current_deck_start_time"] = None
            
            # Get deck information and file paths
            decks = db.query(PitchDeck).filter(PitchDeck.id.in_(deck_ids)).all()
            if not decks:
                logger.error("No decks found for visual analysis batch")
                progress_tracker["step2"]["status"] = "error"
                return
            
            # Create deck mapping
            deck_id_to_deck = {deck.id: deck for deck in decks}
            
            # Import GPU HTTP client
            from ..services.gpu_http_client import gpu_http_client
            
            # Process each deck individually with real-time progress updates
            successful_count = 0
            for i, deck_id in enumerate(deck_ids):
                deck = deck_id_to_deck.get(deck_id)
                if not deck:
                    logger.warning(f"Deck {deck_id} not found in database")
                    continue
                
                deck_name = deck.file_name or f"deck_{deck.id}.pdf"
                deck_start_time = time.time()
                
                # Update progress tracker - currently processing this deck
                progress_tracker["step2"]["current_deck"] = deck_name
                progress_tracker["step2"]["progress"] = i
                progress_tracker["step2"]["current_deck_start_time"] = deck_start_time
                
                logger.info(f"Processing deck {i+1}/{len(deck_ids)}: {deck_name}")
                
                try:
                    # Process single deck
                    result = await gpu_http_client.run_visual_analysis_single_deck(
                        deck_id=deck_id,
                        vision_model=vision_model,
                        analysis_prompt=analysis_prompt,
                        file_path=deck.file_path
                    )
                    
                    deck_end_time = time.time()
                    deck_processing_time = deck_end_time - deck_start_time
                    progress_tracker["step2"]["processing_times"].append(deck_processing_time)
                    
                    if result.get("success"):
                        # Cache the result
                        deck_result = result.get("result", {})
                        if deck_result:
                            db.execute(text(
                                "INSERT INTO visual_analysis_cache (pitch_deck_id, analysis_result_json, vision_model_used, prompt_used) VALUES (:deck_id, :result, :model, :prompt) ON CONFLICT (pitch_deck_id, vision_model_used, prompt_used) DO UPDATE SET analysis_result_json = :result, created_at = CURRENT_TIMESTAMP"
                            ), {
                                "deck_id": deck_id,
                                "result": json.dumps(deck_result),
                                "model": vision_model,
                                "prompt": analysis_prompt
                            })
                            db.commit()
                            successful_count += 1
                            logger.info(f"Successfully processed and cached deck {deck_name} in {deck_processing_time:.1f}s")
                        else:
                            logger.warning(f"No result returned for deck {deck_name}")
                    else:
                        logger.error(f"GPU processing failed for deck {deck_name}: {result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Error processing deck {deck_name}: {e}")
                    deck_end_time = time.time()
                    deck_processing_time = deck_end_time - deck_start_time
                    progress_tracker["step2"]["processing_times"].append(deck_processing_time)
                
                # Update progress after each deck
                progress_tracker["step2"]["progress"] = i + 1
            
            # Complete processing
            completion_time = time.time()
            total_time = completion_time - start_time
            progress_tracker["step2"]["completion_time"] = completion_time
            progress_tracker["step2"]["status"] = "completed"
            progress_tracker["step2"]["current_deck"] = f"Completed: {successful_count}/{len(deck_ids)} decks processed"
            
            logger.info(f"Visual analysis completed: {successful_count}/{len(deck_ids)} decks processed in {total_time:.1f}s")
        
        finally:
            # Close the database connection
            db.close()
        
    except Exception as e:
        logger.error(f"Error in visual analysis processing: {e}")
        # Update progress tracker - error
        progress_tracker["step2"]["status"] = "error"
        progress_tracker["step2"]["current_deck"] = "Processing error occurred"
        if progress_tracker["step2"]["start_time"]:
            progress_tracker["step2"]["completion_time"] = time.time()
@router.post("/template-progress-callback")
async def template_progress_callback(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Receive progress updates from GPU for template processing"""
    try:
        deck_id = request.get("deck_id")
        chapter_name = request.get("chapter_name")
        status = request.get("status", "processing")
        chapter_results = request.get("chapter_results")
        
        if deck_id and chapter_name:
            # Get deck filename for display
            try:
                deck_info = db.execute(text(
                    "SELECT file_name FROM pitch_decks WHERE id = :deck_id"
                ), {"deck_id": deck_id}).fetchone()
                
                deck_filename = deck_info[0] if deck_info else f"Deck {deck_id}"
                
                # Update progress tracker with current deck and chapter
                progress_tracker["step4"]["current_deck"] = deck_filename
                progress_tracker["step4"]["current_chapter"] = chapter_name
                
                # Increment progress on chapter completion
                if status == "completed":
                    progress_tracker["step4"]["progress"] += 1
                    logger.info(f"Template progress update - Deck {deck_filename}: Completed chapter '{chapter_name}' ({progress_tracker['step4']['progress']}/{progress_tracker['step4']['total']})")
                    
                    # Progressive delivery: Store chapter results if provided
                    if chapter_results:
                        try:
                            # Store chapter results in extraction_experiments table
                            from ..services.gpu_http_client import gpu_http_client
                            
                            # Get the current active experiment
                            latest_experiment = db.execute(text(
                                "SELECT id, template_processing_results_json FROM extraction_experiments ORDER BY created_at DESC LIMIT 1"
                            )).fetchone()
                            
                            if latest_experiment:
                                experiment_id = latest_experiment[0]
                                existing_results = json.loads(latest_experiment[1]) if latest_experiment[1] else {}
                                
                                # Add chapter results to deck
                                if "results" not in existing_results:
                                    existing_results["results"] = []
                                
                                # Find or create deck entry
                                deck_entry = None
                                for result in existing_results["results"]:
                                    if result.get("deck_id") == deck_id:
                                        deck_entry = result
                                        break
                                
                                if not deck_entry:
                                    deck_entry = {"deck_id": deck_id, "chapters": {}}
                                    existing_results["results"].append(deck_entry)
                                
                                if "chapters" not in deck_entry:
                                    deck_entry["chapters"] = {}
                                
                                # Store chapter results
                                deck_entry["chapters"][chapter_name] = chapter_results
                                
                                # Update database
                                db.execute(text(
                                    "UPDATE extraction_experiments SET template_processing_results_json = :results WHERE id = :experiment_id"
                                ), {"results": json.dumps(existing_results), "experiment_id": experiment_id})
                                db.commit()
                                
                                logger.info(f"Progressive storage - Deck {deck_id}: Stored chapter '{chapter_name}' results")
                            else:
                                logger.warning("No active experiment found for progressive delivery")
                                
                        except Exception as e:
                            logger.warning(f"Failed to store progressive chapter results: {e}")
                else:
                    logger.info(f"Template progress update - Deck {deck_filename}: Processing chapter '{chapter_name}'")
                
            except Exception as e:
                logger.warning(f"Could not get deck filename for {deck_id}: {e}")
                progress_tracker["step4"]["current_deck"] = f"Processing deck {deck_id}"
                progress_tracker["step4"]["current_chapter"] = chapter_name
                
                # Increment progress on chapter completion (fallback path)
                if status == "completed":
                    progress_tracker["step4"]["progress"] += 1
        
        return {"success": True}
    except Exception as e:
        logger.error(f"Error in template progress callback: {e}")
        return {"success": False, "error": str(e)}

@router.post("/save-extraction-experiment")
async def save_extraction_experiment(
    request: SaveExtractionExperimentRequest,
    db: Session = Depends(get_db)
):
    """Save extraction experiment results to database"""
    try:
        logger.info(f"Saving extraction experiment: {request.experiment_name}")
        
        # Convert deck_ids list to PostgreSQL array format
        deck_ids_str = "{" + ",".join(map(str, request.deck_ids)) + "}"
        
        # The GPU sends results in this format:
        # {
        #   "offering_extraction": [...],
        #   "company_names": [...],
        #   "funding_amounts": [...],
        #   "deck_dates": [...],
        #   "classification": [...]
        # }
        
        # Extract specific result types from the results
        offering_results_json = None
        company_name_results_json = None
        funding_amount_results_json = None 
        deck_date_results_json = None
        classification_results_json = None
        
        # Process the results if they exist
        if isinstance(request.results, list) and len(request.results) > 0:
            # Handle array format from GPU
            results_json = json.dumps(request.results)
        elif isinstance(request.results, dict):
            # Handle dict format with separate categories
            results_dict = request.results
            
            if "offering_extraction" in results_dict:
                offering_results_json = json.dumps(results_dict["offering_extraction"])
            if "company_names" in results_dict:
                company_name_results_json = json.dumps(results_dict["company_names"])
            if "funding_amounts" in results_dict:
                funding_amount_results_json = json.dumps(results_dict["funding_amounts"])
            if "deck_dates" in results_dict:
                deck_date_results_json = json.dumps(results_dict["deck_dates"])
            if "classification" in results_dict:
                classification_results_json = json.dumps(results_dict["classification"])
                
            results_json = json.dumps(request.results)
        else:
            results_json = json.dumps(request.results)
        
        # Insert into extraction_experiments table with all columns
        query = text("""
            INSERT INTO extraction_experiments (
                experiment_name, 
                pitch_deck_ids, 
                extraction_type, 
                text_model_used,
                extraction_prompt,
                results_json,
                company_name_results_json,
                classification_results_json,
                funding_amount_results_json,
                deck_date_results_json,
                created_at
            ) VALUES (
                :experiment_name,
                :deck_ids,
                :experiment_type,
                :text_model,
                :extraction_prompt,
                :results_json,
                :company_name_results_json,
                :classification_results_json,
                :funding_amount_results_json,
                :deck_date_results_json,
                :created_at
            ) RETURNING id
        """)
        
        result = db.execute(query, {
            "experiment_name": request.experiment_name,
            "deck_ids": deck_ids_str,
            "experiment_type": request.experiment_type,
            "text_model": "gemma3:12b",  # Default from GPU request
            "extraction_prompt": f"Extraction for {request.experiment_type}",
            "results_json": results_json,
            "company_name_results_json": company_name_results_json,
            "classification_results_json": classification_results_json,
            "funding_amount_results_json": funding_amount_results_json,
            "deck_date_results_json": deck_date_results_json,
            "created_at": datetime.utcnow()
        })
        
        experiment_id = result.fetchone()[0]
        db.commit()
        
        logger.info(f"Successfully saved extraction experiment {experiment_id}")
        
        return {
            "success": True,
            "experiment_id": experiment_id,
            "message": f"Saved extraction experiment for {len(request.deck_ids)} decks"
        }
        
    except Exception as e:
        logger.error(f"Error saving extraction experiment: {e}")
        db.rollback()
        return {"success": False, "error": str(e)}

@router.post("/internal/classify")
async def internal_classify(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Internal classification endpoint for GPU server - uses existing classification service"""
    try:
        company_offering = request.get("company_offering", "")
        if not company_offering:
            return {"error": "No company offering provided"}
        
        # Import the existing classification service
        from ..services.startup_classifier import classify_startup_offering
        
        # Use the same classification logic as the authenticated endpoint
        classification_result = await classify_startup_offering(
            company_offering,
            db,
            manual_classification=None
        )
        
        return classification_result
        
    except Exception as e:
        logger.error(f"Error in internal classification: {e}")
        return {"error": str(e)}


@router.post("/internal/add-classification-to-experiment")
async def add_classification_to_experiment(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Internal endpoint to add classification data to an experiment for a specific deck"""
    try:
        deck_id = request.get("deck_id")
        classification_data = request.get("classification_data")
        
        if not deck_id or not classification_data:
            return {"error": "Missing deck_id or classification_data"}
        
        # Find experiments containing this deck
        experiments = db.execute(text("""
            SELECT id, experiment_name, classification_results_json, classification_enabled
            FROM extraction_experiments 
            WHERE pitch_deck_ids::text LIKE :deck_search
            ORDER BY id DESC
        """), {"deck_search": f"%{deck_id}%"}).fetchall()
        
        updated_experiments = []
        
        for exp in experiments:
            exp_id = exp[0]
            existing_results = exp[2]
            
            # Parse existing classification results
            if existing_results:
                try:
                    results_list = json.loads(existing_results)
                    if not isinstance(results_list, list):
                        results_list = []
                except:
                    results_list = []
            else:
                results_list = []
            
            # Create classification entry
            classification_entry = {
                "deck_id": deck_id,
                "classification_result": classification_data
            }
            
            # Update or add classification for this deck
            updated = False
            for i, r in enumerate(results_list):
                if r.get('deck_id') == deck_id:
                    results_list[i] = classification_entry
                    updated = True
                    break
            
            if not updated:
                results_list.append(classification_entry)
            
            # Update the experiment
            db.execute(text("""
                UPDATE extraction_experiments 
                SET classification_results_json = :results,
                    classification_enabled = true,
                    classification_completed_at = NOW()
                WHERE id = :exp_id
            """), {
                "results": json.dumps(results_list),
                "exp_id": exp_id
            })
            
            updated_experiments.append(exp_id)
        
        db.commit()
        
        return {
            "success": True,
            "updated_experiments": updated_experiments,
            "deck_id": deck_id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding classification to experiment: {e}")
        return {"error": str(e)}


@router.post("/internal/add-template-results")
async def add_template_results_to_deck(
    request: Dict[str, Any],
    db: Session = Depends(get_db)
):
    """Internal endpoint to add template processing results for a specific deck"""
    try:
        deck_id = request.get("deck_id")
        template_results = request.get("template_results")
        
        if not deck_id or not template_results:
            return {"error": "Missing deck_id or template_results"}
        
        # Store template processing results directly in pitch_decks table
        db.execute(text("""
            UPDATE pitch_decks 
            SET template_processing_results_json = :results_json
            WHERE id = :deck_id
        """), {
            "results_json": json.dumps(template_results),
            "deck_id": deck_id
        })
        
        # Also update extraction experiments containing this deck
        experiments = db.execute(text("""
            SELECT id, template_processing_results_json
            FROM extraction_experiments 
            WHERE pitch_deck_ids::text LIKE :deck_search
        """), {"deck_search": f"%{deck_id}%"}).fetchall()
        
        updated_experiments = []
        
        for exp in experiments:
            exp_id = exp[0]
            existing_results = exp[1]
            
            # Parse existing template results
            if existing_results:
                try:
                    results_data = json.loads(existing_results)
                    if isinstance(results_data, dict):
                        template_processing_results = results_data.get("template_processing_results", [])
                    else:
                        template_processing_results = []
                except:
                    template_processing_results = []
            else:
                template_processing_results = []
            
            # Create template processing entry
            template_entry = {
                "deck_id": deck_id,
                "template_analysis": template_results,
                "processing_success": True,
                "error": None,
                "data_source": "internal"
            }
            
            # Update or add template results for this deck
            updated = False
            for i, r in enumerate(template_processing_results):
                if r.get('deck_id') == deck_id:
                    template_processing_results[i] = template_entry
                    updated = True
                    break
            
            if not updated:
                template_processing_results.append(template_entry)
            
            # Update the experiment
            updated_data = {
                "template_processing_results": template_processing_results,
                "total_decks": len(template_processing_results),
                "successful_template_processing": len([r for r in template_processing_results if r.get("processing_success")]),
                "processing_timestamp": json.dumps({"completed_at": str(datetime.utcnow())})
            }
            
            db.execute(text("""
                UPDATE extraction_experiments 
                SET template_processing_results_json = :results
                WHERE id = :exp_id
            """), {
                "results": json.dumps(updated_data),
                "exp_id": exp_id
            })
            
            updated_experiments.append(exp_id)
        
        db.commit()
        
        return {
            "success": True,
            "deck_id": deck_id,
            "updated_experiments": updated_experiments
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding template results: {e}")
        return {"error": str(e)}

