"""
Internal API endpoints for GPU processing communication
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
import logging

from ..db.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])

class DeckResultsUpdateRequest(BaseModel):
    document_id: int
    results_file_path: str
    processing_status: str

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
            SET results_file_path = :results_file_path, processing_status = :processing_status
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
                results_file_path = :results_file_path,
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
            "results_file_path": request.results_file_path,
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
                progress_message = :progress_message
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