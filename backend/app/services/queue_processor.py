"""
Queue Processor - Polls processing queue and sends tasks to GPU server
"""

import asyncio
import logging
import httpx
import json
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from ..db.database import SessionLocal
from .processing_queue import processing_queue_manager, ProcessingTask, TaskStatus
from ..core.config import settings

logger = logging.getLogger(__name__)

class QueueProcessor:
    """Background task that polls the processing queue and sends tasks to GPU"""
    
    def __init__(self):
        self.running = False
        self.poll_interval = 5  # seconds
        self.gpu_url = self._get_gpu_url()
        self.backend_url = self._get_backend_url()
        logger.info(f"Queue processor initialized - GPU URL: {self.gpu_url}, Backend URL: {self.backend_url}")
    
    def _get_gpu_url(self) -> str:
        """Get GPU server URL based on environment"""
        environment = settings.ENVIRONMENT
        if environment == "production":
            gpu_host = settings.GPU_PRODUCTION
            return f"http://{gpu_host}:8001"
        else:
            gpu_host = settings.GPU_DEVELOPMENT  
            return f"http://{gpu_host}:8001"
    
    def _get_backend_url(self) -> str:
        """Get backend URL for callbacks"""
        environment = settings.ENVIRONMENT
        if environment == "production":
            return settings.BACKEND_PRODUCTION
        else:
            return settings.BACKEND_DEVELOPMENT
    
    async def start(self):
        """Start the queue processor"""
        self.running = True
        logger.info("Starting queue processor background task")
        
        # Register server
        db = SessionLocal()
        try:
            processing_queue_manager.register_server(db)
            # Recover any abandoned tasks
            recovered = processing_queue_manager.recover_abandoned_tasks(db)
            if recovered > 0:
                logger.info(f"Recovered {recovered} abandoned tasks")
        finally:
            db.close()
        
        # Start processing loop
        while self.running:
            try:
                await self.process_next_task()
            except Exception as e:
                logger.error(f"Error in queue processor loop: {e}")
            
            await asyncio.sleep(self.poll_interval)
    
    async def stop(self):
        """Stop the queue processor"""
        self.running = False
        logger.info("Stopping queue processor")
    
    async def process_next_task(self):
        """Get and process the next task from queue"""
        db = SessionLocal()
        try:
            # Get next task
            task = processing_queue_manager.get_next_task(db)
            if not task:
                db.commit()  # Commit the get_next_task transaction
                return
            
            logger.info(f"Processing task {task.id} for document {task.document_id}")
            
            # Update progress
            processing_queue_manager.update_task_progress(
                task.id, 5, "Sending to GPU for processing", "Task picked up by queue processor", db
            )
            db.commit()  # Commit progress update immediately
            
            # Use split processing for incremental progress updates
            logger.info(f"Using split processing for task {task.id}")
            success = await self.send_to_gpu_split_processing(task, db)
            
            if not success:
                # Mark as failed if couldn't send to GPU
                processing_queue_manager.complete_task(
                    task.id, 
                    False,  # success = False 
                    None,   # results_path
                    "Failed to send task to GPU server",  # error_message
                    None,   # metadata
                    db
                )
                db.commit()  # Commit failure state
            else:
                db.commit()  # Commit success state
        
        except Exception as e:
            logger.error(f"Error processing task: {e}", exc_info=True)
            try:
                db.rollback()  # Rollback on error
            except Exception as rollback_error:
                logger.error(f"Error during rollback: {rollback_error}")
        finally:
            try:
                db.close()
            except Exception as close_error:
                logger.error(f"Error closing database session: {close_error}")
    
    async def send_to_gpu(self, task: ProcessingTask, db: Session) -> bool:
        """Send task to GPU server for processing"""
        try:
            # Prepare request data
            # Convert relative path to absolute path
            full_file_path = task.file_path
            if not full_file_path.startswith('/'):
                full_file_path = f"{settings.SHARED_FILESYSTEM_MOUNT_PATH}/{task.file_path}"
            
            request_data = {
                "task_id": task.id,
                "document_id": task.document_id,  # Renamed from pitch_deck_id
                "file_path": full_file_path,
                "company_id": task.company_id,
                "callback_url": f"{self.backend_url}/api/internal/update-deck-results",
                "processing_options": task.processing_options
            }
            
            logger.info(f"Sending task {task.id} to GPU server at {self.gpu_url}/api/process-pdf")
            logger.info(f"Request data: {json.dumps(request_data, indent=2)}")
            
            # Send request to GPU
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.gpu_url}/api/process-pdf",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"GPU accepted task {task.id}: {result.get('message', 'Processing started')}")
                    
                    # Update progress
                    processing_queue_manager.update_task_progress(
                        task.id, 10, "GPU processing started", 
                        f"Task sent to GPU successfully", db
                    )
                    return True
                else:
                    logger.error(f"GPU server returned error {response.status_code}: {response.text}")
                    return False
                    
        except httpx.ConnectError:
            logger.error(f"Failed to connect to GPU server at {self.gpu_url}")
            return False
        except Exception as e:
            logger.error(f"Error sending task to GPU: {e}", exc_info=True)
            return False
    
    async def send_to_gpu_split_processing(self, task: ProcessingTask, db: Session) -> bool:
        """Send task to GPU using split processing approach with incremental progress updates"""
        try:
            # Prepare common data
            full_file_path = task.file_path
            if not full_file_path.startswith('/'):
                full_file_path = f"{settings.SHARED_FILESYSTEM_MOUNT_PATH}/{task.file_path}"
            
            progress_callback_url = f"{self.backend_url}/api/internal/update-processing-progress"
            
            # Phase 1: Visual Analysis (10% -> 30%)
            logger.info(f"Phase 1: Starting visual analysis for document {task.document_id}")
            await self.update_progress(task.document_id, 10, "Visual Analysis", "Analyzing slides and extracting content", db)
            
            visual_success = await self.run_visual_analysis_phase(task, full_file_path, db)
            if not visual_success:
                logger.error(f"Visual analysis failed for document {task.document_id} - failing task")
                await self.fail_task_with_error(task, "Visual analysis failed - could not process slides", db)
                return False
                
            await self.update_progress(task.document_id, 30, "Visual Analysis Complete", "Slides analyzed, starting extraction", db)
            
            # Phase 2: Extraction (30% -> 60%)
            logger.info(f"Phase 2: Starting extraction for document {task.document_id}")
            await self.update_progress(task.document_id, 40, "Data Extraction", "Extracting company details and classification", db)
            
            extraction_success = await self.run_extraction_phase(task, db)
            if not extraction_success:
                logger.error(f"Extraction failed for document {task.document_id} - failing task")
                await self.fail_task_with_error(task, "Data extraction failed - could not extract company details", db)
                return False
                
            await self.update_progress(task.document_id, 60, "Extraction Complete", "Company data extracted, starting template analysis", db)
            
            # Phase 3: Template Analysis (60% -> 95%)
            logger.info(f"Phase 3: Starting template analysis for document {task.document_id}")
            await self.update_progress(task.document_id, 70, "Template Analysis", "Running AI analysis with healthcare templates", db)
            
            template_success = await self.run_template_analysis_phase(task, progress_callback_url, db)
            if not template_success:
                logger.error(f"Template analysis failed for document {task.document_id} - failing task")
                await self.fail_task_with_error(task, "Template analysis failed - could not complete AI analysis", db)
                return False
                
            # Phase 4: Specialized Analysis (80% -> 95%)
            logger.info(f"Phase 4: Starting specialized analysis for document {task.document_id}")
            await self.update_progress(task.document_id, 80, "Specialized Analysis", "Running regulatory, clinical, and scientific analysis", db)
            
            specialized_success = await self.run_specialized_analysis_phase(task, progress_callback_url, db)
            if not specialized_success:
                logger.warning(f"Specialized analysis failed for document {task.document_id} - continuing (not critical)")
                # Don't fail the whole task if specialized analysis fails - it's optional
                
            await self.update_progress(task.document_id, 95, "Analysis Complete", "Finalizing results", db)
            
            # CRITICAL: Manually complete the task since template processing doesn't send final callback
            logger.info(f"Split processing completed successfully for task {task.id} - marking as completed")
            processing_queue_manager.complete_task(
                task.id, 
                True,  # success = True
                None,  # results_path
                None,  # error_message
                None,  # metadata
                db
            )
            
            # Also update project document status
            from sqlalchemy import text
            db.execute(text(
                "UPDATE project_documents SET processing_status = 'completed' WHERE id = :document_id"
            ), {"document_id": task.document_id})
            db.commit()
            
            logger.info(f"Task {task.id} marked as completed in both processing_queue and project_documents")
            return True
            
        except Exception as e:
            logger.error(f"Error in split processing for task {task.id}: {e}", exc_info=True)
            return False
    
    async def update_progress(self, document_id: int, percentage: int, step: str, message: str, db: Session):
        """Update processing progress via internal API"""
        try:
            # Get task ID from document_id
            from sqlalchemy import text
            result = db.execute(text(
                "SELECT id FROM processing_queue WHERE document_id = :document_id AND status = 'processing'"
            ), {"document_id": document_id}).fetchone()
            
            if result:
                task_id = result[0]
                processing_queue_manager.update_task_progress(
                    task_id, percentage, step, message, db
                )
            else:
                logger.warning(f"No processing task found for document {document_id}")
        except Exception as e:
            logger.error(f"Error updating progress for document {document_id}: {e}")
    
    async def fail_task_with_error(self, task: ProcessingTask, error_message: str, db: Session):
        """Mark task as failed with clear error message"""
        try:
            logger.error(f"Failing task {task.id} for document {task.document_id}: {error_message}")
            
            processing_queue_manager.complete_task(
                task.id, 
                False,  # success = False for failed tasks
                None,   # results_path
                error_message,  # error_message
                None,   # metadata
                db
            )
            
            # Also update the project document status
            from sqlalchemy import text
            db.execute(text(
                "UPDATE project_documents SET processing_status = 'failed' WHERE id = :document_id"
            ), {"document_id": task.document_id})
            db.commit()
            
            logger.info(f"Task {task.id} marked as failed with error: {error_message}")
            
        except Exception as e:
            logger.error(f"Error failing task {task.id}: {e}")
    
    async def run_visual_analysis_phase(self, task: ProcessingTask, full_file_path: str, db: Session) -> bool:
        """Run visual analysis phase using existing Dojo infrastructure"""
        try:
            # Retrieve configured models from database - CRITICAL for startup processing
            from sqlalchemy import text
            vision_model = db.execute(text(
                "SELECT model_name FROM model_configs WHERE model_type = 'vision' AND is_active = true LIMIT 1"
            )).scalar()
            
            if not vision_model:
                logger.error("No active vision model configured in database")
                return False
                
            logger.info(f"Using database-configured vision model: {vision_model}")
            
            # The visual analysis batch API expects deck_ids, file_paths, vision_model, and analysis_prompt
            request_data = {
                "deck_ids": [task.document_id],
                "file_paths": [full_file_path],
                "vision_model": vision_model  # CRITICAL: Send database-configured model
                # analysis_prompt will be loaded by GPU from database
            }
            
            logger.info(f"Visual analysis request: deck_id={task.document_id}, file_path={full_file_path}")
            logger.info(f"Request data being sent: {json.dumps(request_data, indent=2)}")
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.gpu_url}/api/run-visual-analysis-batch",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Visual analysis completed for document {task.document_id}")
                    
                    # STEP 4a: Generate slide feedback immediately after visual analysis
                    feedback_success = await self.generate_slide_feedback(task.document_id, db)
                    if feedback_success:
                        logger.info(f"Slide feedback generated for document {task.document_id}")
                    else:
                        logger.warning(f"Slide feedback generation failed for document {task.document_id}, but continuing...")
                    
                    return True
                else:
                    logger.error(f"Visual analysis failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error in visual analysis phase: {e}")
            return False

    async def generate_slide_feedback(self, document_id: int, db: Session) -> bool:
        """Generate slide feedback using slide_feedback prompt from visual analysis results"""
        try:
            from sqlalchemy import text
            from ..db.models import SlideFeedback
            import json
            
            # Get visual analysis results
            visual_cache = db.execute(text("""
                SELECT analysis_result_json FROM visual_analysis_cache 
                WHERE document_id = :document_id
                ORDER BY created_at DESC
                LIMIT 1
            """), {"document_id": document_id}).fetchone()
            
            if not visual_cache or not visual_cache[0]:
                logger.error(f"No visual analysis found for document {document_id}")
                return False
            
            visual_data = json.loads(visual_cache[0])
            slides = visual_data.get('visual_analysis_results', [])
            
            # Get slide feedback prompt
            feedback_prompt = db.execute(text(
                "SELECT prompt_text FROM pipeline_prompts WHERE stage_name = 'slide_feedback' AND is_active = true LIMIT 1"
            )).scalar()
            
            if not feedback_prompt:
                logger.error("No slide_feedback prompt found in database")
                return False
            
            # Generate feedback for each slide using GPU
            for slide in slides:
                slide_num = slide.get('page_number', 1)
                slide_image_path = slide.get('slide_image_path', '')
                
                # Format prompt for image-based analysis
                formatted_prompt = feedback_prompt.replace('{slide_number}', str(slide_num))
                
                # Call GPU for image-based feedback generation
                feedback_text = await self.call_gpu_for_feedback(formatted_prompt, slide_image_path, db)
                
                if feedback_text:
                    # Save feedback to database
                    feedback_entry = SlideFeedback(
                        document_id=document_id,
                        slide_number=slide_num,
                        slide_filename=slide_image_path,
                        feedback_text=feedback_text,
                        feedback_type='ai_analysis'
                    )
                    db.add(feedback_entry)
                    logger.info(f"Generated feedback for slide {slide_num} of document {document_id}")
                else:
                    logger.warning(f"Failed to generate feedback for slide {slide_num} of document {document_id}")
            
            db.commit()
            logger.info(f"Completed slide feedback generation for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error generating slide feedback for document {document_id}: {e}")
            db.rollback()
            return False

    async def call_gpu_for_feedback(self, prompt: str, slide_image_path: str, db: Session) -> str:
        """Call GPU to generate feedback text using vision model on slide image"""
        try:
            from sqlalchemy import text
            import os
            
            # Get vision model for image-based feedback generation - same as visual analysis
            vision_model = db.execute(text(
                "SELECT model_name FROM model_configs WHERE model_type = 'vision' AND is_active = true LIMIT 1"
            )).scalar()
            
            if not vision_model:
                logger.error("No active vision model configured in database for feedback generation")
                return ""
                
            logger.info(f"Using database-configured vision model for feedback: {vision_model}")
            
            # Construct full path to slide image
            if not slide_image_path:
                logger.error("No slide image path provided for feedback generation")
                return ""
                
            # Use shared filesystem path for validation
            from ..core.config import settings
            full_image_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, slide_image_path.lstrip('/'))
            
            if not os.path.exists(full_image_path):
                logger.error(f"Slide image not found: {full_image_path}")
                return ""
            
            # Call GPU vision analysis endpoint for single image
            # CRITICAL: Send relative path, not absolute - GPU will construct full path
            request_data = {
                "images": [slide_image_path],
                "prompt": prompt,
                "model": vision_model,
                "options": {
                    "num_ctx": 32768,  # Increased context size for better feedback generation
                    "temperature": 0.3
                }
            }
            
            async with httpx.AsyncClient(timeout=120.0) as client:  # Longer timeout for vision processing
                response = await client.post(
                    f"{self.gpu_url}/analyze-images",  # GPU vision endpoint
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    # Extract feedback text from vision analysis results
                    if "results" in result and isinstance(result["results"], list) and len(result["results"]) > 0:
                        return result["results"][0].get("analysis", "").strip()
                    elif "analysis" in result:
                        return result.get("analysis", "").strip()
                    else:
                        logger.warning(f"Unexpected response format from GPU vision analysis: {result}")
                        return ""
                else:
                    logger.error(f"GPU vision feedback generation failed: {response.status_code} - {response.text}")
                    return ""
                    
        except Exception as e:
            logger.error(f"Error calling GPU for vision-based feedback: {e}")
            return ""
    
    async def run_extraction_phase(self, task: ProcessingTask, db: Session) -> bool:
        """Run extraction phase (company offering, classification, etc.)"""
        try:
            logger.info(f"Running Dojo Step 3 extractions for document {task.document_id}")
            
            # Prepare request for extraction
            request_data = {
                "deck_ids": [task.document_id],
                "experiment_name": f"extraction_deck_{task.document_id}",
                "extraction_type": "all",  # Run all extractions
                "text_model": "gemma3:12b",
                "processing_options": {
                    "do_classification": True,
                    "extract_company_name": True,
                    "extract_funding_amount": True,
                    "extract_deck_date": True
                }
            }
            
            logger.info(f"Calling GPU extraction endpoint for document {task.document_id}")
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{self.gpu_url}/api/run-extraction-experiment",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Extraction completed: offering, classification, company name, funding, date for document {task.document_id}")
                    
                    # Save extraction results if needed
                    if result.get('success'):
                        # The results are stored in the extraction_experiments table by the GPU
                        logger.info(f"Extraction phase completed successfully for document {task.document_id}")
                        return True
                    else:
                        logger.error(f"Extraction failed: {result.get('error')}")
                        return False
                else:
                    logger.error(f"Extraction request failed: {response.status_code} - {response.text}")
                    return False
            
        except Exception as e:
            logger.error(f"Error in extraction phase: {e}")
            return False
    
    async def run_template_analysis_phase(self, task: ProcessingTask, progress_callback_url: str, db: Session) -> bool:
        """Run template analysis phase using existing template processing infrastructure"""
        try:
            # Get template configuration from processing options
            processing_options = task.processing_options or {}
            
            # Determine template to use
            if processing_options.get('use_single_template') and processing_options.get('selected_template_id'):
                template_id = processing_options['selected_template_id']
                logger.info(f"Using GP override template {template_id} for document {task.document_id}")
            else:
                # Get default template from database
                from sqlalchemy import text
                default_template_id = db.execute(text(
                    "SELECT id FROM analysis_templates WHERE is_default = true LIMIT 1"
                )).scalar()
                template_id = default_template_id or 5  # Fallback to template 5 if no default
                logger.info(f"Using default template {template_id} for document {task.document_id}")
            
            request_data = {
                "deck_ids": [task.document_id],
                "template_id": template_id,  # Always include template_id  
                "processing_options": {
                    "generate_thumbnails": True,
                    "callback_url": f"{self.backend_url}/api/internal/update-deck-results"
                }
            }
            
            async with httpx.AsyncClient(timeout=600.0) as client:  # Longer timeout for template analysis
                response = await client.post(
                    f"{self.gpu_url}/api/run-template-processing-only",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Template analysis completed for document {task.document_id}")
                    
                    # GPU handles all saving via internal endpoints (/save-template-processing)
                    # Queue processor just needs to check if GPU processing was successful
                    if result.get('success'):
                        logger.info(f"✅ GPU successfully completed template processing for document {task.document_id}")
                        return True
                    else:
                        logger.error(f"❌ GPU template processing failed for document {task.document_id}")
                        return False
                    
                    return True
                else:
                    logger.error(f"Template analysis failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error in template analysis phase: {e}")
            return False

    async def run_specialized_analysis_phase(self, task: ProcessingTask, progress_callback_url: str, db: Session) -> bool:
        """Run specialized analysis phase (regulatory, clinical, scientific) - separate from template processing"""
        try:
            logger.info(f"Starting specialized analysis phase for document {task.document_id}")
            
            request_data = {
                "deck_ids": [task.document_id],
                "processing_options": {
                    "generate_thumbnails": False,  # Not needed for specialized analysis
                    "callback_url": f"{self.backend_url}/api/internal/update-deck-results"
                }
            }
            
            async with httpx.AsyncClient(timeout=600.0) as client:  # Longer timeout for specialized analysis
                response = await client.post(
                    f"{self.gpu_url}/api/run-specialized-analysis-only",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"Specialized analysis completed for document {task.document_id}")
                    
                    # GPU handles all saving via internal endpoints (/save-specialized-analysis)
                    # Queue processor just needs to check if GPU processing was successful
                    if result.get('success'):
                        logger.info(f"✅ GPU successfully completed specialized analysis for document {task.document_id}")
                        return True
                    else:
                        logger.error(f"❌ GPU specialized analysis failed for document {task.document_id}")
                        return False
                else:
                    logger.error(f"Specialized analysis failed: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error in specialized analysis phase: {e}")
            return False

# Global queue processor instance
queue_processor = QueueProcessor()