"""
Volume-based file storage service for Datacrunch.io shared volumes
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
        self.results_dir = self.mount_path / "results"
        self.temp_dir = self.mount_path / "temp"
        
        # Create directories if they don't exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        for directory in [self.uploads_dir, self.results_dir, self.temp_dir]:
            directory.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {directory}")
    
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
    
    def create_processing_marker(self, relative_path: str) -> str:
        """Create a marker file to indicate processing has started"""
        marker_path = self.temp_dir / f"{relative_path.replace('/', '_')}.processing"
        marker_path.touch()
        return str(marker_path)
    
    def remove_processing_marker(self, relative_path: str):
        """Remove processing marker"""
        marker_path = self.temp_dir / f"{relative_path.replace('/', '_')}.processing"
        if marker_path.exists():
            marker_path.unlink()
    
    def is_processing(self, relative_path: str) -> bool:
        """Check if file is currently being processed"""
        marker_path = self.temp_dir / f"{relative_path.replace('/', '_')}.processing"
        return marker_path.exists()
    
    def save_results(self, relative_upload_path: str, results_data: dict) -> str:
        """Save processing results"""
        # Create results filename based on upload path
        results_filename = relative_upload_path.replace('/', '_').replace('.pdf', '_results.json')
        results_path = self.results_dir / results_filename
        
        import json
        with open(results_path, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        relative_results_path = f"results/{results_filename}"
        logger.info(f"Saved results to: {relative_results_path}")
        
        return relative_results_path
    
    def get_results(self, relative_results_path: str) -> Optional[dict]:
        """Get processing results"""
        results_path = self.get_file_path(relative_results_path)
        if not results_path.exists():
            return None
        
        import json
        try:
            with open(results_path, 'r') as f:
                content = f.read()
                logger.info(f"Results file content length: {len(content)} chars")
                logger.debug(f"Results file content preview: {content[:200]}...")
                return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error in results file {results_path}: {e}")
            logger.error(f"File content: {content}")
            raise Exception(f"Invalid JSON in results file: {e}")
    
    def list_pending_uploads(self) -> list:
        """List files that need processing (no corresponding results)"""
        pending = []
        
        for company_dir in self.uploads_dir.iterdir():
            if not company_dir.is_dir():
                continue
                
            for file_dir in company_dir.iterdir():
                if not file_dir.is_dir():
                    continue
                    
                for file_path in file_dir.iterdir():
                    if file_path.suffix.lower() == '.pdf':
                        relative_path = str(file_path.relative_to(self.mount_path))
                        
                        # Check if results exist
                        results_filename = relative_path.replace('/', '_').replace('.pdf', '_results.json')
                        results_path = self.results_dir / results_filename
                        
                        if not results_path.exists() and not self.is_processing(relative_path):
                            pending.append(relative_path)
        
        return pending

# Global storage service instance
volume_storage = VolumeStorageService()