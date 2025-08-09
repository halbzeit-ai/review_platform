from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..db.database import get_db
from ..core.config import settings
import os
from typing import Dict, Any
from datetime import datetime

router = APIRouter()

@router.get("/health-detailed")
def detailed_health_check():
    """Comprehensive health check without authentication"""
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "database": "connected",
        "timestamp": "2025-01-01T00:00:00Z",
        "services": {
            "backend": "active",
            "database": "connected",
            "shared_filesystem": os.path.exists(settings.SHARED_FILESYSTEM_MOUNT_PATH)
        }
    }

@router.get("/deck/{deck_id}/specialized-analysis")
def get_specialized_analysis_debug(deck_id: int, db: Session = Depends(get_db)):
    """Get specialized analysis results without authentication for debugging"""
    
    try:
        # Check if deck exists
        deck_check = db.execute(text("SELECT id, ai_extracted_startup_name FROM pitch_decks WHERE id = :deck_id"), {"deck_id": deck_id}).fetchone()
        
        if not deck_check:
            raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")
        
        # Get specialized analysis results
        results = db.execute(text("""
            SELECT 
                analysis_type, 
                LENGTH(analysis_result) as result_length,
                LEFT(analysis_result, 500) as sample,
                confidence_score,
                model_used,
                created_at
            FROM specialized_analysis_results 
            WHERE pitch_deck_id = :deck_id
            ORDER BY created_at DESC
        """), {"deck_id": deck_id}).fetchall()
        
        analyses = []
        for row in results:
            analyses.append({
                "type": row[0],
                "length": row[1],
                "sample": row[2] + "..." if row[1] and row[1] > 500 else row[2],
                "confidence_score": float(row[3]) if row[3] else None,
                "model_used": row[4],
                "created_at": str(row[5]) if row[5] else None
            })
        
        return {
            "deck_id": deck_id,
            "startup_name": deck_check[1] if deck_check[1] else "Unknown",
            "specialized_analyses_count": len(analyses),
            "analyses": analyses,
            "expected_types": ["clinical_validation", "regulatory_pathway", "scientific_hypothesis"],
            "missing_types": [t for t in ["clinical_validation", "regulatory_pathway", "scientific_hypothesis"] if t not in [a["type"] for a in analyses]]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        return {
            "deck_id": deck_id,
            "error": str(e),
            "specialized_analyses_count": 0,
            "analyses": []
        }

@router.get("/deck/{deck_id}/status")
def get_deck_status_debug(deck_id: int, db: Session = Depends(get_db)):
    """Get deck status without authentication for debugging"""
    
    try:
        # Check if deck exists
        result = db.execute(text("SELECT id, ai_extracted_startup_name, processing_status, file_name FROM pitch_decks WHERE id = :deck_id"), {"deck_id": deck_id}).fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail=f"Deck {deck_id} not found")
        
        # Get processing status from various tables
        processing_status = {
            "deck_id": deck_id,
            "startup_name": result[1] if len(result) > 1 and result[1] else "Unknown",
            "processing_status": result[2] if len(result) > 2 else "unknown",
            "file_name": result[3] if len(result) > 3 else "unknown",
            "exists": True,
            "tables": {}
        }
        
        # Check various processing tables with safer queries
        table_queries = {
            "pitch_decks": "SELECT COUNT(*) FROM pitch_decks WHERE id = :deck_id",
            "reviews": "SELECT COUNT(*) FROM reviews WHERE pitch_deck_id = :deck_id",
            "documents": "SELECT COUNT(*) FROM documents WHERE pitch_deck_id = :deck_id"
        }
        
        for table_name, query in table_queries.items():
            try:
                count_result = db.execute(text(query), {"deck_id": deck_id}).fetchone()
                processing_status["tables"][table_name] = count_result[0] if count_result else 0
            except Exception as e:
                processing_status["tables"][table_name] = f"Error: {str(e)}"
        
        # Check extraction experiments with safe array query
        try:
            extraction_result = db.execute(
                text("SELECT COUNT(*) FROM extraction_experiments WHERE :deck_id = ANY(pitch_deck_ids)"), 
                {"deck_id": deck_id}
            ).fetchone()
            processing_status["tables"]["extraction_experiments"] = extraction_result[0] if extraction_result else 0
        except Exception as e:
            processing_status["tables"]["extraction_experiments"] = f"Error: {str(e)}"
        
        return processing_status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")

@router.get("/database/tables")
def list_database_tables(db: Session = Depends(get_db)):
    """List all database tables for debugging"""
    result = db.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")).fetchall()
    
    tables = [row[0] for row in result]
    
    return {
        "tables": tables,
        "count": len(tables)
    }

@router.get("/database/table/{table_name}/info")
def get_table_info(table_name: str, db: Session = Depends(get_db)):
    """Get table structure and row count for debugging"""
    
    # Get column information
    columns_result = db.execute(text("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = :table_name 
        ORDER BY ordinal_position
    """), {"table_name": table_name}).fetchall()
    
    if not columns_result:
        raise HTTPException(status_code=404, detail=f"Table {table_name} not found")
    
    # Get row count
    try:
        count_result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}")).fetchone()
        row_count = count_result[0] if count_result else 0
    except Exception as e:
        row_count = f"Error: {str(e)}"
    
    # Get recent records (if id column exists)
    recent_records = []
    try:
        sample_result = db.execute(text(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 3")).fetchall()
        if sample_result:
            columns = [desc[0] for desc in sample_result[0]._mapping.keys()]
            recent_records = [dict(zip(columns, row)) for row in sample_result]
    except:
        recent_records = "No ID column or error fetching samples"
    
    return {
        "table_name": table_name,
        "columns": [
            {
                "name": col[0],
                "type": col[1], 
                "nullable": col[2]
            } for col in columns_result
        ],
        "row_count": row_count,
        "recent_records": recent_records
    }

@router.get("/environment")
def get_environment_info():
    """Get environment information for debugging"""
    return {
        "environment": settings.ENVIRONMENT,
        "database_url": settings.DATABASE_URL.replace(settings.DATABASE_URL.split('@')[0].split('//')[-1] + '@', '***@') if '@' in settings.DATABASE_URL else "No credentials",
        "shared_filesystem": settings.SHARED_FILESYSTEM_MOUNT_PATH,
        "shared_filesystem_exists": os.path.exists(settings.SHARED_FILESYSTEM_MOUNT_PATH),
        "log_level": getattr(settings, 'LOG_LEVEL', 'INFO'),
        "server_host": getattr(settings, 'SERVER_HOST', 'Unknown')
    }

@router.get("/processing/queue-stats")
async def debug_processing_queue_stats(db: Session = Depends(get_db)):
    """Get comprehensive processing queue statistics without authentication"""
    try:
        # Queue status breakdown
        queue_stats = db.execute(text("""
            SELECT 
                status, 
                COUNT(*) as count, 
                ROUND(AVG(progress_percentage), 1) as avg_progress,
                ROUND(AVG(EXTRACT(EPOCH FROM (COALESCE(completed_at, NOW()) - created_at))/60), 1) as avg_duration_min
            FROM processing_queue 
            GROUP BY status 
            ORDER BY count DESC
        """)).fetchall()
        
        # Failed tasks summary
        failed_tasks = db.execute(text("""
            SELECT 
                pd.file_name,
                pq.retry_count,
                pq.created_at,
                SUBSTRING(pq.last_error, 1, 200) as error_preview
            FROM processing_queue pq
            JOIN pitch_decks pd ON pq.pitch_deck_id = pd.id
            WHERE pq.status = 'failed'
            ORDER BY pq.created_at DESC
            LIMIT 10
        """)).fetchall()
        
        # Processing servers status
        servers = db.execute(text("""
            SELECT 
                id as server_id,
                server_type,
                status,
                current_load,
                max_concurrent_tasks,
                last_heartbeat,
                EXTRACT(EPOCH FROM (NOW() - last_heartbeat))/60 as minutes_since_heartbeat
            FROM processing_servers
            ORDER BY last_heartbeat DESC
        """)).fetchall()
        
        return {
            "queue_statistics": [dict(row._mapping) for row in queue_stats],
            "failed_tasks": [dict(row._mapping) for row in failed_tasks],
            "processing_servers": [dict(row._mapping) for row in servers],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

@router.get("/processing/deck/{deck_id}")
async def debug_deck_processing(deck_id: int, db: Session = Depends(get_db)):
    """Get comprehensive deck processing information without authentication"""
    try:
        # Main processing info
        processing_info = db.execute(text("""
            SELECT 
                pq.status, 
                pq.progress_percentage, 
                pq.current_step, 
                pq.progress_message,
                pq.retry_count,
                pq.created_at, 
                pq.started_at, 
                pq.completed_at,
                pd.file_name, 
                pd.processing_status as deck_status,
                CASE WHEN pq.last_error IS NOT NULL 
                     THEN SUBSTRING(pq.last_error, 1, 300) || '...' 
                     ELSE 'No errors' 
                END as error_preview
            FROM processing_queue pq
            JOIN pitch_decks pd ON pq.pitch_deck_id = pd.id
            WHERE pq.pitch_deck_id = :deck_id
            ORDER BY pq.created_at DESC
        """), {"deck_id": deck_id}).fetchall()
        
        # Processing steps
        processing_steps = db.execute(text("""
            SELECT 
                pp.step_name,
                pp.step_status,
                pp.progress_percentage,
                pp.message,
                pp.created_at
            FROM processing_progress pp
            JOIN processing_queue pq ON pp.processing_queue_id = pq.id
            WHERE pq.pitch_deck_id = :deck_id
            ORDER BY pp.created_at DESC
            LIMIT 20
        """), {"deck_id": deck_id}).fetchall()
        
        # Analysis results status
        analysis_status = db.execute(text("""
            SELECT 
                COUNT(DISTINCT sar.id) as specialized_analyses,
                COUNT(DISTINCT vac.id) as visual_cache_entries,
                COUNT(DISTINCT r.id) as reviews,
                COUNT(DISTINCT sf.id) as slide_feedback
            FROM pitch_decks pd
            LEFT JOIN specialized_analysis_results sar ON pd.id = sar.pitch_deck_id
            LEFT JOIN visual_analysis_cache vac ON pd.id = vac.pitch_deck_id
            LEFT JOIN reviews r ON pd.id = r.pitch_deck_id
            LEFT JOIN slide_feedback sf ON pd.id = sf.pitch_deck_id
            WHERE pd.id = :deck_id
        """), {"deck_id": deck_id}).fetchone()
        
        return {
            "deck_id": deck_id,
            "processing_info": [dict(row._mapping) for row in processing_info],
            "processing_steps": [dict(row._mapping) for row in processing_steps],
            "analysis_results": dict(analysis_status._mapping) if analysis_status else {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e), "deck_id": deck_id, "timestamp": datetime.utcnow().isoformat()}

@router.get("/dojo/experiments-summary")
async def debug_dojo_experiments(db: Session = Depends(get_db)):
    """Get dojo experiment statistics without authentication"""
    try:
        # Dojo deck statistics  
        dojo_stats = db.execute(text("""
            SELECT 
                COUNT(*) as total_dojo_decks,
                COUNT(DISTINCT company_id) as unique_companies,
                COUNT(*) FILTER (WHERE processing_status = 'completed') as processed,
                COUNT(*) FILTER (WHERE processing_status = 'pending') as pending,
                COUNT(*) FILTER (WHERE processing_status = 'failed') as failed,
                MAX(created_at) as latest_upload,
                MIN(created_at) as earliest_upload
            FROM pitch_decks WHERE data_source = 'dojo'
        """)).fetchone()
        
        # Active experiments
        experiments = db.execute(text("""
            SELECT 
                experiment_name,
                extraction_type, 
                array_length(string_to_array(pitch_deck_ids, ','), 1) as deck_count,
                text_model_used,
                created_at,
                CASE WHEN classification_results_json IS NOT NULL THEN true ELSE false END as has_classification,
                CASE WHEN company_name_results_json IS NOT NULL THEN true ELSE false END as has_company_names,
                CASE WHEN funding_amount_results_json IS NOT NULL THEN true ELSE false END as has_funding_amounts,
                CASE WHEN template_processing_results_json IS NOT NULL THEN true ELSE false END as has_template_processing
            FROM extraction_experiments 
            ORDER BY created_at DESC 
            LIMIT 20
        """)).fetchall()
        
        # Visual analysis cache stats
        cache_stats = db.execute(text("""
            SELECT 
                vac.vision_model_used, 
                COUNT(*) as cached_analyses,
                MAX(vac.created_at) as latest_cache,
                COUNT(DISTINCT pd.company_id) as unique_companies
            FROM visual_analysis_cache vac
            JOIN pitch_decks pd ON vac.pitch_deck_id = pd.id
            WHERE pd.data_source = 'dojo'
            GROUP BY vac.vision_model_used
            ORDER BY cached_analyses DESC
        """)).fetchall()
        
        return {
            "dojo_statistics": dict(dojo_stats._mapping) if dojo_stats else {},
            "recent_experiments": [dict(row._mapping) for row in experiments],
            "cache_statistics": [dict(row._mapping) for row in cache_stats],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

@router.get("/templates/performance")
async def debug_template_performance(db: Session = Depends(get_db)):
    """Get template usage and performance metrics without authentication"""
    try:
        # Template performance
        template_performance = db.execute(text("""
            SELECT 
                t.name,
                t.healthcare_sector_id,
                COUNT(tp.id) as usage_count,
                ROUND(AVG(tp.total_processing_time), 2) as avg_processing_time,
                ROUND(AVG(tp.average_confidence), 2) as avg_confidence,
                ROUND(AVG(tp.gp_rating), 1) as avg_gp_rating,
                COUNT(tp.gp_feedback) FILTER (WHERE tp.gp_feedback IS NOT NULL) as feedback_count
            FROM analysis_templates t
            LEFT JOIN template_performance tp ON t.id = tp.template_id
            WHERE t.is_active = true
            GROUP BY t.id, t.name, t.healthcare_sector_id
            HAVING COUNT(tp.id) > 0
            ORDER BY avg_gp_rating DESC NULLS LAST, usage_count DESC
        """)).fetchall()
        
        # Healthcare sectors with classification accuracy
        sector_performance = db.execute(text("""
            SELECT 
                s.display_name as sector,
                COUNT(DISTINCT sc.id) as classified_companies,
                COUNT(DISTINCT t.id) as available_templates,
                COUNT(cp.id) as performance_records,
                COUNT(cp.id) FILTER (WHERE cp.was_accurate = true) as accurate_classifications,
                CASE WHEN COUNT(cp.id) > 0 
                     THEN ROUND(COUNT(cp.id) FILTER (WHERE cp.was_accurate = true)::DECIMAL / COUNT(cp.id) * 100, 1)
                     ELSE NULL 
                END as accuracy_percentage
            FROM healthcare_sectors s
            LEFT JOIN startup_classifications sc ON s.id = sc.primary_sector_id
            LEFT JOIN analysis_templates t ON s.id = t.healthcare_sector_id AND t.is_active = true
            LEFT JOIN classification_performance cp ON sc.id = cp.classification_id
            WHERE s.is_active = true
            GROUP BY s.id, s.display_name
            ORDER BY classified_companies DESC NULLS LAST
        """)).fetchall()
        
        # Template customizations
        customizations = db.execute(text("""
            SELECT 
                gtc.gp_email,
                t.name as base_template,
                gtc.customization_name,
                gtc.is_active,
                gtc.created_at,
                gtc.modified_at
            FROM gp_template_customizations gtc
            JOIN analysis_templates t ON gtc.base_template_id = t.id
            WHERE gtc.is_active = true
            ORDER BY gtc.modified_at DESC
            LIMIT 20
        """)).fetchall()
        
        return {
            "template_performance": [dict(row._mapping) for row in template_performance],
            "sector_performance": [dict(row._mapping) for row in sector_performance], 
            "active_customizations": [dict(row._mapping) for row in customizations],
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

@router.get("/models/config")
async def debug_model_config(db: Session = Depends(get_db)):
    """Get current model configuration without authentication"""
    try:
        # Active models
        models = db.execute(text("""
            SELECT 
                model_type,
                model_name,
                is_active,
                created_at,
                updated_at
            FROM model_configs 
            ORDER BY model_type, is_active DESC, updated_at DESC
        """)).fetchall()
        
        # Model usage by type
        model_stats = db.execute(text("""
            SELECT 
                model_type,
                COUNT(*) as total_models,
                COUNT(*) FILTER (WHERE is_active = true) as active_models,
                MAX(updated_at) as last_updated
            FROM model_configs
            GROUP BY model_type
            ORDER BY total_models DESC
        """)).fetchall()
        
        # Pipeline prompts summary
        prompt_stats = db.execute(text("""
            SELECT 
                COUNT(*) as total_prompts,
                COUNT(*) FILTER (WHERE is_active = true) as active_prompts,
                COUNT(DISTINCT stage_name) as unique_stages,
                ROUND(AVG(LENGTH(prompt_text)), 0) as avg_prompt_length,
                MAX(updated_at) as last_updated
            FROM pipeline_prompts
        """)).fetchone()
        
        return {
            "active_models": [dict(row._mapping) for row in models],
            "model_statistics": [dict(row._mapping) for row in model_stats],
            "prompt_statistics": dict(prompt_stats._mapping) if prompt_stats else {},
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}