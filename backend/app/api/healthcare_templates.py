"""
Healthcare Templates API Endpoints
Handles classification, template management, and analysis configuration
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import json
import logging

from ..db.database import get_db
from ..db.models import User
from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/healthcare-templates", tags=["healthcare-templates"])

# Pydantic models for API requests/responses
class HealthcareSectorResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: str
    keywords: List[str]
    subcategories: List[str]
    confidence_threshold: float
    regulatory_requirements: Dict[str, Any]
    is_active: bool

class AnalysisTemplateResponse(BaseModel):
    id: int
    healthcare_sector_id: int
    name: str
    description: str
    template_version: Optional[str] = None
    specialized_analysis: List[str]
    is_active: bool
    is_default: bool
    usage_count: Optional[int] = 0
    sector_name: Optional[str] = None

class TemplateChapterResponse(BaseModel):
    id: int
    chapter_id: str
    name: str
    description: str
    weight: float
    order_index: int
    is_required: bool
    enabled: bool
    questions: List[Dict[str, Any]]

class ChapterQuestionResponse(BaseModel):
    id: int
    question_id: str
    question_text: str
    weight: float
    order_index: int
    enabled: bool
    scoring_criteria: str
    healthcare_focus: str

class ClassificationRequest(BaseModel):
    company_offering: str
    manual_classification: Optional[str] = None

class ClassificationResponse(BaseModel):
    primary_sector: str
    subcategory: str
    confidence_score: float
    reasoning: str
    secondary_sector: Optional[str] = None
    keywords_matched: List[str]
    recommended_template: int

class TemplateCustomizationRequest(BaseModel):
    base_template_id: int
    customization_name: str
    customized_chapters: Optional[Dict[str, Any]] = None
    customized_questions: Optional[Dict[str, Any]] = None
    customized_weights: Optional[Dict[str, Any]] = None

# Healthcare sectors endpoints  
@router.get("/sectors", response_model=List[HealthcareSectorResponse])
async def get_healthcare_sectors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all healthcare sectors (GP only)"""
    # Check if user is GP
    if current_user.role != "gp":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. GP role required."
        )
    try:
        query = text("""
        SELECT id, name, display_name, description, keywords, subcategories, 
               confidence_threshold, regulatory_requirements, is_active
        FROM healthcare_sectors
        WHERE is_active = TRUE
        ORDER BY display_name
        """)
        
        result = db.execute(query).fetchall()
        
        sectors = []
        for row in result:
            sectors.append(HealthcareSectorResponse(
                id=row[0],
                name=row[1],
                display_name=row[2],
                description=row[3],
                keywords=json.loads(row[4]),
                subcategories=json.loads(row[5]),
                confidence_threshold=row[6],
                regulatory_requirements=json.loads(row[7]),
                is_active=row[8]
            ))
        
        return sectors
        
    except Exception as e:
        logger.error(f"Error getting healthcare sectors: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve healthcare sectors"
        )

@router.get("/templates", response_model=List[AnalysisTemplateResponse])
async def get_all_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all analysis templates (GP only)"""
    # Check if user is GP
    if current_user.role != "gp":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. GP role required."
        )
    try:
        query = text("""
        SELECT at.id, at.healthcare_sector_id, at.name, at.description, at.template_version,
               at.specialized_analysis, at.is_active, at.is_default, at.usage_count,
               hs.display_name as sector_name
        FROM analysis_templates at
        LEFT JOIN healthcare_sectors hs ON at.healthcare_sector_id = hs.id
        WHERE at.is_active = TRUE
        ORDER BY at.is_default DESC, hs.display_name, at.name
        """)
        
        result = db.execute(query).fetchall()
        
        templates = []
        for row in result:
            templates.append(AnalysisTemplateResponse(
                id=row[0],
                healthcare_sector_id=row[1],
                name=row[2],
                description=row[3],
                template_version=row[4],
                specialized_analysis=json.loads(row[5]) if row[5] else {},
                is_active=row[6],
                is_default=row[7],
                usage_count=row[8] or 0,
                sector_name=row[9] or "General"
            ))
        
        return templates
        
    except Exception as e:
        logger.error(f"Error getting all templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve templates"
        )

@router.get("/sectors/{sector_id}/templates", response_model=List[AnalysisTemplateResponse])
async def get_sector_templates(
    sector_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all analysis templates for a specific healthcare sector (GP only)"""
    # Check if user is GP
    if current_user.role != "gp":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. GP role required."
        )
    try:
        query = text("""
        SELECT id, healthcare_sector_id, name, description, template_version,
               specialized_analysis, is_active, is_default, usage_count
        FROM analysis_templates
        WHERE healthcare_sector_id = :sector_id AND is_active = TRUE
        ORDER BY is_default DESC, name
        """)
        
        result = db.execute(query, {"sector_id": sector_id}).fetchall()
        
        templates = []
        for row in result:
            templates.append(AnalysisTemplateResponse(
                id=row[0],
                healthcare_sector_id=row[1],
                name=row[2],
                description=row[3],
                template_version=row[4],
                specialized_analysis=json.loads(row[5]),
                is_active=row[6],
                is_default=row[7],
                usage_count=row[8]
            ))
        
        return templates
        
    except Exception as e:
        logger.error(f"Error getting templates for sector {sector_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve templates for sector {sector_id}"
        )

@router.get("/templates/{template_id}", response_model=Dict[str, Any])
async def get_template_details(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed template information including chapters and questions (GP only)"""
    # Check if user is GP
    if current_user.role != "gp":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. GP role required."
        )
    try:
        # Get template basic info
        template_query = text("""
        SELECT t.id, t.name, t.description, t.template_version, t.specialized_analysis,
               s.name as sector_name, s.display_name as sector_display_name
        FROM analysis_templates t
        JOIN healthcare_sectors s ON t.healthcare_sector_id = s.id
        WHERE t.id = :template_id AND t.is_active = TRUE
        """)
        
        template_result = db.execute(template_query, {"template_id": template_id}).fetchone()
        
        if not template_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {template_id} not found"
            )
        
        # Get chapters
        chapters_query = text("""
        SELECT id, chapter_id, name, description, weight, order_index, 
               is_required, enabled
        FROM template_chapters
        WHERE template_id = :template_id AND enabled = TRUE
        ORDER BY order_index
        """)
        
        chapters_result = db.execute(chapters_query, {"template_id": template_id}).fetchall()
        
        # Get questions for each chapter
        chapters = []
        for chapter_row in chapters_result:
            chapter_id = chapter_row[0]
            
            questions_query = text("""
            SELECT id, question_id, question_text, weight, order_index, enabled,
                   scoring_criteria, healthcare_focus
            FROM chapter_questions
            WHERE chapter_id = :chapter_id AND enabled = TRUE
            ORDER BY order_index
            """)
            
            questions_result = db.execute(questions_query, {"chapter_id": chapter_id}).fetchall()
            
            questions = []
            for question_row in questions_result:
                questions.append({
                    "id": question_row[0],
                    "question_id": question_row[1],
                    "question_text": question_row[2],
                    "weight": question_row[3],
                    "order_index": question_row[4],
                    "enabled": question_row[5],
                    "scoring_criteria": question_row[6],
                    "healthcare_focus": question_row[7]
                })
            
            chapters.append({
                "id": chapter_row[0],
                "chapter_id": chapter_row[1],
                "name": chapter_row[2],
                "description": chapter_row[3],
                "weight": chapter_row[4],
                "order_index": chapter_row[5],
                "is_required": chapter_row[6],
                "enabled": chapter_row[7],
                "questions": questions
            })
        
        return {
            "template": {
                "id": template_result[0],
                "name": template_result[1],
                "description": template_result[2],
                "template_version": template_result[3],
                "specialized_analysis": json.loads(template_result[4]),
                "sector_name": template_result[5],
                "sector_display_name": template_result[6]
            },
            "chapters": chapters
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template details for {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve template details for {template_id}"
        )

@router.post("/classify", response_model=ClassificationResponse)
async def classify_startup(
    request: ClassificationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Classify a startup based on company offering"""
    try:
        # Import the classification service
        from ..services.startup_classifier import classify_startup_offering
        
        # Perform classification
        classification_result = await classify_startup_offering(
            request.company_offering,
            db,
            manual_classification=request.manual_classification
        )
        
        return ClassificationResponse(**classification_result)
        
    except Exception as e:
        logger.error(f"Error classifying startup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to classify startup"
        )

@router.post("/customize-template", response_model=Dict[str, Any])
async def customize_template(
    request: TemplateCustomizationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a customized template for a GP"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can customize templates"
            )
        
        # Insert customization
        insert_query = text("""
        INSERT INTO gp_template_customizations 
        (gp_email, base_template_id, customization_name, customized_chapters, 
         customized_questions, customized_weights, is_active)
        VALUES (:gp_email, :base_template_id, :customization_name, :customized_chapters, 
                :customized_questions, :customized_weights, TRUE)
        """)
        
        result = db.execute(insert_query, {
            "gp_email": current_user.email,
            "base_template_id": request.base_template_id,
            "customization_name": request.customization_name,
            "customized_chapters": json.dumps(request.customized_chapters or {}),
            "customized_questions": json.dumps(request.customized_questions or {}),
            "customized_weights": json.dumps(request.customized_weights or {})
        })
        
        customization_id = result.lastrowid
        db.commit()
        
        return {
            "customization_id": customization_id,
            "message": "Template customization created successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error customizing template: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to customize template"
        )

@router.get("/my-customizations", response_model=List[Dict[str, Any]])
async def get_my_customizations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all customizations for the current GP"""
    try:
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can view customizations"
            )
        
        query = text("""
        SELECT c.id, c.customization_name, c.base_template_id, c.created_at,
               t.name as template_name, s.display_name as sector_name
        FROM gp_template_customizations c
        JOIN analysis_templates t ON c.base_template_id = t.id
        JOIN healthcare_sectors s ON t.healthcare_sector_id = s.id
        WHERE c.gp_email = :gp_email AND c.is_active = TRUE
        ORDER BY c.created_at DESC
        """)
        
        result = db.execute(query, {"gp_email": current_user.email}).fetchall()
        
        customizations = []
        for row in result:
            customizations.append({
                "id": row[0],
                "customization_name": row[1],
                "base_template_id": row[2],
                "created_at": row[3],
                "template_name": row[4],
                "sector_name": row[5]
            })
        
        return customizations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting customizations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve customizations"
        )

@router.put("/templates/{template_id}")
async def update_template(
    template_id: int,
    request: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update an existing template (GP only)"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can update templates"
            )
        
        # Check if template exists and is active
        template_check_query = text("""
        SELECT id, name, is_default 
        FROM analysis_templates 
        WHERE id = :template_id AND is_active = TRUE
        """)
        
        template_result = db.execute(template_check_query, {"template_id": template_id}).fetchone()
        
        if not template_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {template_id} not found or already deleted"
            )
        
        # Prevent updating default templates
        if template_result[2]:  # is_default
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot update default templates"
            )
        
        # Update template name and description
        update_query = text("""
        UPDATE analysis_templates 
        SET name = :name, description = :description
        WHERE id = :template_id
        """)
        
        db.execute(update_query, {
            "template_id": template_id,
            "name": request.get("name", template_result[1]),
            "description": request.get("description", "")
        })
        db.commit()
        
        logger.info(f"Template {template_id} updated by GP {current_user.email}")
        
        return {
            "message": f"Template '{request.get('name', template_result[1])}' updated successfully",
            "template_id": template_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update template"
        )

@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete a template (GP only)"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can delete templates"
            )
        
        # Check if template exists and is active
        template_check_query = text("""
        SELECT id, name, is_default 
        FROM analysis_templates 
        WHERE id = :template_id AND is_active = TRUE
        """)
        
        template_result = db.execute(template_check_query, {"template_id": template_id}).fetchone()
        
        if not template_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {template_id} not found or already deleted"
            )
        
        # Prevent deletion of default templates
        if template_result[2]:  # is_default
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete default templates"
            )
        
        # Perform soft delete
        soft_delete_query = text("""
        UPDATE analysis_templates 
        SET is_active = FALSE 
        WHERE id = :template_id
        """)
        
        db.execute(soft_delete_query, {"template_id": template_id})
        db.commit()
        
        logger.info(f"Template {template_id} ({template_result[1]}) soft deleted by GP {current_user.email}")
        
        return {
            "message": f"Template '{template_result[1]}' deleted successfully",
            "template_id": template_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete template"
        )

@router.delete("/customizations/{customization_id}")
async def delete_customization(
    customization_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft delete a template customization (GP only)"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can delete customizations"
            )
        
        # Check if customization exists and belongs to the current user
        customization_check_query = text("""
        SELECT id, customization_name, gp_email 
        FROM gp_template_customizations 
        WHERE id = :customization_id AND is_active = TRUE
        """)
        
        customization_result = db.execute(customization_check_query, {"customization_id": customization_id}).fetchone()
        
        if not customization_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customization {customization_id} not found or already deleted"
            )
        
        # Check if the customization belongs to the current user
        if customization_result[2] != current_user.email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own customizations"
            )
        
        # Perform soft delete
        soft_delete_query = text("""
        UPDATE gp_template_customizations 
        SET is_active = FALSE 
        WHERE id = :customization_id
        """)
        
        db.execute(soft_delete_query, {"customization_id": customization_id})
        db.commit()
        
        logger.info(f"Customization {customization_id} ({customization_result[1]}) soft deleted by GP {current_user.email}")
        
        return {
            "message": f"Customization '{customization_result[1]}' deleted successfully",
            "customization_id": customization_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting customization {customization_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete customization"
        )

@router.get("/template-status", response_model=Dict[str, Any])
async def get_template_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current template status for migration planning (GP only)"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can view template status"
            )
        
        # Get all active templates
        query = text("""
        SELECT id, name, is_default, is_active, healthcare_sector_id
        FROM analysis_templates
        WHERE is_active = TRUE
        ORDER BY is_default DESC, name
        """)
        
        result = db.execute(query).fetchall()
        
        default_templates = []
        regular_templates = []
        
        for row in result:
            template_data = {
                "id": row[0],
                "name": row[1],
                "is_default": row[2],
                "healthcare_sector_id": row[4]
            }
            
            if row[2]:  # is_default
                default_templates.append(template_data)
            else:
                regular_templates.append(template_data)
        
        # Find Standard Seven-Chapter Review
        standard_template = None
        for template in (default_templates + regular_templates):
            if "standard seven-chapter review" in template["name"].lower():
                standard_template = template
                break
        
        return {
            "total_templates": len(result),
            "default_templates": default_templates,
            "regular_templates": regular_templates,
            "default_count": len(default_templates),
            "regular_count": len(regular_templates),
            "standard_template": standard_template,
            "migration_preview": {
                "templates_to_convert": len(default_templates),
                "will_remain_default": 0 if not standard_template or not standard_template["is_default"] else 1,
                "message": f"All {len(default_templates)} default templates will become editable/deletable"
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting template status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve template status"
        )

@router.post("/migrate-templates", response_model=Dict[str, Any])
async def migrate_template_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Convert all default templates to regular templates (GP only)"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can migrate templates"
            )
        
        # Get current default templates
        query = text("""
        SELECT id, name, healthcare_sector_id
        FROM analysis_templates
        WHERE is_active = TRUE AND is_default = TRUE
        ORDER BY name
        """)
        
        default_templates = db.execute(query).fetchall()
        
        if not default_templates:
            return {
                "message": "No default templates found to convert",
                "converted_count": 0,
                "templates_converted": []
            }
        
        # Convert all default templates to regular
        template_ids = [row[0] for row in default_templates]
        
        update_query = text("""
        UPDATE analysis_templates 
        SET is_default = FALSE 
        WHERE id = ANY(:template_ids) AND is_active = TRUE
        """)
        
        db.execute(update_query, {"template_ids": template_ids})
        
        # Get the count of updated rows
        updated_count = len(template_ids)
        
        # Prepare response data
        converted_templates = []
        for row in default_templates:
            converted_templates.append({
                "id": row[0],
                "name": row[1],
                "healthcare_sector_id": row[2],
                "old_status": "default",
                "new_status": "regular"
            })
        
        db.commit()
        
        logger.info(f"Migrated {updated_count} templates from default to regular by GP {current_user.email}")
        
        return {
            "message": f"Successfully converted {updated_count} templates to regular (editable/deletable)",
            "converted_count": updated_count,
            "templates_converted": converted_templates,
            "note": "All templates are now editable and deletable by GPs. Startup classifier will use fallback logic."
        }
        
    except Exception as e:
        logger.error(f"Error migrating templates: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to migrate templates"
        )

@router.post("/templates/{template_id}/chapters", response_model=Dict[str, Any])
async def add_chapter_to_template(
    template_id: int,
    chapter_data: Dict[str, Any],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Add a new chapter to a template"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can add chapters to templates"
            )
        
        # Check if template exists and is editable
        template_check_query = text("""
        SELECT id, name, is_default 
        FROM analysis_templates 
        WHERE id = :template_id AND is_active = TRUE
        """)
        
        template_result = db.execute(template_check_query, {"template_id": template_id}).fetchone()
        
        if not template_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {template_id} not found"
            )
        
        # Prevent adding chapters to default templates
        if template_result[2]:  # is_default
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot add chapters to default templates"
            )
        
        # Get the highest order_index for this template
        max_order_query = text("""
        SELECT COALESCE(MAX(order_index), 0) as max_order
        FROM template_chapters
        WHERE template_id = :template_id OR analysis_template_id = :template_id
        """)
        
        max_order_result = db.execute(max_order_query, {"template_id": template_id}).fetchone()
        next_order = (max_order_result[0] or 0) + 1
        
        # Create chapter_id from name (lowercase, replace spaces with underscores)
        chapter_name = chapter_data.get("name", "").strip()
        if not chapter_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chapter name is required"
            )
        
        chapter_id = chapter_name.lower().replace(" ", "_").replace("-", "_")
        # Remove any non-alphanumeric characters except underscores
        import re
        chapter_id = re.sub(r'[^a-z0-9_]', '', chapter_id)
        
        # Insert the new chapter
        insert_query = text("""
        INSERT INTO template_chapters (
            template_id, analysis_template_id, chapter_id, name, description, 
            weight, order_index, is_required, enabled
        ) VALUES (
            :template_id, :template_id, :chapter_id, :name, :description,
            :weight, :order_index, :is_required, :enabled
        )
        """)
        
        db.execute(insert_query, {
            "template_id": template_id,
            "chapter_id": chapter_id,
            "name": chapter_name,
            "description": chapter_data.get("description", ""),
            "weight": chapter_data.get("weight", 1.0),
            "order_index": next_order,
            "is_required": chapter_data.get("is_required", True),
            "enabled": chapter_data.get("enabled", True)
        })
        
        db.commit()
        
        logger.info(f"Added chapter '{chapter_name}' to template {template_id} by GP {current_user.email}")
        
        return {
            "message": f"Chapter '{chapter_name}' added successfully",
            "chapter_id": chapter_id,
            "order_index": next_order
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding chapter to template {template_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add chapter"
        )

@router.get("/performance-metrics", response_model=Dict[str, Any])
async def get_performance_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get performance metrics for templates and classifications"""
    try:
        # Template performance metrics
        template_performance_query = text("""
        SELECT t.name, COUNT(tp.id) as usage_count, 
               AVG(tp.average_confidence) as avg_confidence,
               AVG(tp.gp_rating) as avg_rating
        FROM analysis_templates t
        LEFT JOIN template_performance tp ON t.id = tp.template_id
        WHERE t.is_active = TRUE
        GROUP BY t.id, t.name
        ORDER BY usage_count DESC
        """)
        
        template_result = db.execute(template_performance_query).fetchall()
        
        # Classification accuracy metrics
        classification_accuracy_query = text("""
        SELECT COUNT(*) as total_classifications,
               SUM(CASE WHEN was_accurate = TRUE THEN 1 ELSE 0 END) as accurate_classifications,
               SUM(CASE WHEN was_accurate = FALSE THEN 1 ELSE 0 END) as inaccurate_classifications
        FROM classification_performance
        """)
        
        accuracy_result = db.execute(classification_accuracy_query).fetchone()
        
        # Sector distribution
        sector_distribution_query = text("""
        SELECT s.display_name, COUNT(sc.id) as classification_count
        FROM healthcare_sectors s
        LEFT JOIN startup_classifications sc ON s.id = sc.primary_sector_id
        GROUP BY s.id, s.display_name
        ORDER BY classification_count DESC
        """)
        
        sector_result = db.execute(sector_distribution_query).fetchall()
        
        return {
            "template_performance": [
                {
                    "template_name": row[0] or "Unknown Template",
                    "usage_count": int(row[1] or 0),
                    "avg_confidence": float(row[2] or 0.0),
                    "avg_rating": float(row[3] or 0.0)
                }
                for row in template_result
            ],
            "classification_accuracy": {
                "total_classifications": int(accuracy_result[0] or 0),
                "accurate_classifications": int(accuracy_result[1] or 0),
                "inaccurate_classifications": int(accuracy_result[2] or 0),
                "accuracy_percentage": float((accuracy_result[1] or 0) / (accuracy_result[0] or 1) * 100) if (accuracy_result[0] or 0) > 0 else 0.0
            },
            "sector_distribution": [
                {
                    "sector_name": row[0] or "Unknown Sector",
                    "classification_count": int(row[1] or 0)
                }
                for row in sector_result
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve performance metrics"
        )

class TemplateQuestionData(BaseModel):
    question_text: str
    scoring_criteria: str = ""
    weight: float = 1.0
    order_index: int = 0

class TemplateChapterData(BaseModel):
    name: str
    description: str = ""
    weight: float = 1.0
    is_required: bool = True
    enabled: bool = True
    order_index: int = 0
    questions: List[TemplateQuestionData] = []

class CompleteTemplateData(BaseModel):
    name: str
    description: str = ""
    chapters: List[TemplateChapterData] = []

@router.put("/templates/{template_id}/complete")
async def update_template_complete(
    template_id: int,
    template_data: CompleteTemplateData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a template with all its chapters and questions in one atomic operation"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can update templates"
            )
        
        # Check if template exists and is active
        template_check_query = text("""
        SELECT id, name, is_default 
        FROM analysis_templates 
        WHERE id = :template_id AND is_active = TRUE
        """)
        
        template_result = db.execute(template_check_query, {"template_id": template_id}).fetchone()
        
        if not template_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template {template_id} not found"
            )
        
        # Update template basic info
        update_template_query = text("""
        UPDATE analysis_templates 
        SET name = :name, description = :description
        WHERE id = :template_id
        """)
        
        db.execute(update_template_query, {
            "template_id": template_id,
            "name": template_data.name,
            "description": template_data.description
        })
        
        # Delete existing chapters and questions (cascade will handle questions)
        delete_chapters_query = text("""
        DELETE FROM chapter_questions 
        WHERE chapter_id IN (
            SELECT id FROM template_chapters 
            WHERE template_id = :template_id
        )
        """)
        db.execute(delete_chapters_query, {"template_id": template_id})
        
        delete_template_chapters_query = text("""
        DELETE FROM template_chapters 
        WHERE template_id = :template_id
        """)
        db.execute(delete_template_chapters_query, {"template_id": template_id})
        
        # Insert new chapters and questions
        for chapter_idx, chapter in enumerate(template_data.chapters):
            # Insert chapter
            insert_chapter_query = text("""
            INSERT INTO template_chapters (
                template_id, chapter_id, name, description, 
                weight, is_required, enabled, order_index
            ) VALUES (
                :template_id, :chapter_id, :name, :description,
                :weight, :is_required, :enabled, :order_index
            ) RETURNING id
            """)
            
            chapter_result = db.execute(insert_chapter_query, {
                "template_id": template_id,
                "chapter_id": f"chapter_{chapter_idx + 1}",
                "name": chapter.name,
                "description": chapter.description,
                "weight": chapter.weight,
                "is_required": chapter.is_required,
                "enabled": chapter.enabled,
                "order_index": chapter.order_index or chapter_idx
            }).fetchone()
            
            chapter_db_id = chapter_result[0]
            
            # Insert questions for this chapter
            for question_idx, question in enumerate(chapter.questions):
                insert_question_query = text("""
                INSERT INTO chapter_questions (
                    chapter_id, question_id, question_text, scoring_criteria, 
                    weight, order_index, enabled
                ) VALUES (
                    :chapter_id, :question_id, :question_text, :scoring_criteria,
                    :weight, :order_index, :enabled
                )
                """)
                
                db.execute(insert_question_query, {
                    "chapter_id": chapter_db_id,
                    "question_id": f"question_{question_idx + 1}",
                    "question_text": question.question_text,
                    "scoring_criteria": question.scoring_criteria,
                    "weight": question.weight,
                    "order_index": question.order_index or question_idx,
                    "enabled": True
                })
        
        db.commit()
        
        logger.info(f"Template {template_id} completely updated by GP {current_user.email} with {len(template_data.chapters)} chapters")
        
        return {
            "message": f"Template '{template_data.name}' updated successfully",
            "template_id": template_id,
            "chapters_count": len(template_data.chapters),
            "questions_count": sum(len(ch.questions) for ch in template_data.chapters)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating complete template {template_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update template with chapters and questions"
        )