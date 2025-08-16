"""
Internal API endpoints for GPU processing communication
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from typing import Dict, Any, Optional
import logging
import json
from datetime import datetime

from ..db.database import get_db
from ..services.processing_queue import processing_queue_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])

class DeckResultsUpdateRequest(BaseModel):
    document_id: int
    results_file_path: str
    processing_status: str

class ExtractionTemplateResultsRequest(BaseModel):
    document_id: int
    company_offering: str
    startup_name: Optional[str]
    funding_amount: Optional[str]
    deck_date: Optional[str]
    classification: Optional[Dict[str, Any]]
    chapter_analysis: Optional[Dict[str, Any]]
    question_analysis: Optional[Dict[str, Any]]
    overall_score: Optional[float]
    template_used: Optional[Dict[str, Any]]
    processing_metadata: Optional[Dict[str, Any]]

@router.post("/update-deck-results")
async def update_deck_results(
    request: DeckResultsUpdateRequest,
    db: Session = Depends(get_db)
):
    """Internal endpoint for GPU processing to update deck results"""
    try:
        logger.info(f"🔍 DEBUG: Received update request for document {request.document_id}")
        logger.info(f"🔍 DEBUG: Results file: {request.results_file_path}")
        logger.info(f"🔍 DEBUG: Status: {request.processing_status}")
        
        # Check if the document exists first
        check_query = text("SELECT id, file_name FROM project_documents WHERE id = :document_id")
        check_result = db.execute(check_query, {"document_id": request.document_id})
        deck = check_result.fetchone()
        
        if deck:
            logger.info(f"🔍 DEBUG: Found document {deck[0]}: {deck[1]}")
        else:
            logger.error(f"🔍 DEBUG: No document found with ID {request.document_id}")
            # List all existing documents for debugging
            all_docs = db.execute(text("SELECT id, file_name FROM project_documents ORDER BY id")).fetchall()
            logger.error(f"🔍 DEBUG: Available documents: {[(d[0], d[1]) for d in all_docs]}")
        
        # Update the project_documents table
        update_query = text("""
            UPDATE project_documents 
            SET analysis_results_path = :results_file_path, processing_status = :processing_status
            WHERE id = :document_id
        """)
        
        result = db.execute(update_query, {
            "results_file_path": request.results_file_path,
            "processing_status": request.processing_status,
            "document_id": request.document_id
        })
        
        logger.info(f"🔍 DEBUG: Project documents update affected {result.rowcount} rows")
        
        # CRITICAL FIX: Also update the processing_queue table
        queue_update_query = text("""
            UPDATE processing_queue 
            SET status = :queue_status, 
                completed_at = CURRENT_TIMESTAMP,
                progress_percentage = 100,
                current_step = 'Analysis Complete',
                progress_message = 'PDF analysis completed successfully'
            WHERE document_id = :document_id 
            AND status = 'processing'
        """)
        
        # Map processing status to queue status
        queue_status = "completed" if request.processing_status == "completed" else "failed"
        
        queue_result = db.execute(queue_update_query, {
            "queue_status": queue_status,
            "document_id": request.document_id
        })
        
        logger.info(f"🔍 DEBUG: Processing queue update affected {queue_result.rowcount} rows")
        
        db.commit()
        
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {request.document_id} not found"
            )
        
        logger.info(f"Updated document {request.document_id}: {request.results_file_path} -> {request.processing_status}")
        
        return {
            "success": True,
            "message": f"Updated document {request.document_id} successfully",
            "document_id": request.document_id,
            "results_file_path": request.results_file_path,
            "processing_status": request.processing_status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating deck results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update deck results: {str(e)}"
        )

class ProcessingProgressUpdateRequest(BaseModel):
    document_id: int
    progress_percentage: int
    current_step: str
    progress_message: str
    phase: str  # 'visual_analysis', 'extraction', 'template_analysis'

@router.post("/update-processing-progress")
async def update_processing_progress(
    request: ProcessingProgressUpdateRequest,
    db: Session = Depends(get_db)
):
    """Internal endpoint for GPU to send incremental progress updates during processing"""
    try:
        logger.info(f"📊 Progress update for document {request.document_id}: {request.progress_percentage}% - {request.current_step}")
        
        # Update the processing_queue table with incremental progress
        progress_query = text("""
            UPDATE processing_queue 
            SET progress_percentage = :progress_percentage,
                current_step = :current_step,
                progress_message = :progress_message,
                last_progress_update = CURRENT_TIMESTAMP
            WHERE document_id = :document_id 
            AND status = 'processing'
        """)
        
        result = db.execute(progress_query, {
            "progress_percentage": request.progress_percentage,
            "current_step": request.current_step,
            "progress_message": request.progress_message,
            "document_id": request.document_id
        })
        
        db.commit()
        logger.info(f"📊 Progress update applied to {result.rowcount} queue entries")
        
        if result.rowcount == 0:
            logger.warning(f"📊 No processing queue entry found for document {request.document_id}")
        
        return {
            "success": True,
            "message": f"Progress updated for document {request.document_id}",
            "document_id": request.document_id,
            "progress_percentage": request.progress_percentage,
            "current_step": request.current_step
        }
        
    except Exception as e:
        logger.error(f"Error updating processing progress: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update processing progress: {str(e)}"
        )

class SpecializedAnalysisRequest(BaseModel):
    document_id: int
    specialized_analysis: dict  # e.g. {"clinical_validation": "...", "regulatory_pathway": "...", "scientific_hypothesis": "..."}

@router.post("/save-specialized-analysis")
async def save_specialized_analysis(
    request: SpecializedAnalysisRequest,
    db: Session = Depends(get_db)
):
    """Internal endpoint for GPU to save specialized analysis results"""
    try:
        logger.info(f"💾 Saving specialized analysis for document {request.document_id}")
        
        # First, delete any existing specialized analysis for this document
        delete_query = text("DELETE FROM specialized_analysis_results WHERE document_id = :document_id")
        db.execute(delete_query, {"document_id": request.document_id})
        
        # Save each specialized analysis result
        saved_analyses = []
        for analysis_type, analysis_result in request.specialized_analysis.items():
            if analysis_result and analysis_result.strip():  # Only save non-empty results
                insert_query = text("""
                    INSERT INTO specialized_analysis_results 
                    (document_id, analysis_type, analysis_result, created_at) 
                    VALUES (:document_id, :analysis_type, :analysis_result, NOW())
                """)
                
                db.execute(insert_query, {
                    "document_id": request.document_id,
                    "analysis_type": analysis_type,
                    "analysis_result": analysis_result
                })
                
                saved_analyses.append(analysis_type)
                logger.info(f"✅ Saved {analysis_type} analysis for document {request.document_id}")
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Saved {len(saved_analyses)} specialized analyses for document {request.document_id}",
            "document_id": request.document_id,
            "saved_analyses": saved_analyses
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error saving specialized analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save specialized analysis: {str(e)}"
        )

class ExtractionResultsRequest(BaseModel):
    experiment_name: str
    document_ids: list
    extraction_results: dict  # {document_id: {company_offering, classification, funding_amount, deck_date, company_name}}
    extraction_type: str
    text_model_used: str

@router.post("/save-extraction-results")
async def save_extraction_results(
    request: ExtractionResultsRequest,
    db: Session = Depends(get_db)
):
    """Internal endpoint for GPU to save extraction experiment results"""
    try:
        logger.info(f"💾 Saving extraction results for documents {request.document_ids}")
        
        import json
        
        # Check if there's an existing extraction experiment for these documents
        doc_ids_str = ','.join(map(str, request.document_ids))
        existing_query = text("""
            SELECT id FROM extraction_experiments 
            WHERE document_ids = :document_ids
            ORDER BY created_at DESC
            LIMIT 1
        """)
        existing_result = db.execute(existing_query, {"document_ids": doc_ids_str}).fetchone()
        
        if existing_result:
            # Update existing experiment
            experiment_id = existing_result[0]
            logger.info(f"Updating existing extraction experiment {experiment_id}")
            
            update_query = text("""
                UPDATE extraction_experiments 
                SET results_json = :results_json,
                    extraction_type = :extraction_type,
                    text_model_used = :text_model_used
                WHERE id = :experiment_id
            """)
            
            db.execute(update_query, {
                "results_json": json.dumps(request.extraction_results),
                "extraction_type": request.extraction_type,
                "text_model_used": request.text_model_used,
                "experiment_id": experiment_id
            })
            
        else:
            # Create new extraction experiment
            logger.info(f"Creating new extraction experiment for documents {request.document_ids}")
            
            insert_query = text("""
                INSERT INTO extraction_experiments (
                    experiment_name,
                    document_ids,
                    extraction_type,
                    text_model_used,
                    extraction_prompt,
                    results_json,
                    created_at
                ) VALUES (
                    :experiment_name,
                    :document_ids,
                    :extraction_type,
                    :text_model_used,
                    'Automatic extraction for startup upload',
                    :results_json,
                    NOW()
                )
            """)
            
            db.execute(insert_query, {
                "experiment_name": request.experiment_name,
                "document_ids": doc_ids_str,
                "extraction_type": request.extraction_type,
                "text_model_used": request.text_model_used,
                "results_json": json.dumps(request.extraction_results)
            })
        
        db.commit()
        
        logger.info(f"✅ Successfully saved extraction results for documents {request.document_ids}")
        
        return {
            "success": True,
            "message": f"Extraction results saved for {len(request.document_ids)} documents",
            "document_ids": request.document_ids,
            "experiment_name": request.experiment_name
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error saving extraction results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save extraction results: {str(e)}"
        )

@router.get("/get-extraction-results/{document_id}")
async def get_extraction_results(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Internal endpoint for GPU to fetch extraction results for a specific document"""
    try:
        logger.info(f"🔍 Fetching extraction results for document {document_id}")
        
        # Query extraction_experiments table for this document
        # document_ids is stored as text in format '{9}' so we use string matching
        query = text("""
            SELECT results_json, classification_results_json, company_name_results_json,
                   funding_amount_results_json, deck_date_results_json, template_processing_results_json
            FROM extraction_experiments 
            WHERE document_ids LIKE '%' || :document_id || '%'
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        result = db.execute(query, {"document_id": str(document_id)}).fetchone()
        
        if not result:
            logger.warning(f"⚠️ No extraction results found for document {document_id}")
            return {
                "document_id": document_id,
                "has_results": False,
                "extraction_results": None
            }
        
        # Parse the JSON results
        extraction_data = {}
        
        if result[0]:  # results_json (offering extraction)
            try:
                offering_data = json.loads(result[0])
                extraction_data["offering_extraction"] = offering_data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse offering extraction results for document {document_id}")
        
        if result[1]:  # classification_results_json
            try:
                classification_data = json.loads(result[1])
                extraction_data["classification"] = classification_data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse classification results for document {document_id}")
        
        if result[2]:  # company_name_results_json
            try:
                company_name_data = json.loads(result[2])
                extraction_data["company_name"] = company_name_data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse company name results for document {document_id}")
        
        if result[3]:  # funding_amount_results_json
            try:
                funding_data = json.loads(result[3])
                extraction_data["funding_amount"] = funding_data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse funding amount results for document {document_id}")
        
        if result[4]:  # deck_date_results_json
            try:
                date_data = json.loads(result[4])
                extraction_data["deck_date"] = date_data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse deck date results for document {document_id}")
        
        if result[5]:  # template_processing_results_json
            try:
                template_data = json.loads(result[5])
                extraction_data["template_processing"] = template_data
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse template processing results for document {document_id}")
        
        logger.info(f"✅ Found extraction results for document {document_id} with {len(extraction_data)} data sections")
        
        return {
            "document_id": document_id,
            "has_results": True,
            "extraction_results": extraction_data
        }
        
    except Exception as e:
        logger.error(f"❌ Error fetching extraction results for document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch extraction results: {str(e)}"
        )

class TemplateProcessingRequest(BaseModel):
    experiment_name: str
    document_id: int
    template_processing_results: dict

@router.post("/save-template-processing")
async def save_template_processing(
    request: TemplateProcessingRequest,
    db: Session = Depends(get_db)
):
    """Internal endpoint for GPU to save template processing results for startup uploads"""
    try:
        logger.info(f"💾 Saving template processing results for document {request.document_id}")
        
        import json
        
        # First check if there's an existing extraction experiment for this document
        existing_query = text("""
            SELECT id FROM extraction_experiments 
            WHERE document_ids LIKE '%' || :document_id || '%'
            ORDER BY created_at DESC
            LIMIT 1
        """)
        existing_result = db.execute(existing_query, {"document_id": str(request.document_id)}).fetchone()
        
        if existing_result:
            # Update existing experiment with template processing results
            experiment_id = existing_result[0]
            logger.info(f"Updating existing extraction experiment {experiment_id} with template processing")
            
            update_query = text("""
                UPDATE extraction_experiments 
                SET template_processing_results_json = :template_results,
                    template_processing_completed_at = NOW()
                WHERE id = :experiment_id
            """)
            
            db.execute(update_query, {
                "template_results": json.dumps(request.template_processing_results),
                "experiment_id": experiment_id
            })
            
        else:
            # Create new extraction experiment entry
            logger.info(f"Creating new extraction experiment for document {request.document_id}")
            
            insert_query = text("""
                INSERT INTO extraction_experiments (
                    experiment_name, 
                    document_ids, 
                    extraction_type,
                    text_model_used,
                    extraction_prompt,
                    results_json,
                    template_processing_results_json,
                    template_processing_completed_at,
                    created_at
                ) VALUES (
                    :experiment_name,
                    :document_ids,
                    'startup_upload',
                    'auto',
                    'Automatic startup upload processing',
                    '{}',
                    :template_results,
                    NOW(),
                    NOW()
                )
            """)
            
            db.execute(insert_query, {
                "experiment_name": request.experiment_name,
                "document_ids": f"{request.document_id}",  # Simple text format
                "template_results": json.dumps(request.template_processing_results)
            })
        
        db.commit()
        
        logger.info(f"✅ Successfully saved template processing results for document {request.document_id}")
        
        return {
            "success": True,
            "message": f"Template processing results saved for document {request.document_id}",
            "document_id": request.document_id,
            "experiment_name": request.experiment_name
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error saving template processing results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save template processing results: {str(e)}"
        )

# Queue System Integration Endpoints

class ProcessingServerRegistration(BaseModel):
    server_id: str
    server_type: str  # 'gpu', 'cpu', etc.
    capabilities: Dict[str, Any]
    max_concurrent_tasks: int = 3

class ServerHeartbeat(BaseModel):
    server_id: str

class GetNextTaskRequest(BaseModel):
    server_id: str
    capabilities: Dict[str, Any]

class TaskStatusUpdate(BaseModel):
    task_id: int
    status: str  # 'queued', 'processing', 'completed', 'failed'
    message: str
    server_id: str

class ServerUnregistration(BaseModel):
    server_id: str

@router.post("/register-processing-server")
async def register_processing_server(
    registration: ProcessingServerRegistration,
    db: Session = Depends(get_db)
):
    """Register a processing server (GPU/CPU) with the queue system"""
    try:
        logger.info(f"🟢 Registering processing server: {registration.server_id} ({registration.server_type})")
        
        # Insert or update server registration
        query = text("""
            INSERT INTO processing_servers (
                id, server_type, status, capabilities, max_concurrent_tasks, 
                current_load, created_at, updated_at, last_heartbeat
            ) VALUES (
                :server_id, :server_type, 'active', :capabilities, :max_concurrent_tasks,
                0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            ON CONFLICT (id) DO UPDATE SET
                server_type = :server_type,
                status = 'active',
                capabilities = :capabilities,
                max_concurrent_tasks = :max_concurrent_tasks,
                updated_at = CURRENT_TIMESTAMP,
                last_heartbeat = CURRENT_TIMESTAMP
        """)
        
        db.execute(query, {
            "server_id": registration.server_id,
            "server_type": registration.server_type,
            "capabilities": json.dumps(registration.capabilities),
            "max_concurrent_tasks": registration.max_concurrent_tasks
        })
        
        db.commit()
        
        logger.info(f"✅ Successfully registered processing server {registration.server_id}")
        
        return {
            "success": True,
            "message": f"Server {registration.server_id} registered successfully",
            "server_id": registration.server_id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error registering processing server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register processing server: {str(e)}"
        )

@router.post("/server-heartbeat")
async def server_heartbeat(
    heartbeat: ServerHeartbeat,
    db: Session = Depends(get_db)
):
    """Update server heartbeat to maintain registration"""
    try:
        query = text("""
            UPDATE processing_servers 
            SET last_heartbeat = CURRENT_TIMESTAMP, status = 'active'
            WHERE id = :server_id
        """)
        
        result = db.execute(query, {"server_id": heartbeat.server_id})
        db.commit()
        
        if result.rowcount == 0:
            logger.warning(f"⚠️ Heartbeat for unknown server: {heartbeat.server_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Server {heartbeat.server_id} not found - please re-register"
            )
        
        logger.debug(f"💓 Heartbeat received from server {heartbeat.server_id}")
        
        return {
            "success": True,
            "message": "Heartbeat recorded",
            "server_id": heartbeat.server_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error processing heartbeat: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process heartbeat: {str(e)}"
        )

@router.post("/get-next-queue-task")
async def get_next_queue_task(
    request: GetNextTaskRequest,
    db: Session = Depends(get_db)
):
    """Get the next available task from the processing queue"""
    try:
        logger.debug(f"🔍 Server {request.server_id} polling for queue tasks")
        
        # Use the existing get_next_processing_task function from the queue system
        query = text("""
            SELECT * FROM get_next_processing_task(
                :server_id, 
                :capabilities
            )
        """)
        
        result = db.execute(query, {
            "server_id": request.server_id,
            "capabilities": json.dumps(request.capabilities)
        })
        
        task = result.fetchone()
        
        if task:
            logger.info(f"📋 Assigned task {task[0]} to server {request.server_id}")
            
            # Handle processing_options - could be dict, string, or None
            processing_options = task[5]
            if processing_options is None:
                processing_options = {}
            elif isinstance(processing_options, str):
                try:
                    processing_options = json.loads(processing_options)
                except json.JSONDecodeError:
                    processing_options = {}
            elif isinstance(processing_options, dict):
                # Already a dict, use as-is
                pass
            else:
                # Unknown type, default to empty dict
                processing_options = {}
            
            return {
                "task_id": task[0],
                "document_id": task[1], 
                "task_type": task[2],
                "file_path": task[3],
                "company_id": task[4],
                "processing_options": processing_options
            }
        else:
            # No tasks available
            return {}
            
    except Exception as e:
        logger.error(f"❌ Error getting next queue task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get next queue task: {str(e)}"
        )

@router.post("/update-task-status")
async def update_task_status(
    update: TaskStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update the status of a processing queue task"""
    try:
        logger.info(f"📊 Updating task {update.task_id} status to {update.status}")
        
        # Update main task status with processing duration calculation
        update_query = text("""
            UPDATE processing_queue 
            SET status = :status,
                progress_message = :message,
                completed_at = CASE WHEN :status IN ('completed', 'failed') THEN CURRENT_TIMESTAMP ELSE completed_at END,
                processing_duration_seconds = CASE 
                    WHEN :status IN ('completed', 'failed') AND started_at IS NOT NULL 
                    THEN EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - started_at))::integer
                    ELSE processing_duration_seconds 
                END,
                last_progress_update = CURRENT_TIMESTAMP
            WHERE id = :task_id
        """)
        
        db.execute(update_query, {
            "task_id": update.task_id,
            "status": update.status,
            "message": update.message
        })
        
        # Add progress entry
        progress_query = text("""
            INSERT INTO processing_progress (processing_queue_id, step_name, step_status, message, created_at)
            VALUES (:task_id, :step_name, :step_status, :message, CURRENT_TIMESTAMP)
        """)
        
        db.execute(progress_query, {
            "task_id": update.task_id,
            "step_name": update.status.title() + " Status",
            "step_status": "completed" if update.status in ['completed', 'failed'] else "started",
            "message": update.message
        })
        
        db.commit()
        
        logger.info(f"✅ Updated task {update.task_id} status to {update.status}")
        
        return {
            "success": True,
            "message": f"Task {update.task_id} status updated to {update.status}",
            "task_id": update.task_id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error updating task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update task status: {str(e)}"
        )

@router.post("/unregister-processing-server")
async def unregister_processing_server(
    unregistration: ServerUnregistration,
    db: Session = Depends(get_db)
):
    """Unregister a processing server from the queue system"""
    try:
        logger.info(f"🔴 Unregistering processing server: {unregistration.server_id}")
        
        # Update server status to inactive instead of deleting
        query = text("""
            UPDATE processing_servers 
            SET status = 'inactive', updated_at = CURRENT_TIMESTAMP
            WHERE id = :server_id
        """)
        
        result = db.execute(query, {"server_id": unregistration.server_id})
        db.commit()
        
        if result.rowcount > 0:
            logger.info(f"✅ Successfully unregistered server {unregistration.server_id}")
        else:
            logger.warning(f"⚠️ Server {unregistration.server_id} was not found")
        
        return {
            "success": True,
            "message": f"Server {unregistration.server_id} unregistered successfully",
            "server_id": unregistration.server_id
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error unregistering processing server: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unregister processing server: {str(e)}"
        )

class CompleteTaskAndCreateSpecialized(BaseModel):
    task_id: int
    document_id: int
    success: bool
    results_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

@router.get("/check-document-exists/{document_id}")
async def check_document_exists(
    document_id: int,
    db: Session = Depends(get_db)
):
    """Check if a document still exists (not deleted)"""
    try:
        query = text("""
            SELECT COUNT(*) > 0 as exists
            FROM project_documents
            WHERE id = :document_id
        """)
        
        result = db.execute(query, {"document_id": document_id}).fetchone()
        exists = result[0] if result else False
        
        return {
            "document_id": document_id,
            "exists": exists
        }
        
    except Exception as e:
        logger.error(f"Error checking document existence: {e}")
        # On error, return true to avoid false aborts
        return {
            "document_id": document_id,
            "exists": True,
            "error": str(e)
        }

@router.post("/complete-task-and-create-specialized")
async def complete_task_and_create_specialized(
    completion: CompleteTaskAndCreateSpecialized,
    db: Session = Depends(get_db)
):
    """Complete main task and automatically create specialized analysis tasks"""
    try:
        logger.info(f"🎯 Completing main task {completion.task_id} and creating specialized analysis for document {completion.document_id}")
        
        # Use the processing queue manager to complete task and create specialized tasks
        success = processing_queue_manager.complete_task_and_create_specialized(
            task_id=completion.task_id,
            document_id=completion.document_id,
            success=completion.success,
            results_path=completion.results_path,
            metadata=completion.metadata,
            db=db
        )
        
        if success:
            logger.info(f"✅ Successfully completed main task and created specialized analysis tasks for document {completion.document_id}")
            return {
                "success": True,
                "message": f"Main task completed and specialized analysis tasks created for document {completion.document_id}",
                "task_id": completion.task_id,
                "document_id": completion.document_id
            }
        else:
            logger.error(f"❌ Failed to complete task and create specialized analysis for document {completion.document_id}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to complete task and create specialized analysis"
            )
        
    except Exception as e:
        logger.error(f"❌ Error in complete_task_and_create_specialized: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete task and create specialized analysis: {str(e)}"
        )

@router.post("/save-extraction-template-results")
async def save_extraction_template_results(
    request: ExtractionTemplateResultsRequest,
    db: Session = Depends(get_db)
):
    """Save extraction and template analysis results from GPU processing"""
    try:
        logger.info(f"💾 Saving extraction and template results for document {request.document_id}")
        
        # Save chapter analysis results if present
        if request.chapter_analysis:
            for chapter_id, chapter_data in request.chapter_analysis.items():
                try:
                    insert_query = text("""
                        INSERT INTO chapter_analysis_results 
                        (document_id, chapter_id, analysis_results_json, created_at)
                        VALUES (:document_id, :chapter_id, :analysis_json, NOW())
                        ON CONFLICT (document_id, chapter_id) 
                        DO UPDATE SET 
                            analysis_results_json = EXCLUDED.analysis_results_json,
                            created_at = EXCLUDED.created_at
                    """)
                    
                    db.execute(insert_query, {
                        "document_id": request.document_id,
                        "chapter_id": int(chapter_id) if chapter_id.isdigit() else 0,
                        "analysis_json": json.dumps(chapter_data)
                    })
                except Exception as e:
                    logger.warning(f"Failed to save chapter {chapter_id}: {e}")
        
        # Save question analysis results if present
        if request.question_analysis:
            for question_key, question_data in request.question_analysis.items():
                try:
                    # Extract question_id from the key (format: "chapterX_questionY")
                    parts = question_key.split('_')
                    if len(parts) >= 2 and parts[-1].startswith('question'):
                        question_id = int(parts[-1].replace('question', ''))
                    else:
                        question_id = 0
                    
                    insert_query = text("""
                        INSERT INTO question_analysis_results 
                        (document_id, question_id, analysis_results_json, created_at)
                        VALUES (:document_id, :question_id, :analysis_json, NOW())
                        ON CONFLICT (document_id, question_id) 
                        DO UPDATE SET 
                            analysis_results_json = EXCLUDED.analysis_results_json,
                            created_at = EXCLUDED.created_at
                    """)
                    
                    db.execute(insert_query, {
                        "document_id": request.document_id,
                        "question_id": question_id,
                        "analysis_json": json.dumps(question_data)
                    })
                except Exception as e:
                    logger.warning(f"Failed to save question {question_key}: {e}")
        
        # Save extraction results (offering, classification, name, funding, date) to extraction_experiments
        # This maintains compatibility with dojo's expected format
        extraction_data = {
            "experiment_name": f"document_{request.document_id}_extraction",
            "document_ids": str([request.document_id]),
            "extraction_type": "healthcare_template",
            "text_model_used": request.processing_metadata.get("model_versions", {}).get("text_model", "unknown") if request.processing_metadata else "unknown",
            "extraction_prompt": "Healthcare template extraction",
            "results_json": json.dumps({
                str(request.document_id): {
                    "company_offering": request.company_offering,
                    "extraction_timestamp": datetime.now().isoformat()
                }
            }),
            "classification_results_json": json.dumps({
                str(request.document_id): request.classification
            }) if request.classification else None,
            "company_name_results_json": json.dumps({
                str(request.document_id): {"company_name": request.startup_name}
            }) if request.startup_name else None,
            "funding_amount_results_json": json.dumps({
                str(request.document_id): {"funding_amount": request.funding_amount}
            }) if request.funding_amount else None,
            "deck_date_results_json": json.dumps({
                str(request.document_id): {"deck_date": request.deck_date}
            }) if request.deck_date else None,
            "template_processing_results_json": json.dumps({
                str(request.document_id): {
                    "template_used": request.template_used,
                    "overall_score": request.overall_score,
                    "chapter_count": len(request.chapter_analysis) if request.chapter_analysis else 0,
                    "question_count": len(request.question_analysis) if request.question_analysis else 0
                }
            })
        }
        
        # Insert or update extraction_experiments
        insert_extraction_query = text("""
            INSERT INTO extraction_experiments 
            (experiment_name, document_ids, extraction_type, text_model_used, extraction_prompt, 
             results_json, classification_results_json, company_name_results_json,
             funding_amount_results_json, deck_date_results_json, template_processing_results_json,
             created_at, classification_enabled)
            VALUES (:experiment_name, :document_ids, :extraction_type, :text_model_used, :extraction_prompt,
                    :results_json, :classification_results_json, :company_name_results_json,
                    :funding_amount_results_json, :deck_date_results_json, :template_processing_results_json,
                    NOW(), true)
        """)
        
        db.execute(insert_extraction_query, extraction_data)
        
        db.commit()
        
        logger.info(f"✅ Successfully saved extraction and template results for document {request.document_id}")
        
        return {
            "success": True,
            "message": f"Extraction and template results saved for document {request.document_id}",
            "document_id": request.document_id,
            "chapters_saved": len(request.chapter_analysis) if request.chapter_analysis else 0,
            "questions_saved": len(request.question_analysis) if request.question_analysis else 0
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error saving extraction and template results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save extraction and template results: {str(e)}"
        )