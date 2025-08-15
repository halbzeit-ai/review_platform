"""
Progress Reporter - Updates backend processing queue with progress during GPU processing

This module provides functionality to report processing progress back to the backend
so the frontend can display real-time progress updates to users.
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

class ProgressReporter:
    """Reports processing progress to backend for frontend display"""
    
    def __init__(self, backend_url: str, document_id: int):
        self.backend_url = backend_url
        self.document_id = document_id
        
    def update_progress(self, percentage: int, current_step: str, message: str, phase: str = "processing") -> bool:
        """
        Update processing progress in the backend queue
        
        Args:
            percentage: Progress percentage (0-100)
            current_step: Current processing step
            message: Detailed progress message
            phase: Processing phase identifier
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Call backend's internal progress update endpoint
            response = requests.post(
                f"{self.backend_url}/api/internal/update-processing-progress",
                json={
                    "document_id": self.document_id,
                    "progress_percentage": percentage,
                    "current_step": current_step,
                    "progress_message": message,
                    "phase": phase
                },
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"📊 Progress updated: {percentage}% - {current_step}")
                return True
            else:
                logger.warning(f"Failed to update progress: {response.status_code} - {response.text}")
                return False
                
        except requests.RequestException as e:
            logger.warning(f"Network error updating progress: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating progress: {e}")
            return False
            
    def report_phase_start(self, phase_name: str, percentage: int) -> bool:
        """Report the start of a processing phase"""
        return self.update_progress(
            percentage, 
            phase_name, 
            f"Starting {phase_name.lower()}", 
            phase_name.lower().replace(' ', '_')
        )
        
    def report_phase_progress(self, phase_name: str, percentage: int, details: str) -> bool:
        """Report progress within a processing phase"""
        return self.update_progress(
            percentage, 
            phase_name, 
            details, 
            phase_name.lower().replace(' ', '_')
        )
        
    def report_phase_complete(self, phase_name: str, percentage: int) -> bool:
        """Report completion of a processing phase"""
        return self.update_progress(
            percentage, 
            f"{phase_name} Complete", 
            f"{phase_name} completed successfully", 
            phase_name.lower().replace(' ', '_')
        )