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
    template_version: str
    specialized_analysis: List[str]
    is_active: bool
    is_default: bool
    usage_count: int

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
    """Get all healthcare sectors"""
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

@router.get("/sectors/{sector_id}/templates", response_model=List[AnalysisTemplateResponse])
async def get_sector_templates(
    sector_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all analysis templates for a specific healthcare sector"""
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
    """Get detailed template information including chapters and questions"""
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