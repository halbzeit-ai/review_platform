"""
Task Validator - Checks if a processing task is still valid (not deleted)

This module provides functionality to check if a document/task has been deleted
while processing is ongoing, allowing the GPU to abort processing for deleted tasks.
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class TaskValidator:
    """Validates if a processing task is still active and not deleted"""
    
    def __init__(self, backend_url: str):
        self.backend_url = backend_url
        
    def is_task_valid(self, document_id: int) -> bool:
        """
        Check if a document/task is still valid (not deleted)
        
        Args:
            document_id: The document ID to check
            
        Returns:
            True if task is still valid, False if deleted or error
        """
        try:
            # Query backend to check if document still exists
            response = requests.get(
                f"{self.backend_url}/api/internal/check-document-exists/{document_id}",
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                exists = data.get("exists", False)
                if not exists:
                    logger.warning(f"⚠️ Document {document_id} has been deleted - aborting processing")
                return exists
            elif response.status_code == 404:
                logger.warning(f"⚠️ Document {document_id} not found - likely deleted")
                return False
            else:
                # On error, assume task is still valid to avoid false aborts
                logger.error(f"Error checking document {document_id} validity: {response.status_code}")
                return True
                
        except requests.RequestException as e:
            # On network error, assume task is still valid
            logger.error(f"Network error checking document {document_id} validity: {e}")
            return True
        except Exception as e:
            # On any other error, assume task is still valid
            logger.error(f"Unexpected error checking document {document_id} validity: {e}")
            return True
    
    def check_and_abort_if_deleted(self, document_id: int, stage: str = "processing") -> bool:
        """
        Check if document was deleted and log appropriate abort message
        
        Args:
            document_id: The document ID to check
            stage: Current processing stage for logging
            
        Returns:
            True if should continue processing, False if should abort
        """
        if not self.is_task_valid(document_id):
            logger.warning(f"🛑 ABORTING {stage} for document {document_id} - Document was deleted by user")
            logger.info(f"📊 Processing statistics for aborted document {document_id}:")
            logger.info(f"  - Stage reached: {stage}")
            logger.info(f"  - Reason: User deleted document during processing")
            logger.info(f"  - Action: Cleanly aborting all processing")
            return False
        return True