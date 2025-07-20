"""
Dojo API Endpoints
Handles training data uploads and management for GPs
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import os
import zipfile
import shutil
import logging
from pathlib import Path
import uuid
from datetime import datetime

from ..db.database import get_db
from ..db.models import User, PitchDeck
from .auth import get_current_user

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
        
        # Store zip file for manual processing later
        # Note: Processing is now manual, not automatic
        
        logger.info(f"Dojo zip upload initiated by {current_user.email}: {file.filename} ({file_size} bytes)")
        
        return {
            "message": "Dojo training data uploaded successfully",
            "filename": file.filename,
            "size": file_size,
            "status": "uploaded",
            "zip_path": temp_file_path
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