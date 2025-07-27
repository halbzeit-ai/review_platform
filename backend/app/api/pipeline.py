"""
Pipeline Configuration API Endpoints
Handles configurable processing prompts and settings
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import json
import logging

from ..db.database import get_db
from ..db.models import User
from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["pipeline"])

# Pydantic models for API requests/responses
class PipelinePromptResponse(BaseModel):
    id: int
    stage_name: str
    prompt_text: str
    is_active: bool
    created_by: Optional[str] = None
    created_at: str
    updated_at: str

class PipelinePromptUpdateRequest(BaseModel):
    prompt_text: str = Field(..., min_length=10, max_length=5000)

class PipelinePromptListResponse(BaseModel):
    prompts: Dict[str, str]  # stage_name -> prompt_text mapping

@router.get("/prompts", response_model=PipelinePromptListResponse)
async def get_all_prompts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all active pipeline prompts"""
    try:
        # Only GPs can access pipeline configuration
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can access pipeline configuration"
            )
        
        query = text("""
        SELECT stage_name, prompt_text 
        FROM pipeline_prompts 
        WHERE is_active = TRUE 
        ORDER BY stage_name
        """)
        
        result = db.execute(query).fetchall()
        
        prompts = {}
        for row in result:
            prompts[row[0]] = row[1]
        
        return PipelinePromptListResponse(prompts=prompts)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pipeline prompts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve pipeline prompts"
        )

@router.get("/prompts/{stage_name}", response_model=PipelinePromptResponse)
async def get_prompt_by_stage(
    stage_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get prompt for a specific pipeline stage"""
    try:
        # Only GPs can access pipeline configuration
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can access pipeline configuration"
            )
        
        query = text("""
        SELECT id, stage_name, prompt_text, is_active, created_by, created_at, updated_at
        FROM pipeline_prompts 
        WHERE stage_name = :stage_name AND is_active = TRUE 
        LIMIT 1
        """)
        
        result = db.execute(query, {"stage_name": stage_name}).fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active prompt found for stage '{stage_name}'"
            )
        
        return PipelinePromptResponse(
            id=result[0],
            stage_name=result[1],
            prompt_text=result[2],
            is_active=result[3],
            created_by=result[4],
            created_at=result[5],
            updated_at=result[6]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting prompt for stage {stage_name}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve prompt for stage '{stage_name}'"
        )

@router.put("/prompts/{stage_name}")
async def update_prompt_by_stage(
    stage_name: str,
    request: PipelinePromptUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update prompt for a specific pipeline stage"""
    try:
        # Only GPs can modify pipeline configuration
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can modify pipeline configuration"
            )
        
        # Check if prompt exists
        check_query = text("""
        SELECT id FROM pipeline_prompts 
        WHERE stage_name = :stage_name AND is_active = TRUE 
        LIMIT 1
        """)
        
        existing = db.execute(check_query, {"stage_name": stage_name}).fetchone()
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active prompt found for stage '{stage_name}'"
            )
        
        # Update the prompt
        update_query = text("""
        UPDATE pipeline_prompts 
        SET prompt_text = :prompt_text, updated_at = CURRENT_TIMESTAMP 
        WHERE stage_name = :stage_name AND is_active = TRUE
        """)
        
        db.execute(update_query, {
            "prompt_text": request.prompt_text,
            "stage_name": stage_name
        })
        
        db.commit()
        
        logger.info(f"Updated prompt for stage '{stage_name}' by user {current_user.email}")
        
        return {
            "message": f"Successfully updated prompt for stage '{stage_name}'",
            "stage_name": stage_name,
            "updated_by": current_user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating prompt for stage {stage_name}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update prompt for stage '{stage_name}'"
        )

@router.post("/prompts/{stage_name}/reset")
async def reset_prompt_to_default(
    stage_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reset prompt to system default"""
    try:
        # Only GPs can modify pipeline configuration
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can modify pipeline configuration"
            )
        
        # Default prompts mapping
        default_prompts = {
            "image_analysis": "Describe this image and make sure to include anything notable about it (include text you see in the image):",
            "company_offering": "You are an analyst working at a Venture Capital company. Here is the descriptions of a startup's pitchdeck. Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company.",
            "role_definition": "You are an analyst working at a Venture Capital company. Here is the descriptions of a startup's pitchdeck.",
            "offering_extraction": "Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company.",
            "startup_name_extraction": "Please find the name of the startup in the pitchdeck. Deliver only the name, no conversational text around it.",
            "funding_amount_extraction": "Find the exact funding amount the startup is seeking or has raised from this pitch deck. Look for phrases like 'seeking $X', 'raising $X', 'funding round of $X', or similar. Return only the numerical amount with currency symbol (e.g., '$2.5M', '€500K', '$10 million'). If no specific amount is mentioned, return 'Not specified'.",
            "deck_date_extraction": "Find the date when this pitch deck was created or last updated. Look for dates on slides, footers, headers, or any text mentioning when the deck was prepared. Common formats include 'March 2024', '2024-03-15', 'Q1 2024', 'Spring 2024', etc. Return only the date in a clear format (e.g., 'March 2024', '2024-03-15', 'Q1 2024'). If no date is found, return 'Date not specified'.",
            "question_analysis": "Your task is to find answers to the following questions: ",
            "scoring_analysis": "Your task is to give a score between 0 and 7 based on how much information is provided for the following questions. Just give a number, no explanations.",
            "scientific_hypothesis": "You are a medical doctor reviewing a pitchdeck of a health startup. Provide a numbered list of core scientific, health related or medical hypothesis that are addressed by the startup. Do not report market size or any other economic hypotheses. Do not mention the name of the product or the company."
        }
        
        if stage_name not in default_prompts:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No default prompt available for stage '{stage_name}'"
            )
        
        # Reset to default
        update_query = text("""
        UPDATE pipeline_prompts 
        SET prompt_text = :prompt_text, updated_at = CURRENT_TIMESTAMP 
        WHERE stage_name = :stage_name AND is_active = TRUE
        """)
        
        db.execute(update_query, {
            "prompt_text": default_prompts[stage_name],
            "stage_name": stage_name
        })
        
        db.commit()
        
        logger.info(f"Reset prompt for stage '{stage_name}' to default by user {current_user.email}")
        
        return {
            "message": f"Successfully reset prompt for stage '{stage_name}' to default",
            "stage_name": stage_name,
            "default_prompt": default_prompts[stage_name],
            "reset_by": current_user.email
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting prompt for stage {stage_name}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset prompt for stage '{stage_name}'"
        )

@router.get("/stages")
async def get_available_stages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get list of available pipeline stages"""
    try:
        # Only GPs can access pipeline configuration
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can access pipeline configuration"
            )
        
        query = text("""
        SELECT DISTINCT stage_name 
        FROM pipeline_prompts 
        WHERE is_active = TRUE 
        ORDER BY stage_name
        """)
        
        result = db.execute(query).fetchall()
        
        stages = [row[0] for row in result]
        
        return {
            "stages": stages,
            "total_count": len(stages)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting available stages: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available stages"
        )