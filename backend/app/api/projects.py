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
from pathlib import Path

from ..db.database import get_db
from ..db.models import User, Project, ProjectMember
from .auth import get_current_user
from ..core.config import settings

logger = logging.getLogger(__name__)

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

def check_project_access(user: User, company_id: str) -> bool:
    """Check if user has access to the project"""
    # Startups can only access their own company projects
    if user.role == "startup":
        return get_company_id_from_user(user) == company_id
    
    # GPs can access any company project
    if user.role == "gp":
        return True
    
    return False

@router.get("/{company_id}/deck-analysis/{deck_id}", response_model=DeckAnalysisResponse)
async def get_deck_analysis(
    company_id: str,
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get slide-by-slide analysis for a specific deck"""
    try:
        logger.info(f"Getting deck analysis for company_id='{company_id}', deck_id={deck_id}, user={current_user.email}")
        
        # Check access permissions
        if not check_project_access(current_user, company_id):
            logger.warning(f"Access denied for user {current_user.email} to company {company_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get deck information - check both pitch_decks and project_documents tables
        # First try pitch_decks table (legacy)
        deck_query = text("""
        SELECT pd.id, pd.file_path, pd.results_file_path, u.email, u.company_name, 'pitch_decks' as source
        FROM pitch_decks pd
        JOIN users u ON pd.user_id = u.id
        WHERE pd.id = :deck_id
        """)
        
        deck_result = db.execute(deck_query, {"deck_id": deck_id}).fetchone()
        
        # If not found in pitch_decks, try project_documents table
        if not deck_result:
            logger.info(f"Deck {deck_id} not found in pitch_decks, checking project_documents")
            project_deck_query = text("""
            SELECT pd.id, pd.file_path, NULL as results_file_path, u.email, u.company_name, 'project_documents' as source
            FROM project_documents pd
            JOIN projects p ON pd.project_id = p.id
            JOIN users u ON pd.uploaded_by = u.id
            WHERE pd.id = :deck_id AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
            """)
            
            deck_result = db.execute(project_deck_query, {"deck_id": deck_id}).fetchone()
        
        if not deck_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deck {deck_id} not found"
            )
        
        deck_id_db, file_path, results_file_path, user_email, company_name, source_table = deck_result
        
        # Verify this deck belongs to the requested company (for ALL users including GPs)
        # For project_documents, check the project's company_id rather than uploader's company
        # This allows GP admins to upload decks for other companies
        if source_table == 'project_documents':
            # For project-based decks, get the project's company_id
            project_company_query = text("""
                SELECT p.company_id
                FROM projects p
                JOIN project_documents pd ON p.id = pd.project_id
                WHERE pd.id = :deck_id AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
            """)
            
            project_company_result = db.execute(project_company_query, {"deck_id": deck_id}).fetchone()
            
            if project_company_result:
                actual_company_id = project_company_result[0]
                logger.info(f"Project-based deck {deck_id}: project company_id = {actual_company_id}, requested company_id = {company_id}")
            else:
                logger.warning(f"Could not find project company for deck {deck_id}")
                actual_company_id = None
        else:
            # For legacy pitch_decks, use uploader's company (original logic)
            if company_name:
                import re
                actual_company_id = re.sub(r'[^a-z0-9-]', '', company_name.lower().replace(' ', '-'))
            else:
                actual_company_id = user_email.split('@')[0]
            
            logger.info(f"Legacy deck {deck_id}: uploader company_id = {actual_company_id}, requested company_id = {company_id}")
        
        # Allow GP access to dojo companies (test/demo data)
        is_dojo_access = (company_id == 'dojo' or 'dojo' in company_id.lower()) and current_user.role == "gp"
        
        if actual_company_id and actual_company_id != company_id and not is_dojo_access:
            logger.warning(f"Security violation: User {current_user.email} ({current_user.role}) attempted to access deck {deck_id} via company {company_id}, but deck belongs to {actual_company_id}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Deck {deck_id} does not belong to company {company_id}. Please access this deck through the correct company path: /project/{actual_company_id}/deck-viewer/{deck_id}"
            )
        elif is_dojo_access:
            logger.info(f"GP {current_user.email} accessing dojo company {company_id} - allowed for test data")
        
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
            
            # For project_documents (new system), find the corresponding pitch_deck_id by filename match
            if source_table == 'project_documents':
                logger.info(f"Project document deck {deck_id}, finding matching pitch_deck by filename")
                
                # Get the filename from project_documents
                filename_query = text("""
                    SELECT file_name FROM project_documents 
                    WHERE id = :deck_id AND document_type = 'pitch_deck' AND is_active = TRUE
                """)
                filename_result = db.execute(filename_query, {"deck_id": deck_id}).fetchone()
                
                if filename_result:
                    filename = filename_result[0]
                    logger.info(f"Looking for pitch_deck with filename: {filename}")
                    
                    # Find matching pitch_deck by filename
                    pitch_deck_query = text("""
                        SELECT id FROM pitch_decks 
                        WHERE file_name = :filename AND data_source = 'dojo'
                        ORDER BY created_at DESC LIMIT 1
                    """)
                    pitch_deck_result = db.execute(pitch_deck_query, {"filename": filename}).fetchone()
                    
                    if pitch_deck_result:
                        actual_pitch_deck_id = pitch_deck_result[0]
                        logger.info(f"Found matching pitch_deck ID {actual_pitch_deck_id} for project document {deck_id}")
                        
                        # Query visual_analysis_cache with the actual pitch_deck_id
                        cache_query = text("""
                        SELECT analysis_result_json, vision_model_used, created_at
                        FROM visual_analysis_cache 
                        WHERE pitch_deck_id = :pitch_deck_id
                        ORDER BY created_at DESC
                        LIMIT 1
                        """)
                        
                        cache_result = db.execute(cache_query, {"pitch_deck_id": actual_pitch_deck_id}).fetchone()
                    else:
                        logger.warning(f"No matching pitch_deck found for filename: {filename}")
                        cache_result = None
                else:
                    logger.warning(f"Could not get filename for project document {deck_id}")
                    cache_result = None
            else:
                # For legacy pitch_decks table, use deck_id directly
                cache_query = text("""
                SELECT analysis_result_json, vision_model_used, created_at
                FROM visual_analysis_cache 
                WHERE pitch_deck_id = :deck_id
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
            dojo_analysis_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", "dojo", "analysis")
            
            if os.path.exists(dojo_analysis_path):
                for dir_name in os.listdir(dojo_analysis_path):
                    if deck_name in dir_name or filesystem_deck_name in dir_name:
                        dir_path = os.path.join(dojo_analysis_path, dir_name)
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
        logger.error(f"Error getting deck analysis for {company_id}/{deck_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve deck analysis"
        )

@router.get("/{company_id}/results/{deck_id}")
async def get_project_results(
    company_id: str,
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get analysis results for a specific deck"""
    try:
        # Check access permissions
        if not check_project_access(current_user, company_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get deck information - check both pitch_decks and project_documents
        # First try pitch_decks table (regular uploads)
        deck_query = text("""
        SELECT pd.id, pd.file_path, pd.results_file_path, u.email, u.company_name, 'pitch_decks' as source
        FROM pitch_decks pd
        JOIN users u ON pd.user_id = u.id
        WHERE pd.id = :deck_id
        """)
        
        deck_result = db.execute(deck_query, {"deck_id": deck_id}).fetchone()
        
        # If not found in pitch_decks, try project_documents (dojo projects)
        if not deck_result:
            project_doc_query = text("""
            SELECT pd.id, pd.file_path, 
                   (SELECT file_path FROM project_documents pd2 
                    WHERE pd2.project_id = pd.project_id 
                    AND pd2.document_type = 'analysis_results' 
                    AND pd2.is_active = TRUE 
                    LIMIT 1) as results_file_path,
                   u.email, p.company_id, 'project_documents' as source
            FROM project_documents pd
            JOIN projects p ON pd.project_id = p.id
            LEFT JOIN users u ON pd.uploaded_by = u.id
            WHERE pd.id = :deck_id AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
            """)
            
            deck_result = db.execute(project_doc_query, {"deck_id": deck_id}).fetchone()
        
        if not deck_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deck {deck_id} not found"
            )
        
        deck_id_db, file_path, results_file_path, user_email, company_name, source = deck_result
        
        # Verify this deck belongs to the requested company (skip for GP admin access)
        if current_user.role != "gp":
            if company_name:
                import re
                deck_company_id = re.sub(r'[^a-z0-9-]', '', company_name.lower().replace(' ', '-'))
            else:
                deck_company_id = user_email.split('@')[0]
            if deck_company_id != company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Deck doesn't belong to this company"
                )
        
        # Load analysis results
        if not results_file_path:
            # Check if template processing results exist based on source
            if source == 'pitch_decks':
                template_check = db.execute(text("""
                    SELECT template_processing_results_json 
                    FROM pitch_decks 
                    WHERE id = :deck_id AND template_processing_results_json IS NOT NULL
                """), {"deck_id": deck_id}).fetchone()
            else:
                # For project_documents, check if original pitch_deck has template processing
                template_check = db.execute(text("""
                    SELECT pd_orig.template_processing_results_json
                    FROM project_documents pd
                    JOIN pitch_decks pd_orig ON pd.file_path = pd_orig.file_path
                    WHERE pd.id = :deck_id AND pd_orig.template_processing_results_json IS NOT NULL
                """), {"deck_id": deck_id}).fetchone()
            
            if not template_check:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Analysis results not found for this deck"
                )
            else:
                # Use template processing results
                results_file_path = f"template_processed_{deck_id}"
        
        # Check if this is a template processing marker
        if results_file_path.startswith("template_processed"):
            logger.info(f"Loading template processing results for deck {deck_id}")
            
            # Get template processing results from database based on source
            if source == 'pitch_decks':
                template_query = text("""
                    SELECT template_processing_results_json 
                    FROM pitch_decks 
                    WHERE id = :deck_id
                """)
            else:
                # For dojo projects, get results from original pitch_decks table
                # Need to map project_document ID back to original pitch_deck ID
                template_query = text("""
                    SELECT pd_orig.template_processing_results_json, pd_orig.id as original_deck_id
                    FROM project_documents pd
                    JOIN pitch_decks pd_orig ON pd.file_path = pd_orig.file_path
                    WHERE pd.id = :deck_id
                """)
            
            template_result = db.execute(template_query, {"deck_id": deck_id}).fetchone()
            
            if not template_result or not template_result[0]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template processing results not found for this deck"
                )
            
            # Parse template processing data
            template_data = json.loads(template_result[0])
            
            # Check if we need to fetch from extraction_experiments (progressive delivery results)
            original_deck_id = template_result[1] if len(template_result) > 1 else deck_id
            if template_data.get("template_analysis") == "No chapter analysis available.":
                # Try to get progressive delivery results from extraction_experiments
                experiment_query = text("""
                    SELECT template_processing_results_json 
                    FROM extraction_experiments 
                    WHERE :deck_id = ANY(string_to_array(trim(both '{}' from pitch_deck_ids), ',')::int[])
                    AND template_processing_results_json IS NOT NULL
                    ORDER BY created_at DESC 
                    LIMIT 1
                """)
                
                experiment_result = db.execute(experiment_query, {"deck_id": original_deck_id}).fetchone()
                
                if experiment_result and experiment_result[0]:
                    try:
                        experiment_data = json.loads(experiment_result[0])
                        # Extract results for this specific deck from the experiment data
                        deck_results = experiment_data.get("results", [])
                        
                        for deck_entry in deck_results:
                            if deck_entry.get("deck_id") == original_deck_id:
                                # Found progressive delivery results for this deck
                                chapters_data = deck_entry.get("chapters", {})
                                if chapters_data:
                                    # Format chapters into template_analysis
                                    analysis_parts = []
                                    for chapter_name, chapter_content in chapters_data.items():
                                        # Format chapter with its questions and scores
                                        chapter_text = f"## {chapter_name}\n\n"
                                        if isinstance(chapter_content, dict):
                                            # Add chapter description if available
                                            if chapter_content.get("description"):
                                                chapter_text += f"**{chapter_content['description']}**\n\n"
                                            
                                            # Add questions and responses
                                            questions = chapter_content.get("questions", [])
                                            if questions:
                                                for q in questions:
                                                    chapter_text += f"**{q.get('question_text', 'Question')}**\n"
                                                    if q.get('response'):
                                                        chapter_text += f"{q['response']}\n"
                                                    else:
                                                        chapter_text += "No response provided.\n"
                                                    chapter_text += f"*Score: {q.get('score', 'N/A')}/7*\n\n"
                                            
                                            # Add overall chapter score
                                            if chapter_content.get("weighted_score"):
                                                chapter_text += f"**Chapter Score: {chapter_content['weighted_score']:.1f}/7**\n"
                                        else:
                                            chapter_text += str(chapter_content)
                                        
                                        analysis_parts.append(chapter_text)
                                    
                                    template_data = {
                                        "template_analysis": "\n\n".join(analysis_parts),
                                        "template_used": deck_entry.get("template_used", "Healthcare Template"),
                                        "processed_at": deck_entry.get("processed_at"),
                                        "thumbnail_path": deck_entry.get("thumbnail_path"),
                                        "slide_images": deck_entry.get("slide_images", [])
                                    }
                                break
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Failed to parse experiment results for deck {original_deck_id}: {e}")
            
            # For dojo projects, return structured data for startup-compatible display
            if source == 'project_documents':
                # Return the full template data as-is (startup-compatible JSON structure)
                if isinstance(template_data, dict) and ("chapter_analysis" in template_data or "report_chapters" in template_data):
                    # This is new startup-compatible format - return as-is
                    template_data["analysis_metadata"] = {
                        "source": "dojo_template_processing",
                        "deck_id": deck_id,
                        "original_deck_id": template_result[1] if len(template_result) > 1 else deck_id
                    }
                    return template_data
                else:
                    # Legacy format - convert to startup-compatible format
                    return {
                        "template_analysis": template_data.get("template_analysis", ""),
                        "template_used": template_data.get("template_used", "Unknown"),
                        "processed_at": template_data.get("processed_at"),
                        "thumbnail_path": template_data.get("thumbnail_path"),
                        "slide_images": template_data.get("slide_images", []),
                        "analysis_metadata": {
                            "source": "dojo_template_processing",
                            "deck_id": deck_id,
                            "original_deck_id": template_result[1] if len(template_result) > 1 else deck_id
                        }
                    }
            
            # Format results for frontend consumption - return the raw template analysis
            return {
                "template_analysis": template_data.get("template_analysis", ""),
                "template_used": template_data.get("template_used", "Unknown"),
                "processed_at": template_data.get("processed_at"),
                "thumbnails": template_data.get("thumbnails", []),
                "analysis_metadata": {
                    "source": "template_processing",
                    "deck_id": deck_id
                }
            }
        
        # Check if this is a dojo experiment marker
        elif results_file_path.startswith("dojo_experiment:"):
            logger.info(f"Loading dojo experiment results for deck {deck_id}")
            experiment_id = results_file_path.split("dojo_experiment:")[1]
            
            # Get template processing results from database
            experiment_query = text("""
                SELECT template_processing_results_json, experiment_name 
                FROM extraction_experiments 
                WHERE id = :experiment_id
            """)
            
            experiment_result = db.execute(experiment_query, {"experiment_id": experiment_id}).fetchone()
            
            if not experiment_result or not experiment_result[0]:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template processing results not found for this dojo experiment"
                )
            
            # Parse template processing data
            template_processing_data = json.loads(experiment_result[0])
            
            # Find results for this specific deck
            deck_results = None
            if template_processing_data.get("template_processing_results"):
                for result in template_processing_data["template_processing_results"]:
                    if result.get("deck_id") == deck_id:
                        deck_results = result
                        break
            
            if not deck_results:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Template processing results not found for this deck"
                )
            
            # Format results for frontend consumption - return structured data for startup-compatible display
            if isinstance(deck_results, dict) and ("chapter_analysis" in deck_results or "report_chapters" in deck_results):
                # This is new startup-compatible format - return as-is
                deck_results["analysis_metadata"] = {
                    "source": "dojo_experiment",
                    "experiment_id": experiment_id,
                    "processed_at": template_processing_data.get("processed_at")
                }
                results_data = deck_results
            else:
                # Legacy format - return as template_analysis
                results_data = {
                    "experiment_name": experiment_result[1],
                    "template_used": deck_results.get("template_used"),
                    "template_analysis": deck_results.get("template_analysis"),
                    "thumbnail_path": deck_results.get("thumbnail_path"),
                    "slide_images": deck_results.get("slide_images", []),
                    "analysis_metadata": {
                        "source": "dojo_experiment",
                        "experiment_id": experiment_id,
                        "processed_at": template_processing_data.get("processed_at")
                    }
                }
            
            logger.info(f"Loaded dojo experiment results for deck {deck_id} from experiment {experiment_id}")
            return results_data
        
        # Handle regular file-based results
        if results_file_path.startswith('/'):
            results_full_path = results_file_path
        else:
            results_full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, results_file_path)
        
        if not os.path.exists(results_full_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis results file not found"
            )
        
        # Load and return the results JSON
        with open(results_full_path, 'r') as f:
            results_data = json.load(f)
        
        # Remove visual_analysis_results from this endpoint (it's in deck-analysis)
        if "visual_analysis_results" in results_data:
            del results_data["visual_analysis_results"]
        
        return results_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project results for {company_id}/{deck_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project results"
        )

@router.get("/{company_id}/uploads", response_model=ProjectUploadsResponse)
async def get_project_uploads(
    company_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all uploads for a company project"""
    try:
        # Check access permissions
        if not check_project_access(current_user, company_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get all pitch decks and filter by company in application logic
        # This handles cases where company_id might not be populated in the database
        uploads_query = text("""
        SELECT pd.id, pd.file_path, pd.created_at, pd.results_file_path, u.email, pd.processing_status, u.company_name
        FROM pitch_decks pd
        JOIN users u ON pd.user_id = u.id
        ORDER BY pd.created_at DESC
        """)
        
        uploads_result = db.execute(uploads_query).fetchall()
        
        uploads = []
        for upload in uploads_result:
            deck_id, file_path, created_at, results_file_path, user_email, processing_status, company_name = upload
            
            # Filter to only include decks that belong to the requested company
            # Convert company name to company_id format for comparison
            if company_name:
                import re
                deck_company_id = re.sub(r'[^a-z0-9-]', '', company_name.lower().replace(' ', '-'))
            else:
                deck_company_id = user_email.split('@')[0]
            
            # Skip if this deck doesn't belong to the requested company (unless GP admin access)
            if current_user.role != "gp" and deck_company_id != company_id:
                continue
            # For GP admin access, only include if they specifically requested this company's uploads
            elif current_user.role == "gp" and deck_company_id != company_id:
                continue
            
            # Get file info
            full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, file_path)
            filename = os.path.basename(file_path)
            file_size = 0
            file_type = "PDF"
            pages = None
            
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
            
            # Check for visual analysis completion and get page count
            visual_analysis_completed = False
            if results_file_path:
                try:
                    if results_file_path.startswith('/'):
                        results_full_path = results_file_path
                    else:
                        results_full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, results_file_path)
                    
                    if os.path.exists(results_full_path):
                        with open(results_full_path, 'r') as f:
                            results_data = json.load(f)
                            # Check if visual analysis results exist
                            visual_results = results_data.get("visual_analysis_results", [])
                            if visual_results:
                                visual_analysis_completed = True
                                pages = len(visual_results)
                except Exception as e:
                    logger.warning(f"Could not extract page count from results file: {e}")
            
            # Alternative check: Look for slide images in project storage
            if not visual_analysis_completed:
                try:
                    # Extract deck name from filename
                    deck_name = os.path.splitext(filename)[0]
                    # Check if slide images directory exists and has images
                    slide_images_dir = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", company_id, "analysis", deck_name)
                    if os.path.exists(slide_images_dir):
                        # Count slide image files
                        slide_files = [f for f in os.listdir(slide_images_dir) if f.startswith('slide_') and f.endswith('.jpg')]
                        if slide_files:
                            visual_analysis_completed = True
                            if not pages:  # Only set pages if we don't have it from results file
                                pages = len(slide_files)
                except Exception as e:
                    logger.warning(f"Could not check slide images for deck {deck_id}: {e}")
            
            uploads.append(ProjectUpload(
                id=deck_id,
                filename=filename,
                file_path=file_path,
                file_size=file_size,
                upload_date=created_at,
                file_type=file_type,
                pages=pages,
                processing_status=processing_status,
                visual_analysis_completed=visual_analysis_completed
            ))
        
        return ProjectUploadsResponse(
            company_id=company_id,
            uploads=uploads
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project uploads for {company_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project uploads"
        )

@router.get("/{company_id}/slide-image/{deck_name}/{slide_filename}")
async def get_slide_image(
    company_id: str,
    deck_name: str,
    slide_filename: str,
    current_user: User = Depends(get_current_user)
):
    """Serve slide images from project storage"""
    try:
        # Check access permissions
        if not check_project_access(current_user, company_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Construct image path - check multiple possible locations
        possible_paths = [
            # Dojo structure (most likely)
            os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", "dojo", "analysis", deck_name, slide_filename),
            # Company-based structure (fallback)
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
            dojo_analysis_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", "dojo", "analysis")
            if os.path.exists(dojo_analysis_path):
                logger.info(f"Searching in dojo analysis directories for deck containing: {deck_name}")
                for dir_name in os.listdir(dojo_analysis_path):
                    if deck_name in dir_name:
                        potential_path = os.path.join(dojo_analysis_path, dir_name, slide_filename)
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
                dojo_analysis_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", "dojo", "analysis")
                if os.path.exists(dojo_analysis_path):
                    available_dirs = os.listdir(dojo_analysis_path)
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

@router.delete("/{company_id}/deck/{deck_id}")
async def delete_deck(
    company_id: str,
    deck_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a pitch deck including PDF, images, and results"""
    try:
        # Check access permissions
        if not check_project_access(current_user, company_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get deck information
        deck_query = text("""
        SELECT pd.id, pd.file_name, pd.file_path, pd.results_file_path, u.email, u.company_name
        FROM pitch_decks pd
        JOIN users u ON pd.user_id = u.id
        WHERE pd.id = :deck_id
        """)
        
        deck_result = db.execute(deck_query, {"deck_id": deck_id}).fetchone()
        
        if not deck_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Deck {deck_id} not found"
            )
        
        deck_id_db, file_name, file_path, results_file_path, user_email, company_name = deck_result
        
        # Verify this deck belongs to the requested company (skip for GP admin access)
        if current_user.role != "gp":
            if company_name:
                import re
                deck_company_id = re.sub(r'[^a-z0-9-]', '', company_name.lower().replace(' ', '-'))
            else:
                deck_company_id = user_email.split('@')[0]
            if deck_company_id != company_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Deck doesn't belong to this company"
                )
        
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
        
        # Delete the analysis folder with slide images (project-based structure)
        analysis_folder = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", company_id, "analysis", file_name)
        if os.path.exists(analysis_folder):
            try:
                shutil.rmtree(analysis_folder)
                logger.info(f"Deleted analysis folder: {analysis_folder}")
            except Exception as e:
                logger.warning(f"Could not delete analysis folder {analysis_folder}: {e}")
        
        # Delete the database record
        delete_query = text("DELETE FROM pitch_decks WHERE id = :deck_id")
        db.execute(delete_query, {"deck_id": deck_id})
        db.commit()
        
        logger.info(f"Successfully deleted deck {deck_id} ({file_name}) for company {company_id}")
        
        return {"message": f"Deck {file_name} deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting deck {deck_id} for company {company_id}: {e}")
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
    classification: Optional[str] = None
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
        
        # Query extraction results from user's pitch decks
        query = text("""
            SELECT DISTINCT
                pd.id as deck_id,
                pd.file_name as deck_name,
                ee.company_name_results_json,
                ee.results_json,
                ee.classification_results_json,
                ee.funding_amount_results_json,
                ee.deck_date_results_json,
                ee.created_at as extracted_at
            FROM pitch_decks pd
            LEFT JOIN extraction_experiments ee ON pd.id::text = ANY(string_to_array(trim(both '{}' from ee.pitch_deck_ids), ','))
            WHERE pd.company_id = :company_id
            AND ee.id IS NOT NULL
            ORDER BY ee.created_at DESC
        """)
        
        results = db.execute(query, {"company_id": company_id}).fetchall()
        
        # Group results by deck_id to consolidate multiple experiments for the same deck
        deck_results = {}
        
        for row in results:
            # Parse JSON results to extract data for this specific deck
            company_name = None
            company_offering = None
            classification = None
            funding_amount = None
            deck_date = None
            
            # Parse company name results
            if row.company_name_results_json:
                try:
                    name_data = json.loads(row.company_name_results_json)
                    # Handle both formats: direct array or wrapped in extraction_results
                    if isinstance(name_data, list):
                        results_array = name_data
                    else:
                        results_array = name_data.get("extraction_results", [])
                    
                    # Find result for this specific deck
                    for result in results_array:
                        if result.get("deck_id") == row.deck_id:
                            company_name = result.get("company_name_extraction", "").strip()
                            break
                except:
                    pass
            
            # Parse company offering results
            if row.results_json:
                try:
                    offering_data = json.loads(row.results_json)
                    # Handle both formats: direct array or wrapped in extraction_results
                    if isinstance(offering_data, list):
                        results_array = offering_data
                    else:
                        results_array = offering_data.get("extraction_results", [])
                    
                    # Find result for this specific deck
                    for result in results_array:
                        if result.get("deck_id") == row.deck_id:
                            company_offering = result.get("offering_extraction", "").strip()
                            break
                except:
                    pass
            
            # Parse classification results
            if row.classification_results_json:
                try:
                    class_data = json.loads(row.classification_results_json)
                    # Handle both formats: direct array or wrapped in classification_results
                    if isinstance(class_data, list):
                        results_array = class_data
                    else:
                        results_array = class_data.get("classification_results", [])
                    
                    # Find result for this specific deck
                    for result in results_array:
                        if result.get("deck_id") == row.deck_id:
                            class_result = result.get("classification_result", {})
                            if isinstance(class_result, dict):
                                classification = class_result.get("sector", "")
                            break
                except:
                    pass
            
            # Parse funding amount results
            if row.funding_amount_results_json:
                try:
                    funding_data = json.loads(row.funding_amount_results_json)
                    # Handle both formats: direct array or wrapped in extraction_results
                    if isinstance(funding_data, list):
                        results_array = funding_data
                    else:
                        results_array = funding_data.get("extraction_results", [])
                    
                    # Find result for this specific deck
                    for result in results_array:
                        if result.get("deck_id") == row.deck_id:
                            funding_amount = result.get("funding_amount_extraction", "").strip()
                            break
                except:
                    pass
            
            # Parse deck date results
            if row.deck_date_results_json:
                try:
                    date_data = json.loads(row.deck_date_results_json)
                    # Handle both formats: direct array or wrapped in extraction_results
                    if isinstance(date_data, list):
                        results_array = date_data
                    else:
                        results_array = date_data.get("extraction_results", [])
                    
                    # Find result for this specific deck  
                    for result in results_array:
                        if result.get("deck_id") == row.deck_id:
                            deck_date = result.get("deck_date_extraction", "").strip()
                            break
                except:
                    pass
            
            # Consolidate results by deck_id
            deck_id = row.deck_id
            if deck_id not in deck_results:
                deck_results[deck_id] = {
                    'deck_id': deck_id,
                    'deck_name': row.deck_name,
                    'company_name': None,
                    'company_offering': None,
                    'classification': None,
                    'funding_amount': None,
                    'deck_date': None,
                    'extracted_at': row.extracted_at
                }
            
            # Update with any non-empty values (latest experiments take precedence)
            if company_name:
                deck_results[deck_id]['company_name'] = company_name
            if company_offering:
                deck_results[deck_id]['company_offering'] = company_offering
            if classification:
                deck_results[deck_id]['classification'] = classification
            if funding_amount:
                deck_results[deck_id]['funding_amount'] = funding_amount
            if deck_date:
                deck_results[deck_id]['deck_date'] = deck_date
        
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