#!/usr/bin/env python3
"""
GPU Job Monitor
Monitors shared filesystem for processing jobs and executes them
"""

import os
import json
import time
import glob
import logging
from pathlib import Path
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GPUJobMonitor:
    """Monitor for processing jobs in shared filesystem"""
    
    def __init__(self, mount_path: str = "/mnt/shared"):
        self.mount_path = mount_path
        self.queue_path = os.path.join(mount_path, "queue")
        self.results_path = os.path.join(mount_path, "results")
        self.processing_path = os.path.join(mount_path, "gpu_processing")
        
        # Ensure directories exist
        os.makedirs(self.queue_path, exist_ok=True)
        os.makedirs(self.results_path, exist_ok=True)
        
        logger.info(f"GPU Job Monitor initialized")
        logger.info(f"Queue path: {self.queue_path}")
        logger.info(f"Results path: {self.results_path}")
        logger.info(f"Processing path: {self.processing_path}")
    
    def monitor_jobs(self):
        """Main monitoring loop"""
        logger.info("Starting job monitoring...")
        
        while True:
            try:
                # Look for new job files
                job_files = glob.glob(os.path.join(self.queue_path, "*.json"))
                
                if job_files:
                    logger.info(f"Found {len(job_files)} job(s) to process")
                    
                    for job_file in job_files:
                        try:
                            self.process_job(job_file)
                        except Exception as e:
                            logger.error(f"Error processing job {job_file}: {e}")
                            self.create_error_file(job_file, str(e))
                
                # Wait before checking again
                time.sleep(5)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(10)
    
    def process_job(self, job_file: str):
        """Process a single job file"""
        logger.info(f"Processing job file: {job_file}")
        
        # Read job data
        with open(job_file, 'r') as f:
            job_data = json.load(f)
        
        job_id = job_data['job_id']
        file_path = job_data['file_path']
        
        logger.info(f"Processing job {job_id} for file: {file_path}")
        
        # Import the processor (must be in the same directory)
        import sys
        sys.path.append(self.processing_path)
        from main import PDFProcessor
        
        try:
            # Initialize processor
            processor = PDFProcessor(self.mount_path)
            
            # Process the PDF
            results = processor.process_pdf(file_path)
            
            # Save results with job_id format for backend
            results_file = os.path.join(self.results_path, f"{job_id}_results.json")
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"Job {job_id} completed successfully")
            logger.info(f"Results saved to: {results_file}")
            
            # Remove job file
            os.remove(job_file)
            
        except Exception as e:
            logger.error(f"Job {job_id} failed: {e}")
            self.create_error_file(job_file, str(e))
            raise
    
    def create_error_file(self, job_file: str, error_message: str):
        """Create error file for failed job"""
        try:
            # Extract job ID from filename
            job_filename = os.path.basename(job_file)
            job_id = job_filename.replace('.json', '')
            
            error_file = os.path.join(self.results_path, f"{job_id}_error.json")
            error_data = {
                "job_id": job_id,
                "error": error_message,
                "timestamp": time.time()
            }
            
            with open(error_file, 'w') as f:
                json.dump(error_data, f, indent=2)
            
            logger.info(f"Created error file: {error_file}")
            
            # Remove job file
            os.remove(job_file)
            
        except Exception as e:
            logger.error(f"Failed to create error file: {e}")

def main():
    """Main entry point"""
    mount_path = os.environ.get('SHARED_FILESYSTEM_MOUNT_PATH', '/mnt/shared')
    
    monitor = GPUJobMonitor(mount_path)
    monitor.monitor_jobs()

if __name__ == "__main__":
    main()