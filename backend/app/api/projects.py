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
from ..db.models import User
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
            
            # Query the visual_analysis_cache table
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
        
        # Get deck information
        deck_query = text("""
        SELECT pd.id, pd.file_path, pd.results_file_path, u.email, u.company_name
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
        
        deck_id_db, file_path, results_file_path, user_email, company_name = deck_result
        
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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis results not found for this deck"
            )
        
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