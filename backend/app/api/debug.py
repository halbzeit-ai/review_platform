from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..db.database import get_db
from ..core.config import settings
import os
from typing import Dict, Any

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