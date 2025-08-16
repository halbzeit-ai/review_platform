"""
Volume-based file storage service for shared filesystem

Handles file upload and management for the document processing pipeline.
Primary purpose: Save uploaded PDFs to shared filesystem for GPU processing.

ACTIVE FUNCTIONS:
- File upload management (save_upload, get_file_path, file_exists, etc.)
- Filesystem mount validation (is_filesystem_mounted, is_volume_mounted)
- Basic file operations (delete_file, get_file_size)

DEPRECATED FUNCTIONS (2025-08-16):
- Processing coordination (removed - now uses database queue system)
- Results management (removed - now stored in database tables)
- Processing markers (removed - replaced by processing_queue.status)
"""
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional, BinaryIO
from ..core.config import settings
import logging

logger = logging.getLogger(__name__)

class VolumeStorageService:
    def __init__(self):
        self.mount_path = Path(settings.SHARED_FILESYSTEM_MOUNT_PATH)
        self.uploads_dir = self.mount_path / "uploads"
        self.results_dir = self.mount_path / "results"  # Legacy - for deprecated methods only
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist"""
        # Only create uploads directory - results stored in database now
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {self.uploads_dir}")
        
        # Create results directory for backward compatibility with deprecated methods
        self.results_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured legacy results directory exists: {self.results_dir}")
    
    def is_filesystem_mounted(self) -> bool:
        """Check if the shared filesystem is mounted"""
        return self.mount_path.exists() and self.mount_path.is_dir()
    
    # Keep old method name for compatibility
    def is_volume_mounted(self) -> bool:
        """Check if the shared filesystem is mounted (legacy method name)"""
        return self.is_filesystem_mounted()
    
    def save_upload(self, file: BinaryIO, original_filename: str, company_name: str) -> str:
        """
        Save uploaded file to shared filesystem
        Returns: relative file path for database storage
        """
        if not self.is_filesystem_mounted():
            raise Exception("Shared filesystem is not mounted")
        
        # Generate unique filename structure
        file_id = str(uuid.uuid4())
        company_dir = self.uploads_dir / company_name.replace(" ", "_").lower()
        file_dir = company_dir / file_id
        
        # Create directory structure
        file_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file
        file_path = file_dir / original_filename
        
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file, f)
        
        # Return relative path for database storage
        relative_path = f"uploads/{company_name.replace(' ', '_').lower()}/{file_id}/{original_filename}"
        logger.info(f"Saved file to: {relative_path}")
        
        return relative_path
    
    def get_file_path(self, relative_path: str) -> Path:
        """Get absolute file path from relative path"""
        return self.mount_path / relative_path
    
    def file_exists(self, relative_path: str) -> bool:
        """Check if file exists"""
        return self.get_file_path(relative_path).exists()
    
    def get_file_size(self, relative_path: str) -> int:
        """Get file size in bytes"""
        file_path = self.get_file_path(relative_path)
        return file_path.stat().st_size if file_path.exists() else 0
    
    def delete_file(self, relative_path: str) -> bool:
        """Delete file from volume"""
        file_path = self.get_file_path(relative_path)
        if file_path.exists():
            file_path.unlink()
            # Try to remove empty directories
            try:
                file_path.parent.rmdir()
                file_path.parent.parent.rmdir()
            except OSError:
                pass  # Directory not empty, that's fine
            return True
        return False
    
    # REMOVED: Processing marker methods (2025-08-16)
    # Processing coordination now handled entirely by database queue system:
    # - processing_queue.status tracks task status
    # - project_documents.processing_status tracks document status
    # - No need for .processing marker files
    
    def save_results(self, relative_upload_path: str, results_data: dict) -> str:
        """
        DEPRECATED: Save processing results to filesystem
        
        This method is deprecated as of 2025-08-16. All new processing results
        should be stored directly in database tables via queue completion callbacks.
        
        Use database storage instead:
        - Template processing: Store in extraction_experiments.template_processing_results_json
        - Visual analysis: Store in visual_analysis_cache.analysis_result_json
        """
        logger.warning(f"DEPRECATED: save_results() called for {relative_upload_path}")
        logger.warning("Use database storage via queue completion callbacks instead")
        
        # Create results filename based on upload path
        results_filename = relative_upload_path.replace('/', '_').replace('.pdf', '_results.json')
        results_path = self.results_dir / results_filename
        
        import json
        with open(results_path, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        relative_results_path = f"results/{results_filename}"
        logger.info(f"Saved legacy results to: {relative_results_path}")
        
        return relative_results_path
    
    def get_results(self, relative_results_path: str) -> Optional[dict]:
        """
        DEPRECATED: Get processing results from files
        
        This method is deprecated as of 2025-08-16. All new processing results
        are stored in database tables (extraction_experiments, visual_analysis_cache)
        instead of physical JSON files.
        
        Use database queries instead:
        - Template processing results: extraction_experiments.template_processing_results_json
        - Visual analysis results: visual_analysis_cache.analysis_result_json
        """
        logger.warning(f"DEPRECATED: get_results() called for {relative_results_path}")
        logger.warning("Use database queries for extraction_experiments or visual_analysis_cache instead")
        
        results_path = self.get_file_path(relative_results_path)
        if not results_path.exists():
            logger.info(f"Results file does not exist: {results_path}")
            return None
        
        import json
        try:
            with open(results_path, 'r') as f:
                content = f.read()
                logger.info(f"Reading legacy results file: {results_path}")
                logger.info(f"Results file content length: {len(content)} chars")
                logger.debug(f"Results file content preview: {content[:200]}...")
                return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in results file {results_path}: {e}")
            logger.error(f"File content: {content}")
            # Clean up the invalid file to prevent future errors
            try:
                results_path.unlink()
                logger.info(f"Removed invalid results file: {results_path}")
            except:
                pass
            raise Exception(f"Invalid JSON in results file: {e}")
    
    def list_pending_uploads(self) -> list:
        """
        DEPRECATED: List files that need processing
        
        This method is deprecated as of 2025-08-16. Processing status is now
        tracked in the database queue system, not file-based markers.
        
        Use database queries instead:
        - Query project_documents for documents without processing_status='completed'
        - Query processing_queue for pending/failed tasks
        """
        logger.warning("DEPRECATED: list_pending_uploads() called")
        logger.warning("Use database queries on project_documents and processing_queue instead")
        
        return []  # Return empty list - all tracking is now database-based

# Global storage service instance
volume_storage = VolumeStorageService()