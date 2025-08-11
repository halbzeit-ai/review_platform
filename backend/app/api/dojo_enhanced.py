"""
Enhanced Dojo ZIP extraction with duplicate detection and unified file structure
"""

import os
import zipfile
import shutil
import logging
import hashlib
import uuid
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from ..db.models import ProjectDocument, Project

logger = logging.getLogger(__name__)

class DojoUploadResult:
    """Result object for dojo upload operations"""
    
    def __init__(self):
        self.total_files = 0
        self.new_files: List[str] = []
        self.duplicate_files: List[str] = []
        self.error_files: List[str] = []
        self.new_pitch_deck_ids: List[int] = []
    
    @property
    def success_count(self) -> int:
        return len(self.new_files)
    
    @property
    def duplicate_count(self) -> int:
        return len(self.duplicate_files)
    
    @property
    def error_count(self) -> int:
        return len(self.error_files)
    
    def to_dict(self) -> Dict:
        return {
            "success": True,
            "summary": {
                "total_files": self.total_files,
                "new_files": self.success_count,
                "duplicate_files": self.duplicate_count,
                "error_files": self.error_count
            },
            "new_files": self.new_files,
            "duplicates": self.duplicate_files,
            "errors": self.error_files,
            "new_pitch_deck_ids": self.new_pitch_deck_ids
        }

def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of a file"""
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def check_duplicate_file(db: Session, file_name: str, file_hash: str) -> Optional[int]:
    """Check if file already exists by name or hash. Returns pitch_deck_id if found."""
    existing = db.query(ProjectDocument).filter(
        ProjectDocument.data_source == "dojo",
        ((ProjectDocument.file_name == file_name) | (ProjectDocument.file_hash == file_hash))
    ).first()
    return existing.id if existing else None

async def extract_dojo_zip_enhanced(
    zip_file_path: str, 
    uploaded_by: int, 
    db: Session, 
    dojo_uploads_path: str,
    original_filename: str = None
) -> DojoUploadResult:
    """
    Enhanced dojo ZIP extraction with duplicate detection and unified structure
    
    Args:
        zip_file_path: Path to uploaded ZIP file
        uploaded_by: User ID who uploaded the file
        db: Database session
        dojo_uploads_path: Path where dojo files should be stored
        original_filename: Original ZIP filename
        
    Returns:
        DojoUploadResult with detailed processing information
    """
    result = DojoUploadResult()
    extract_dir = None
    
    try:
        logger.info(f"Processing enhanced dojo zip file: {zip_file_path}")
        
        # Get original ZIP filename for database storage
        zip_filename = original_filename if original_filename else os.path.basename(zip_file_path)
        
        # Create temporary extraction directory
        extract_dir = os.path.join(os.path.dirname(dojo_uploads_path), f"extract_{uuid.uuid4().hex}")
        os.makedirs(extract_dir, exist_ok=True)
        
        # Extract ZIP file
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        # Find all PDF files in extracted content
        pdf_files = []
        for root, dirs, files in os.walk(extract_dir):
            for file in files:
                if file.lower().endswith('.pdf'):
                    pdf_files.append(os.path.join(root, file))
        
        result.total_files = len(pdf_files)
        logger.info(f"Found {result.total_files} PDF files in dojo upload")
        
        # Ensure dojo uploads directory exists
        os.makedirs(dojo_uploads_path, exist_ok=True)
        
        # Process each PDF file with duplicate detection
        for pdf_path in pdf_files:
            try:
                original_name = os.path.basename(pdf_path)
                
                # Calculate file hash for duplicate detection
                file_hash = calculate_file_hash(pdf_path)
                
                # Check for duplicates
                existing_id = check_duplicate_file(db, original_name, file_hash)
                
                if existing_id:
                    logger.info(f"Duplicate detected: {original_name} (existing ID: {existing_id})")
                    result.duplicate_files.append(original_name)
                    continue
                
                # File is new - process it
                unique_name = f"{uuid.uuid4().hex}_{original_name}"
                final_path = os.path.join(dojo_uploads_path, unique_name)
                
                # Move file to dojo uploads directory
                shutil.move(pdf_path, final_path)
                
                # Create database record
                pitch_deck = ProjectDocument(
                    user_id=uploaded_by,
                    company_id="dojo",
                    file_name=original_name,
                    file_path=f"projects/dojo/uploads/{unique_name}",
                    file_hash=file_hash,
                    data_source="dojo",
                    zip_filename=zip_filename,
                    processing_status="pending"
                )
                
                db.add(pitch_deck)
                db.flush()  # Get the ID
                
                result.new_files.append(original_name)
                result.new_pitch_deck_ids.append(pitch_deck.id)
                
                logger.info(f"Added new file: {original_name} (ID: {pitch_deck.id})")
                
            except Exception as e:
                logger.error(f"Error processing PDF {os.path.basename(pdf_path)}: {e}")
                result.error_files.append(os.path.basename(pdf_path))
                continue
        
        # Commit all database changes
        db.commit()
        
        logger.info(f"Enhanced dojo upload completed: {result.success_count} new, {result.duplicate_count} duplicates, {result.error_count} errors")
        
    except Exception as e:
        logger.error(f"Error in enhanced dojo zip extraction: {e}")
        db.rollback()
        raise
        
    finally:
        # Clean up temporary extraction directory
        if extract_dir and os.path.exists(extract_dir):
            shutil.rmtree(extract_dir, ignore_errors=True)
        
        # Clean up uploaded ZIP file
        if os.path.exists(zip_file_path):
            os.remove(zip_file_path)
    
    return result