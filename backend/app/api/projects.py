"""
Project-based API Endpoints
Handles project dashboard, deck viewer, results, and uploads
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json
import os
import logging
import shutil
import io
import re
from pathlib import Path

from ..db.database import get_db
from ..db.models import User, Project, ProjectMember
from .auth import get_current_user
from ..core.config import settings
from ..core.access_control import check_project_access_by_company_id, check_project_access

logger = logging.getLogger(__name__)

def parse_chapter_scores_from_text(template_analysis: str) -> Dict[str, float]:
    """Parse chapter scores from template_analysis text containing embedded scores like **Chapter Score: 4.5/7**"""
    chapter_scores = {}
    
    # Map chapter titles to keys the frontend expects
    chapter_mapping = {
        "Problem Analysis": "problem_analysis", 
        "Solution Approach": "solution_approach",
        "Product Market Fit": "product_market_fit",
        "Monetization": "monetization",
        "Financials": "financials", 
        "Use of Funds": "use_of_funds",
        "Organization": "organization"
    }
    
    # Split by chapters (##)
    chapters = re.split(r'##\s+', template_analysis)
    
    for chapter in chapters:
        if not chapter.strip():
            continue
            
        # Extract chapter name (first line)
        lines = chapter.split('\n')
        chapter_name = lines[0].strip() if lines else ""
        
        # Look for chapter score pattern: **Chapter Score: X.X/7**
        chapter_score_match = re.search(r'\*\*Chapter Score:\s*(\d+(?:\.\d+)?)/7\*\*', chapter)
        if chapter_score_match and chapter_name in chapter_mapping:
            score = float(chapter_score_match.group(1))
            key = chapter_mapping[chapter_name]
            chapter_scores[key] = score
            logger.debug(f"Parsed chapter score: {chapter_name} -> {key} = {score}")
    
    return chapter_scores

router = APIRouter(prefix="/projects", tags=["projects"])

# Pydantic models for API requests/responses
class SlideAnalysisResponse(BaseModel):
    page_number: int
    slide_image_path: str
    description: str
    deck_name: str

class DeckAnalysisResponse(BaseModel):
    deck_id: int
    deck_name: str
    company_id: str
    total_slides: int
    slides: List[SlideAnalysisResponse]
    processing_metadata: Dict[str, Any]

class ProjectUpload(BaseModel):
    id: int
    filename: str
    file_path: str
    file_size: int
    upload_date: datetime
    file_type: str
    pages: Optional[int] = None
    processing_status: str = "pending"
    visual_analysis_completed: bool = False

class ProjectUploadsResponse(BaseModel):
    company_id: str
    uploads: List[ProjectUpload]

def get_company_id_from_user(user: User) -> str:
    """Extract company_id from user based on company name"""
    if user.company_name:
        # Convert company name to a URL-safe slug - same logic as frontend
        import re
        # Replace all whitespace with dashes, then remove non-alphanumeric chars except dashes
        return re.sub(r'[^a-z0-9-]', '', re.sub(r'\s+', '-', user.company_name.lower()))
    # Fallback to email prefix if company name is not available
    return user.email.split('@')[0]

# Legacy function removed - now using unified access control from core.access_control

@router.get("/{project_id}/deck-analysis/{deck_id}", response_model=DeckAnalysisResponse)
async def get_deck_analysis(
    project_id: int,
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get slide-by-slide analysis for a specific deck"""
    try:
        logger.info(f"Getting deck analysis for project_id={project_id}, deck_id={deck_id}, user={current_user.email}")
        
        # Check access permissions using unified access control
        if not check_project_access(current_user, project_id, db):
            logger.warning(f"Access denied for user {current_user.email} to project {project_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get deck information - project-based approach (simplified)
        project_deck_query = text("""
        SELECT pd.id, pd.file_path, p.company_id, u.email, u.company_name, pd.analysis_results_path
        FROM project_documents pd
        JOIN projects p ON pd.project_id = p.id
        LEFT JOIN users u ON pd.uploaded_by = u.id
        WHERE pd.project_id = :project_id AND pd.id = :deck_id 
        AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
        """)
        
        deck_result = db.execute(project_deck_query, {"project_id": project_id, "deck_id": deck_id}).fetchone()
        
        if not deck_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deck {deck_id} not found"
            )
        
        deck_id_db, file_path, company_id, user_email, company_name, results_file_path = deck_result
        
        # Access already verified by check_project_access() - no additional validation needed
        logger.info(f"Project-based deck {deck_id} access granted for user {current_user.email}")
        
        # Since we're querying project_documents, set source table
        source_table = 'project_documents'
        
        # Load analysis results - check multiple locations
        analysis_found = False
        results_data = None
        
        # First try the database results_file_path if available
        if results_file_path:
            if results_file_path.startswith('/'):
                results_full_path = results_file_path
            else:
                results_full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, results_file_path)
            
            if os.path.exists(results_full_path):
                try:
                    with open(results_full_path, 'r') as f:
                        results_data = json.load(f)
                        analysis_found = True
                        logger.info(f"Found analysis results at database path: {results_full_path}")
                except Exception as e:
                    logger.warning(f"Could not load results from database path {results_full_path}: {e}")
        
        # If not found via database path, check visual_analysis_cache table for dojo results
        if not analysis_found:
            logger.info(f"Checking visual_analysis_cache for deck ID {deck_id}")
            
            # Query visual_analysis_cache directly with project_document.id
            if source_table == 'project_documents':
                logger.info(f"Project document deck {deck_id}, querying visual_analysis_cache directly")
                
                # Query visual_analysis_cache with project_document ID
                cache_query = text("""
                SELECT analysis_result_json, vision_model_used, created_at
                FROM visual_analysis_cache 
                WHERE document_id = :deck_id
                ORDER BY created_at DESC
                LIMIT 1
                """)
                
                cache_result = db.execute(cache_query, {"deck_id": deck_id}).fetchone()
            else:
                # For project_documents table, use document_id
                cache_query = text("""
                SELECT analysis_result_json, vision_model_used, created_at
                FROM visual_analysis_cache 
                WHERE document_id = :deck_id
                ORDER BY created_at DESC
                LIMIT 1
                """)
                
                cache_result = db.execute(cache_query, {"deck_id": deck_id}).fetchone()
            
            if cache_result:
                try:
                    cached_analysis_json = cache_result[0]
                    vision_model = cache_result[1]
                    created_at = cache_result[2]
                    
                    logger.info(f"Found cached visual analysis for deck {deck_id}, model: {vision_model}")
                    
                    # Parse the cached analysis JSON
                    if isinstance(cached_analysis_json, str):
                        cached_analysis = json.loads(cached_analysis_json)
                    else:
                        cached_analysis = cached_analysis_json
                    
                    # Create results_data structure from cached analysis
                    results_data = {
                        "visual_analysis_results": cached_analysis.get("visual_analysis_results", cached_analysis if isinstance(cached_analysis, list) else []),
                        "processing_metadata": {
                            "source": "visual_analysis_cache",
                            "vision_model": vision_model,
                            "created_at": str(created_at)
                        }
                    }
                    
                    analysis_found = True
                    logger.info(f"✅ Found visual analysis in cache for deck {deck_id}")
                    
                except Exception as e:
                    logger.warning(f"Could not parse cached visual analysis for deck {deck_id}: {e}")
            else:
                logger.info(f"No cached visual analysis found for deck {deck_id}")
                
                # As a fallback, check if there's any company offering data from experiments
                logger.info(f"Checking for company offering data in projects table")
                
                # Try to find the company offering from the projects table
                offering_query = text("""
                SELECT company_offering, project_metadata
                FROM projects p
                JOIN project_documents pd ON p.id = pd.project_id
                WHERE pd.id = :deck_id AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
                """)
                
                offering_result = db.execute(offering_query, {"deck_id": deck_id}).fetchone()
                
                if offering_result and offering_result[0]:
                    logger.info(f"Found company offering data for deck {deck_id}")
                    company_offering = offering_result[0]
                    project_metadata = offering_result[1] if offering_result[1] else {}
                    
                    # Create results using company offering data
                    results_data = {
                        "company_offering": company_offering,
                        "processing_metadata": {
                            "source": "projects_table_fallback",
                            "has_visual_analysis": False
                        },
                        "project_metadata": project_metadata
                    }
                    
                    analysis_found = True
                    logger.info(f"✅ Using company offering data as fallback for deck {deck_id}")
                else:
                    logger.warning(f"No company offering data found for deck {deck_id}")
        
        # If still not found, look in file-based results as final fallback
        if not analysis_found:
            logger.info(f"Final fallback: checking file-based results for deck ID {deck_id}")
            
            results_dir = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "results")
            if os.path.exists(results_dir):
                try:
                    result_files = os.listdir(results_dir)
                    job_pattern = f"job_{deck_id}_"
                    matching_files = [f for f in result_files if f.startswith(job_pattern) and f.endswith('_results.json')]
                    
                    if matching_files:
                        matching_files.sort(reverse=True)
                        results_file_path = os.path.join(results_dir, matching_files[0])
                        
                        with open(results_file_path, 'r') as f:
                            results_data = json.load(f)
                            analysis_found = True
                            logger.info(f"✅ Found file-based results at: {results_file_path}")
                except Exception as e:
                    logger.warning(f"Error checking file-based results: {e}")
        
        if not analysis_found:
            logger.warning(f"No analysis results found for deck {deck_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis results not found for this deck"
            )
        
        # Extract visual analysis results
        visual_results = results_data.get("visual_analysis_results", [])
        
        # If no visual analysis results, create minimal slide entries with slide images but no analysis text
        if not visual_results:
            logger.warning(f"No visual analysis results found for deck {deck_id}, creating slides with images only")
            
            # Look for slide images to create basic slide structure
            deck_name = os.path.splitext(os.path.basename(file_path))[0]
            filesystem_deck_name = deck_name.replace(' ', '_')
            # Look for slide images in company analysis directory
            analysis_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects")
            
            if os.path.exists(analysis_path):
                # Check if this company has analysis data
                company_analysis_path = os.path.join(analysis_path, "analysis")
                if os.path.exists(company_analysis_path):
                    for dir_name in os.listdir(company_analysis_path):
                        if deck_name in dir_name or filesystem_deck_name in dir_name:
                            dir_path = os.path.join(company_analysis_path, dir_name)
                        if os.path.exists(dir_path):
                            slide_files = sorted([f for f in os.listdir(dir_path) if f.startswith('slide_') and f.endswith(('.jpg', '.png'))])
                            
                            if slide_files:
                                logger.info(f"Creating slide structure from {len(slide_files)} slide images")
                                
                                # Create visual analysis entries with images but no analysis text
                                visual_results = []
                                for i, slide_file in enumerate(slide_files, 1):
                                    slide_path = os.path.join(dir_path, slide_file)
                                    visual_results.append({
                                        "page_number": i,
                                        "slide_image_path": slide_path,
                                        "description": "Visual analysis not available for this slide",
                                        "deck_name": deck_name
                                    })
                                
                                logger.info(f"Created {len(visual_results)} slide entries with images only")
                                break
        
        if not visual_results:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No slides found for this deck"
            )
        
        # Extract deck name from file path
        deck_name = os.path.splitext(os.path.basename(file_path))[0]
        
        # Format slide analysis data
        slides = []
        for slide_data in visual_results:
            if isinstance(slide_data, dict):
                slides.append(SlideAnalysisResponse(
                    page_number=slide_data.get("page_number", 0),
                    slide_image_path=slide_data.get("slide_image_path", ""),
                    description=slide_data.get("description", ""),
                    deck_name=slide_data.get("deck_name", deck_name)
                ))
            else:
                # Handle legacy format (string descriptions)
                slides.append(SlideAnalysisResponse(
                    page_number=len(slides) + 1,
                    slide_image_path="",
                    description=str(slide_data),
                    deck_name=deck_name
                ))
        
        return DeckAnalysisResponse(
            deck_id=deck_id,
            deck_name=deck_name,
            company_id=company_id,
            total_slides=len(slides),
            slides=slides,
            processing_metadata=results_data.get("processing_metadata", {})
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting deck analysis for project {project_id}, deck {deck_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve deck analysis"
        )

@router.get("/{project_id}/results/{deck_id}")
async def get_project_results(
    project_id: int,
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analysis results for a specific deck - DATABASE-FIRST APPROACH"""
    try:
        # Check access permissions
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get deck information from project_documents
        project_doc_query = text("""
        SELECT pd.id, pd.file_name, pd.file_path, p.company_id, u.email
        FROM project_documents pd
        JOIN projects p ON pd.project_id = p.id
        LEFT JOIN users u ON pd.uploaded_by = u.id
        WHERE pd.project_id = :project_id AND pd.id = :deck_id 
        AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
        """)
        
        deck_result = db.execute(project_doc_query, {"project_id": project_id, "deck_id": deck_id}).fetchone()
        
        if not deck_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deck {deck_id} not found"
            )
        
        deck_id_db, file_name, file_path, company_id, user_email = deck_result
        logger.info(f"Loading database-first results for deck {deck_id}")
        
        # DATABASE-FIRST: Load all data from database tables
        
        # 1. Get template processing results
        template_query = text("""
            SELECT template_processing_results_json
            FROM extraction_experiments 
            WHERE document_ids LIKE '%' || :deck_id || '%' 
            AND template_processing_results_json IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
        """)
        template_result = db.execute(template_query, {"deck_id": str(deck_id)}).fetchone()
        
        # 2. Get extraction results (company_offering, classification, etc.)
        extraction_query = text("""
            SELECT results_json
            FROM extraction_experiments 
            WHERE document_ids LIKE '%' || :deck_id || '%' 
            AND results_json IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
        """)
        extraction_result = db.execute(extraction_query, {"deck_id": str(deck_id)}).fetchone()
        
        # 3. Get specialized analysis results
        specialized_analysis_query = text("""
            SELECT analysis_type, analysis_result 
            FROM specialized_analysis_results 
            WHERE document_id = :deck_id
        """)
        specialized_results = db.execute(specialized_analysis_query, {"deck_id": deck_id}).fetchall()
        
        # 4. Get visual analysis (if needed for partial results)
        visual_query = text("""
            SELECT analysis_result_json FROM visual_analysis_cache 
            WHERE document_id = :deck_id
            ORDER BY created_at DESC
            LIMIT 1
        """)
        visual_result = db.execute(visual_query, {"deck_id": deck_id}).fetchone()
        
        # Build complete results from database
        results_data = {}
        
        # Add template processing results if available
        if template_result and template_result[0]:
            try:
                template_data = json.loads(template_result[0])
                template_analysis = template_data.get("template_analysis", "")
                
                # Extract chapter scores from structured chapter_analysis if available
                chapter_scores = template_data.get("chapter_scores", {})
                chapter_analysis = template_data.get("chapter_analysis", {})
                
                if not chapter_scores and chapter_analysis:
                    # Extract scores from structured chapter_analysis 
                    chapter_scores = {}
                    for chapter_key, chapter_data in chapter_analysis.items():
                        if isinstance(chapter_data, dict) and "average_score" in chapter_data:
                            chapter_scores[chapter_key] = chapter_data["average_score"]
                
                # Fallback: parse from template_analysis text if no structured data
                if not chapter_scores and template_analysis:
                    chapter_scores = parse_chapter_scores_from_text(template_analysis)
                
                # Calculate overall score from chapter scores
                overall_score = 0.0
                if chapter_scores:
                    overall_score = sum(chapter_scores.values()) / len(chapter_scores)
                
                results_data.update({
                    "template_analysis": template_analysis,
                    "template_used": template_data.get("template_used", "Unknown"),
                    "processed_at": template_data.get("processed_at"),
                    "thumbnails": template_data.get("thumbnails", []),
                    "chapter_analysis": template_data.get("chapter_analysis", {}),
                    "chapter_scores": chapter_scores,
                    "overall_score": round(overall_score, 2),
                    "processing_metadata": template_data.get("processing_metadata", {}),
                })
                logger.info(f"Added template processing results for deck {deck_id}, parsed {len(chapter_scores)} chapter scores")
            except Exception as e:
                logger.warning(f"Failed to parse template results: {e}")
        
        # Add extraction results if available
        if extraction_result and extraction_result[0]:
            try:
                extraction_data = json.loads(extraction_result[0])
                
                # Handle both new format (arrays) and legacy format (keyed by deck_id)
                deck_data = extraction_data.get(str(deck_id), {})
                
                # New format: data is in arrays keyed by extraction type
                if not deck_data and any(key in extraction_data for key in ["offering_extraction", "company_names", "classification", "funding_amounts", "deck_dates"]):
                    # Extract data from array format for this specific deck_id
                    company_offering = ""
                    company_name = ""
                    classification = {}
                    funding_amount = ""
                    deck_date = ""
                    
                    # Extract offering
                    if "offering_extraction" in extraction_data:
                        for item in extraction_data["offering_extraction"]:
                            if item.get("deck_id") == deck_id:
                                company_offering = item.get("offering_extraction", "")
                                break
                    
                    # Extract company name
                    if "company_names" in extraction_data:
                        for item in extraction_data["company_names"]:
                            if item.get("deck_id") == deck_id:
                                company_name = item.get("company_name_extraction", "")
                                break
                    
                    # Extract classification
                    if "classification" in extraction_data:
                        for item in extraction_data["classification"]:
                            if item.get("deck_id") == deck_id:
                                classification = item.get("classification_result", {})
                                break
                    
                    # Extract funding amount
                    if "funding_amounts" in extraction_data:
                        for item in extraction_data["funding_amounts"]:
                            if item.get("deck_id") == deck_id:
                                funding_amount = item.get("funding_amount_extraction", "")
                                break
                    
                    # Extract deck date
                    if "deck_dates" in extraction_data:
                        for item in extraction_data["deck_dates"]:
                            if item.get("deck_id") == deck_id:
                                deck_date = item.get("deck_date_extraction", "")
                                break
                    
                    results_data.update({
                        "company_offering": company_offering,
                        "company_name": company_name,
                        "classification": classification,  # Keep full classification object
                        "funding_amount": funding_amount,
                        "deck_date": deck_date
                    })
                    logger.info(f"Added extraction results for deck {deck_id} (array format)")
                
                # Legacy format: data is keyed by deck_id
                elif deck_data:
                    results_data.update({
                        "company_offering": deck_data.get("company_offering", ""),
                        "company_name": deck_data.get("company_name", ""),
                        "classification": deck_data.get("classification", {}),
                        "funding_amount": deck_data.get("funding_amount", ""),
                        "deck_date": deck_data.get("deck_date", "")
                    })
                    logger.info(f"Added extraction results for deck {deck_id} (legacy format)")
                    
            except Exception as e:
                logger.warning(f"Failed to parse extraction results: {e}")
        
        # Add specialized analysis if available
        if specialized_results:
            specialized_analysis = {}
            for analysis_type, analysis_result in specialized_results:
                specialized_analysis[analysis_type] = analysis_result
            results_data["specialized_analysis"] = specialized_analysis
            logger.info(f"Added {len(specialized_results)} specialized analysis results for deck {deck_id}")
        
        # Check if we have enough data to return results
        has_template = bool(template_result)
        has_extraction = bool(extraction_result) 
        has_specialized = bool(specialized_results)
        has_visual = bool(visual_result)
        
        if not (has_template or has_extraction or has_specialized or has_visual):
            # FALLBACK: Try file-based approach for legacy data
            if file_path and os.path.exists(file_path):
                logger.info(f"No database results found, falling back to file: {file_path}")
                try:
                    with open(file_path, 'r') as f:
                        file_data = json.load(f)
                    results_data.update(file_data)
                    
                    # Still add database specialized analysis even for file-based results
                    if specialized_results:
                        specialized_analysis = {}
                        for analysis_type, analysis_result in specialized_results:
                            specialized_analysis[analysis_type] = analysis_result
                        results_data["specialized_analysis"] = specialized_analysis
                        
                except Exception as e:
                    logger.warning(f"Failed to load file results: {e}")
            
            if not results_data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No analysis data available for this document."
                )
        
        # Add metadata
        results_data["analysis_metadata"] = {
            "source": "database_first",
            "deck_id": deck_id,
            "has_template_processing": has_template,
            "has_extraction_results": has_extraction,
            "has_specialized_analysis": has_specialized,
            "has_visual_analysis": has_visual
        }
        
        # Remove visual_analysis_results from this endpoint (it's in deck-analysis)
        if "visual_analysis_results" in results_data:
            del results_data["visual_analysis_results"]
        
        return results_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project results for project {project_id}, deck {deck_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get project results: {str(e)}"
        )

@router.get("/{project_id}/uploads", response_model=ProjectUploadsResponse)
async def get_project_uploads(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all uploads for a project"""
    try:
        # Check access permissions using unified access control
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get project information to determine company_id for response
        project_query = text("""
        SELECT p.company_id FROM projects p 
        WHERE p.id = :project_id AND p.is_active = TRUE
        """)
        
        project_result = db.execute(project_query, {"project_id": project_id}).fetchone()
        
        if not project_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        company_id = project_result[0] or "unknown"
        
        # Get project documents (modern approach) - only documents for this specific project
        uploads_query = text("""
        SELECT pd.id, pd.file_name, pd.file_path, pd.upload_date, pd.processing_status, 
               pd.file_size, u.email, u.company_name, p.company_id as project_company_id
        FROM project_documents pd
        JOIN projects p ON pd.project_id = p.id
        LEFT JOIN users u ON pd.uploaded_by = u.id
        WHERE pd.project_id = :project_id 
        AND pd.document_type = 'pitch_deck' 
        AND pd.is_active = TRUE
        ORDER BY pd.upload_date DESC
        """)
        
        uploads_result = db.execute(uploads_query, {"project_id": project_id}).fetchall()
        
        uploads = []
        for upload in uploads_result:
            deck_id, file_name, file_path, upload_date, processing_status, file_size, user_email, company_name, project_company_id = upload
            
            # No filtering needed - we already query only this project's documents
            # Access control was already verified by check_project_access()
            
            # Get file info
            if file_path:
                if file_path.startswith('/'):
                    full_path = file_path
                else:
                    full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, file_path)
                filename = os.path.basename(file_path)
            else:
                # Use file_name if file_path is not available
                filename = file_name or f"deck_{deck_id}.pdf"
                full_path = None
            
            # Use database file_size if available, otherwise check filesystem
            if file_size:
                actual_file_size = file_size
            elif full_path and os.path.exists(full_path):
                actual_file_size = os.path.getsize(full_path)
            else:
                actual_file_size = 0
                
            file_type = "PDF"
            pages = None
            
            # Check for visual analysis completion and get page count
            visual_analysis_completed = False
            
            # Check extraction_experiments table for analysis results
            try:
                # First check for extraction experiment results
                extraction_check = db.execute(text("""
                    SELECT 1 FROM extraction_experiments 
                    WHERE document_ids LIKE '%' || :deck_id || '%'
                    AND results_json IS NOT NULL
                    LIMIT 1
                """), {"deck_id": str(deck_id)}).fetchone()
                
                # Check visual_analysis_cache table
                cache_check = db.execute(text("""
                    SELECT 1 FROM visual_analysis_cache 
                    WHERE document_id = :deck_id 
                    LIMIT 1
                """), {"deck_id": deck_id}).fetchone()
                
                if extraction_check or cache_check:
                    visual_analysis_completed = True
                    logger.debug(f"Deck {deck_id} marked as completed based on database analysis results")
                    
            except Exception as e:
                logger.warning(f"Could not check database analysis results for deck {deck_id}: {e}")
            
            # Alternative check: Look for slide images in project storage
            if not visual_analysis_completed and filename:
                try:
                    # Extract deck name from filename
                    deck_name = os.path.splitext(filename)[0]
                    
                    # Check multiple possible locations for slide images
                    possible_slide_dirs = [
                        # Standard company-based structure
                        os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", company_id, "analysis", deck_name),
                    ]
                    
                    for slide_images_dir in possible_slide_dirs:
                        if os.path.exists(slide_images_dir):
                            # Count slide image files
                            slide_files = [f for f in os.listdir(slide_images_dir) if f.startswith('slide_') and f.endswith('.jpg')]
                            if slide_files:
                                visual_analysis_completed = True
                                if not pages:  # Only set pages if we don't have it from results file
                                    pages = len(slide_files)
                                break  # Found slides, stop checking other locations
                            
                except Exception as e:
                    logger.warning(f"Could not check slide images for deck {deck_id}: {e}")
            
            uploads.append(ProjectUpload(
                id=deck_id,
                filename=filename,
                file_path=file_path or "",
                file_size=actual_file_size,
                upload_date=upload_date,
                file_type=file_type,
                pages=pages,
                processing_status=processing_status or "pending",
                visual_analysis_completed=visual_analysis_completed
            ))
        
        return ProjectUploadsResponse(
            company_id=company_id,
            uploads=uploads
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project uploads for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project uploads"
        )

@router.get("/documents/{document_id}/slide-image/{slide_filename}")
async def get_document_slide_image(
    document_id: int,
    slide_filename: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Serve slide images for a specific document"""
    try:
        # Get document information and check access
        document_query = text("""
        SELECT pd.id, pd.file_name, pd.original_filename, pd.project_id, p.company_id 
        FROM project_documents pd
        JOIN projects p ON pd.project_id = p.id
        WHERE pd.id = :document_id AND pd.is_active = TRUE AND p.is_active = TRUE
        """)
        
        document_result = db.execute(document_query, {"document_id": document_id}).fetchone()
        
        if not document_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found"
            )
        
        doc_id, file_name, original_filename, project_id, company_id = document_result
        
        # Check project access permissions
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this document's project"
            )
        
        # Derive deck name from filename (remove extension)
        deck_name = os.path.splitext(original_filename)[0] if original_filename else os.path.splitext(file_name)[0]
        
        # Construct image path - check multiple possible locations
        possible_paths = [
            # Standard company-based structure
            os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", company_id, "analysis", deck_name, slide_filename),
        ]
        
        image_path = None
        for path in possible_paths:
            logger.info(f"Checking image path: {path}")
            if os.path.exists(path):
                image_path = path
                logger.info(f"Found image at: {path}")
                break
        
        if not image_path:
            # Try to find the image in any directory that contains the deck name
            # Search through company analysis directories
            projects_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects")
            if os.path.exists(projects_path):
                logger.info(f"Searching in company analysis directories for deck containing: {deck_name}")
                for company_dir in os.listdir(projects_path):
                    analysis_dir = os.path.join(projects_path, company_dir, "analysis")
                    if os.path.exists(analysis_dir):
                        for deck_dir in os.listdir(analysis_dir):
                            if deck_name in deck_dir:
                                potential_path = os.path.join(analysis_dir, deck_dir, slide_filename)
                        logger.info(f"Checking potential path: {potential_path}")
                        if os.path.exists(potential_path):
                            image_path = potential_path
                            logger.info(f"Found image in directory: {dir_name}")
                            break
        
        # Debug logging
        if image_path:
            logger.info(f"Final image path: {image_path}")
            logger.info(f"File exists: {os.path.exists(image_path)}")
        else:
            logger.error(f"No valid image path found for {slide_filename}")
        
        if not image_path or not os.path.exists(image_path):
            # Development fallback - create placeholder image if shared filesystem doesn't exist
            if not os.path.exists(settings.SHARED_FILESYSTEM_MOUNT_PATH):
                logger.warning(f"Development mode: Serving placeholder image for {slide_filename}")
                
                # Create a simple placeholder image using PIL
                try:
                    from PIL import Image, ImageDraw, ImageFont
                    import io
                    
                    # Create a 800x600 placeholder image
                    img = Image.new('RGB', (800, 600), color='#f0f0f0')
                    draw = ImageDraw.Draw(img)
                    
                    # Add text
                    slide_num = slide_filename.replace('slide_', '').replace('.jpg', '').replace('.png', '')
                    text_lines = [
                        f"Slide {slide_num}",
                        "Development Mode",
                        "Placeholder Image",
                        "",
                        f"Deck: {deck_name}",
                        f"Company: {company_id}"
                    ]
                    
                    # Draw text
                    y_offset = 200
                    for line in text_lines:
                        # Get text size (approximate)
                        text_width = len(line) * 12
                        x = (800 - text_width) // 2
                        draw.text((x, y_offset), line, fill='#666666')
                        y_offset += 40
                    
                    # Save to bytes
                    img_byte_arr = io.BytesIO()
                    img.save(img_byte_arr, format='JPEG', quality=85)
                    img_byte_arr.seek(0)
                    
                    from fastapi.responses import StreamingResponse
                    return StreamingResponse(
                        io.BytesIO(img_byte_arr.getvalue()),
                        media_type="image/jpeg",
                        headers={"Content-Disposition": f"inline; filename={slide_filename}"}
                    )
                    
                except ImportError:
                    logger.warning("PIL not available, serving text placeholder")
                    # Fallback to text response if PIL is not available
                    placeholder_text = f"Slide {slide_filename} - Development Placeholder\nDeck: {deck_name}\nCompany: {company_id}"
                    from fastapi.responses import Response
                    return Response(
                        content=placeholder_text,
                        media_type="text/plain",
                        headers={"Content-Disposition": f"inline; filename={slide_filename}.txt"}
                    )
            
            # Add more debug info for production
            if image_path:
                parent_dir = os.path.dirname(image_path)
                logger.error(f"Image not found: {image_path}")
                logger.error(f"Parent directory exists: {os.path.exists(parent_dir)}")
                if os.path.exists(parent_dir):
                    logger.error(f"Files in parent directory: {os.listdir(parent_dir)}")
            else:
                logger.error(f"No valid path found for slide {slide_filename} in deck {deck_name}")
                
                # List what directories are actually available
                projects_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects")
                if os.path.exists(projects_path):
                    available_dirs = os.listdir(projects_path)
                    logger.error(f"Available analysis directories: {available_dirs}")
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Slide image not found: {slide_filename} for deck {deck_name}"
            )
        
        # Return image file
        from fastapi.responses import FileResponse
        return FileResponse(
            path=image_path,
            media_type="image/jpeg",
            filename=slide_filename
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving slide image {company_id}/{deck_name}/{slide_filename}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to serve slide image"
        )

@router.delete("/{project_id}/deck/{deck_id}")
async def delete_deck(
    project_id: int,
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a pitch deck including PDF, images, and results"""
    try:
        # Check access permissions using unified access control
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get deck information from project_documents
        deck_query = text("""
        SELECT pd.id, pd.file_name, pd.file_path, pd.analysis_results_path, u.email, u.company_name, 'project_documents' as source_table
        FROM project_documents pd
        LEFT JOIN users u ON pd.uploaded_by = u.id
        JOIN projects p ON pd.project_id = p.id
        WHERE pd.id = :deck_id AND pd.project_id = :project_id 
        AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
        """)
        
        deck_result = db.execute(deck_query, {"deck_id": deck_id, "project_id": project_id}).fetchone()
        
        if not deck_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deck {deck_id} not found"
            )
        
        deck_id_db, file_name, file_path, results_file_path, user_email, company_name, source_table = deck_result
        
        # Get project company_id for folder paths
        project_query = text("""
        SELECT p.company_id FROM projects p 
        WHERE p.id = :project_id AND p.is_active = TRUE
        """)
        
        project_result = db.execute(project_query, {"project_id": project_id}).fetchone()
        company_id = project_result[0] if project_result else "unknown"
        
        # Access control already verified by check_project_access() - no additional verification needed
        
        # Delete the PDF file
        if file_path:
            if file_path.startswith('/'):
                pdf_full_path = file_path
            else:
                pdf_full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, file_path)
            
            if os.path.exists(pdf_full_path):
                try:
                    os.remove(pdf_full_path)
                    logger.info(f"Deleted PDF file: {pdf_full_path}")
                except Exception as e:
                    logger.warning(f"Could not delete PDF file {pdf_full_path}: {e}")
        
        # Delete the results file
        if results_file_path:
            if results_file_path.startswith('/'):
                results_full_path = results_file_path
            else:
                results_full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, results_file_path)
            
            if os.path.exists(results_full_path):
                try:
                    os.remove(results_full_path)
                    logger.info(f"Deleted results file: {results_full_path}")
                except Exception as e:
                    logger.warning(f"Could not delete results file {results_full_path}: {e}")
        
        # Delete the analysis folder with slide images
        analysis_folder = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", company_id, "analysis", file_name)
        if os.path.exists(analysis_folder):
            try:
                shutil.rmtree(analysis_folder)
                logger.info(f"Deleted analysis folder: {analysis_folder}")
            except Exception as e:
                logger.warning(f"Could not delete analysis folder {analysis_folder}: {e}")
        
        # Delete dependent records first to avoid foreign key violations
        logger.info(f"Cleaning up dependent records for document {deck_id}")
        
        # Delete slide feedback
        db.execute(text("DELETE FROM slide_feedback WHERE document_id = :deck_id"), {"deck_id": deck_id})
        
        # Delete visual analysis cache
        db.execute(text("DELETE FROM visual_analysis_cache WHERE document_id = :deck_id"), {"deck_id": deck_id})
        
        # Delete processing queue entries
        db.execute(text("DELETE FROM processing_queue WHERE document_id = :deck_id"), {"deck_id": deck_id})
        
        # Delete specialized analysis results
        db.execute(text("DELETE FROM specialized_analysis_results WHERE document_id = :deck_id"), {"deck_id": deck_id})
        
        # Delete extraction experiments (check if document is in the document_ids array)  
        db.execute(text("DELETE FROM extraction_experiments WHERE document_ids LIKE '%' || :deck_id || '%'"), {"deck_id": str(deck_id)})
        
        # Delete the main document record (only project_documents table exists)
        delete_query = text("DELETE FROM project_documents WHERE id = :deck_id")
        db.execute(delete_query, {"deck_id": deck_id})
        db.commit()
        
        logger.info(f"Successfully cleaned up all dependent records and deleted document {deck_id}")
        
        logger.info(f"Successfully deleted deck {deck_id} ({file_name}) from {source_table} for project {project_id}")
        
        return {"message": f"Deck {file_name} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting deck {deck_id} for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete deck"
        )


# Project Creation Models
class CreateProjectRequest(BaseModel):
    project_name: str = Field(..., min_length=1, max_length=255)
    company_name: str = Field(..., min_length=1, max_length=255)
    invite_emails: Optional[List[str]] = []
    invitation_language: Optional[str] = "en"

class CreateProjectResponse(BaseModel):
    project_id: int
    company_id: str
    project_name: str
    owner_id: int
    invitations_sent: int
    project_url: str


@router.post("/create", response_model=CreateProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project and optionally invite users"""
    try:
        # Only GPs can create projects for other companies
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can create projects"
            )
        
        # Generate company_id from company name
        import re
        company_id = re.sub(r'[^a-z0-9-]', '', request.company_name.lower().replace(' ', '-'))
        
        # Check if project already exists
        existing_project = db.query(Project).filter(
            Project.company_id == company_id,
            Project.project_name == request.project_name
        ).first()
        
        if existing_project:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A project with this name already exists for this company"
            )
        
        # Create the project
        new_project = Project(
            company_id=company_id,
            project_name=request.project_name,
            owner_id=current_user.id,
            is_test=False,
            is_active=True
        )
        
        db.add(new_project)
        db.commit()
        db.refresh(new_project)
        
        # Add creator as project member with owner role
        owner_member = ProjectMember(
            project_id=new_project.id,
            user_id=current_user.id,
            role="owner",
            added_by_id=current_user.id
        )
        db.add(owner_member)
        db.commit()
        
        # Send invitations if provided
        invitations_sent = 0
        if request.invite_emails:
            try:
                from app.services.invitation_service import invite_users_to_project
                invitations = invite_users_to_project(
                    db=db,
                    project_id=new_project.id,
                    emails=request.invite_emails,
                    invited_by=current_user
                )
                invitations_sent = len(invitations)
            except Exception as e:
                logger.warning(f"Failed to send invitations for project {new_project.id}: {e}")
                # Don't fail project creation if invitations fail
        
        # Generate project URL
        project_url = f"/admin/project/{new_project.id}/startup-view"
        
        logger.info(f"Created project {new_project.id} ({request.project_name}) for company {company_id}")
        
        return CreateProjectResponse(
            project_id=new_project.id,
            company_id=company_id,
            project_name=request.project_name,
            owner_id=current_user.id,
            invitations_sent=invitations_sent,
            project_url=project_url
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )

# Extraction Results API
class ExtractionResult(BaseModel):
    deck_id: int
    deck_name: str
    company_name: Optional[str] = None
    company_offering: Optional[str] = None
    classification: Optional[dict] = None  # Changed to dict to include full classification object
    funding_amount: Optional[str] = None
    deck_date: Optional[str] = None
    extracted_at: Optional[datetime] = None

@router.get("/extraction-results", response_model=List[ExtractionResult])
async def get_extraction_results(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get extraction results for current user's decks"""
    try:
        logger.info(f"Getting extraction results for user {current_user.email}")
        
        # Get user's company_id
        company_id = get_company_id_from_user(current_user)
        
        # Query extraction results using unified results_json field - GPs have access to all projects, members only to their projects
        if current_user.role == 'gp':
            # GPs have access to all projects
            query = text("""
                SELECT DISTINCT
                    pd.id as deck_id,
                    pd.file_name as deck_name,
                    ee.results_json,
                    ee.created_at as extracted_at
                FROM project_documents pd
                JOIN projects p ON pd.project_id = p.id
                LEFT JOIN extraction_experiments ee ON ee.document_ids LIKE '%' || pd.id::text || '%'
                WHERE pd.document_type = 'pitch_deck'
                AND pd.is_active = TRUE
                AND ee.results_json IS NOT NULL
                ORDER BY ee.created_at DESC
            """)
            results = db.execute(query).fetchall()
        else:
            # Regular users only see their project documents
            query = text("""
                SELECT DISTINCT
                    pd.id as deck_id,
                    pd.file_name as deck_name,
                    ee.results_json,
                    ee.created_at as extracted_at
                FROM project_documents pd
                JOIN projects p ON pd.project_id = p.id
                JOIN project_members pm ON p.id = pm.project_id
                LEFT JOIN extraction_experiments ee ON ee.document_ids LIKE '%' || pd.id::text || '%'
                WHERE pm.user_id = :user_id
                AND pd.document_type = 'pitch_deck'
                AND pd.is_active = TRUE
                AND ee.results_json IS NOT NULL
                ORDER BY ee.created_at DESC
            """)
            results = db.execute(query, {"user_id": current_user.id}).fetchall()
        
        # Group results by deck_id to consolidate multiple experiments for the same deck
        deck_results = {}
        
        for row in results:
            deck_id = row.deck_id
            
            # Parse unified results_json - handle both new array format and legacy keyed format
            if row.results_json:
                try:
                    results_data = json.loads(row.results_json)
                    
                    # Try legacy format first (keyed by deck_id)
                    deck_data = results_data.get(str(deck_id), {})
                    
                    # If legacy format failed, try new array format
                    if not deck_data and any(key in results_data for key in ["offering_extraction", "company_names", "classification", "funding_amounts", "deck_dates"]):
                        # Extract data from array format for this specific deck_id
                        company_offering = ""
                        company_name = ""
                        classification_obj = {}
                        funding_amount = ""
                        deck_date = ""
                        
                        # Extract offering
                        if "offering_extraction" in results_data:
                            for item in results_data["offering_extraction"]:
                                if item.get("deck_id") == deck_id:
                                    company_offering = item.get("offering_extraction", "").strip()
                                    break
                        
                        # Extract company name
                        if "company_names" in results_data:
                            for item in results_data["company_names"]:
                                if item.get("deck_id") == deck_id:
                                    company_name = item.get("company_name_extraction", "").strip()
                                    break
                        
                        # Extract classification
                        if "classification" in results_data:
                            for item in results_data["classification"]:
                                if item.get("deck_id") == deck_id:
                                    classification_obj = item.get("classification_result", {})
                                    break
                        
                        # Extract funding amount
                        if "funding_amounts" in results_data:
                            for item in results_data["funding_amounts"]:
                                if item.get("deck_id") == deck_id:
                                    funding_amount = item.get("funding_amount_extraction", "").strip()
                                    break
                        
                        # Extract deck date
                        if "deck_dates" in results_data:
                            for item in results_data["deck_dates"]:
                                if item.get("deck_id") == deck_id:
                                    deck_date = item.get("deck_date_extraction", "").strip()
                                    break
                        
                        # Create deck_data structure for array format
                        deck_data = {
                            "company_name": company_name,
                            "company_offering": company_offering,
                            "classification": classification_obj,
                            "funding_amount": funding_amount,
                            "deck_date": deck_date
                        }
                    
                    if deck_data and any([deck_data.get("company_name"), deck_data.get("company_offering"), 
                                         deck_data.get("classification"), deck_data.get("funding_amount"), deck_data.get("deck_date")]):
                        # Keep the full classification object for detailed display
                        classification_obj = deck_data.get("classification", {})
                        
                        # Initialize or update deck results
                        if deck_id not in deck_results:
                            deck_results[deck_id] = {
                                'deck_id': deck_id,
                                'deck_name': row.deck_name,
                                'company_name': deck_data.get("company_name", "").strip(),
                                'company_offering': deck_data.get("company_offering", "").strip(),
                                'classification': classification_obj,  # Send full classification object
                                'funding_amount': deck_data.get("funding_amount", "").strip(),
                                'deck_date': deck_data.get("deck_date", "").strip(),
                                'extracted_at': row.extracted_at
                            }
                        else:
                            # Update with latest data if available
                            if deck_data.get("company_name"):
                                deck_results[deck_id]['company_name'] = deck_data.get("company_name", "").strip()
                            if deck_data.get("company_offering"):
                                deck_results[deck_id]['company_offering'] = deck_data.get("company_offering", "").strip()
                            if classification_obj:
                                deck_results[deck_id]['classification'] = classification_obj  # Send full classification object
                            if deck_data.get("funding_amount"):
                                deck_results[deck_id]['funding_amount'] = deck_data.get("funding_amount", "").strip()
                            if deck_data.get("deck_date"):
                                deck_results[deck_id]['deck_date'] = deck_data.get("deck_date", "").strip()
                except Exception as e:
                    logger.warning(f"Failed to parse extraction results for deck {deck_id}: {e}")
                    continue
        
        # Convert consolidated results to final format
        extraction_results = []
        for deck_data in deck_results.values():
            # Only add if we have at least some extraction data
            if any([deck_data['company_name'], deck_data['company_offering'], 
                   deck_data['classification'], deck_data['funding_amount'], deck_data['deck_date']]):
                extraction_results.append(ExtractionResult(
                    deck_id=deck_data['deck_id'],
                    deck_name=deck_data['deck_name'],
                    company_name=deck_data['company_name'],
                    company_offering=deck_data['company_offering'],
                    classification=deck_data['classification'],
                    funding_amount=deck_data['funding_amount'],
                    deck_date=deck_data['deck_date'],
                    extracted_at=deck_data['extracted_at']
                ))
        
        logger.info(f"Found {len(extraction_results)} consolidated extraction results for user {current_user.email}")
        return extraction_results
        
    except Exception as e:
        logger.error(f"Error getting extraction results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get extraction results"
        )