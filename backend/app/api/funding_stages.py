"""
Funding Stages Management API
Handles stage templates, project stage progression, and visual journey tracking
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json
import logging

from ..db.database import get_db
from ..db.models import User
from .auth import get_current_user
from ..core.access_control import check_project_access

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/funding-stages", tags=["funding-stages"])

# Pydantic models for API requests/responses
class StageTemplateResponse(BaseModel):
    id: int
    stage_name: str
    stage_code: str
    description: str
    stage_order: int
    is_required: bool
    estimated_duration_days: Optional[int] = None
    stage_metadata: Dict[str, Any] = {}
    is_active: bool

class ProjectStageResponse(BaseModel):
    id: int
    project_id: int
    stage_template_id: Optional[int] = None
    stage_name: str
    stage_code: Optional[str] = None
    stage_order: int
    status: str  # pending, active, completed, skipped
    stage_metadata: Dict[str, Any] = {}
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    estimated_completion: Optional[datetime] = None

class ProjectJourneyResponse(BaseModel):
    project_id: int
    company_id: str
    project_name: str
    funding_round: Optional[str] = None
    total_stages: int
    completed_stages: int
    active_stages: int
    pending_stages: int
    completion_percentage: float
    current_stage_name: Optional[str] = None
    current_stage_order: Optional[int] = None
    stages: List[ProjectStageResponse]
    estimated_completion_date: Optional[datetime] = None

class UpdateStageStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(pending|active|completed|skipped)$")
    completion_notes: Optional[str] = None
    stage_metadata: Optional[Dict[str, Any]] = None

class CreateStageTemplateRequest(BaseModel):
    stage_name: str
    stage_code: str
    description: Optional[str] = None
    stage_order: int
    is_required: bool = True
    estimated_duration_days: Optional[int] = None
    stage_metadata: Optional[Dict[str, Any]] = {}

# Legacy function removed - now using unified access control from core.access_control

# Stage Templates Management (GP only)
@router.get("/templates", response_model=List[StageTemplateResponse])
async def get_stage_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all stage templates"""
    try:
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can view stage templates"
            )
        
        query = text("""
        SELECT id, stage_name, stage_code, description, stage_order, is_required,
               estimated_duration_days, stage_metadata, is_active
        FROM stage_templates
        WHERE is_active = TRUE
        ORDER BY stage_order
        """)
        
        results = db.execute(query).fetchall()
        
        templates = []
        for row in results:
            templates.append(StageTemplateResponse(
                id=row[0],
                stage_name=row[1],
                stage_code=row[2],
                description=row[3] or "",
                stage_order=row[4],
                is_required=row[5],
                estimated_duration_days=row[6],
                stage_metadata=row[7] if isinstance(row[7], dict) else (json.loads(row[7]) if row[7] else {}),
                is_active=row[8]
            ))
        
        return templates
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stage templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve stage templates"
        )

@router.post("/templates", response_model=StageTemplateResponse)
async def create_stage_template(
    request: CreateStageTemplateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new stage template (GP only)"""
    try:
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can create stage templates"
            )
        
        # Check if stage_code already exists
        existing_query = text("SELECT id FROM stage_templates WHERE stage_code = :stage_code")
        existing = db.execute(existing_query, {"stage_code": request.stage_code}).fetchone()
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Stage code '{request.stage_code}' already exists"
            )
        
        # Create the template
        insert_query = text("""
        INSERT INTO stage_templates (
            stage_name, stage_code, description, stage_order, is_required,
            estimated_duration_days, stage_metadata, created_at, updated_at
        )
        VALUES (:stage_name, :stage_code, :description, :stage_order, :is_required,
                :estimated_duration_days, :stage_metadata, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id, created_at
        """)
        
        result = db.execute(insert_query, {
            "stage_name": request.stage_name,
            "stage_code": request.stage_code,
            "description": request.description,
            "stage_order": request.stage_order,
            "is_required": request.is_required,
            "estimated_duration_days": request.estimated_duration_days,
            "stage_metadata": json.dumps(request.stage_metadata or {})
        })
        
        template_data = result.fetchone()
        template_id = template_data[0]
        db.commit()
        
        logger.info(f"Created stage template {template_id} by {current_user.email}")
        
        return StageTemplateResponse(
            id=template_id,
            stage_name=request.stage_name,
            stage_code=request.stage_code,
            description=request.description or "",
            stage_order=request.stage_order,
            is_required=request.is_required,
            estimated_duration_days=request.estimated_duration_days,
            stage_metadata=request.stage_metadata or {},
            is_active=True
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating stage template: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create stage template"
        )

# Project Journey Management
@router.get("/projects/{project_id}/journey", response_model=ProjectJourneyResponse)
async def get_project_journey(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get complete funding journey for a project (visible to both startup and GPs)"""
    try:
        # Check access permissions
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get project info and progress
        project_query = text("""
        SELECT project_id, company_id, project_name, funding_round, total_stages,
               completed_stages, active_stages, pending_stages, completion_percentage,
               current_stage_name, current_stage_order
        FROM project_progress
        WHERE project_id = :project_id
        """)
        
        project_result = db.execute(project_query, {"project_id": project_id}).fetchone()
        
        if not project_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        # Get all stages for the project
        stages_query = text("""
        SELECT ps.id, ps.project_id, ps.stage_template_id, ps.stage_name, ps.stage_code,
               ps.stage_order, ps.status, ps.stage_metadata, ps.started_at, ps.completed_at,
               ps.created_at, st.estimated_duration_days
        FROM project_stages ps
        LEFT JOIN stage_templates st ON ps.stage_template_id = st.id
        WHERE ps.project_id = :project_id
        ORDER BY ps.stage_order
        """)
        
        stages_result = db.execute(stages_query, {"project_id": project_id}).fetchall()
        
        stages = []
        estimated_completion_date = None
        
        for row in stages_result:
            stage_id, proj_id, template_id, stage_name, stage_code, stage_order, stage_status, metadata, started_at, completed_at, created_at, est_duration = row
            
            # Calculate estimated completion for pending/active stages
            estimated_completion = None
            if stage_status in ['pending', 'active'] and est_duration:
                base_date = started_at if started_at else datetime.utcnow()
                estimated_completion = base_date + timedelta(days=est_duration)
                
                # Update overall project estimated completion (furthest stage)
                if not estimated_completion_date or estimated_completion > estimated_completion_date:
                    estimated_completion_date = estimated_completion
            
            stages.append(ProjectStageResponse(
                id=stage_id,
                project_id=proj_id,
                stage_template_id=template_id,
                stage_name=stage_name,
                stage_code=stage_code,
                stage_order=stage_order,
                status=stage_status,
                stage_metadata=metadata if isinstance(metadata, dict) else (json.loads(metadata) if metadata else {}),
                started_at=started_at,
                completed_at=completed_at,
                created_at=created_at,
                estimated_completion=estimated_completion
            ))
        
        return ProjectJourneyResponse(
            project_id=project_result[0],
            company_id=project_result[1],
            project_name=project_result[2],
            funding_round=project_result[3],
            total_stages=project_result[4] or 0,
            completed_stages=project_result[5] or 0,
            active_stages=project_result[6] or 0,
            pending_stages=project_result[7] or 0,
            completion_percentage=float(project_result[8] or 0.0),
            current_stage_name=project_result[9],
            current_stage_order=project_result[10],
            stages=stages,
            estimated_completion_date=estimated_completion_date
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project journey for {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project journey"
        )

@router.put("/projects/{project_id}/stages/{stage_id}/status")
async def update_stage_status(
    project_id: int,
    stage_id: int,
    request: UpdateStageStatusRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update stage status (GP only for now)"""
    try:
        # Check if user is GP (later we can allow startups to update certain stages)
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can update stage status"
            )
        
        # Check access permissions
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Verify stage belongs to project
        stage_check = text("""
        SELECT id, status, stage_order FROM project_stages
        WHERE id = :stage_id AND project_id = :project_id
        """)
        
        stage_result = db.execute(stage_check, {
            "stage_id": stage_id,
            "project_id": project_id
        }).fetchone()
        
        if not stage_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stage {stage_id} not found in project {project_id}"
            )
        
        current_status, stage_order = stage_result[1], stage_result[2]
        
        # Build update query
        update_parts = ["status = :status"]
        params = {
            "stage_id": stage_id,
            "project_id": project_id,
            "status": request.status
        }
        
        # Handle status-specific timestamps
        if request.status == "active" and current_status != "active":
            update_parts.append("started_at = CURRENT_TIMESTAMP")
        elif request.status == "completed" and current_status != "completed":
            update_parts.append("completed_at = CURRENT_TIMESTAMP")
        
        # Update metadata if provided
        if request.stage_metadata is not None:
            update_parts.append("stage_metadata = :stage_metadata")
            params["stage_metadata"] = json.dumps(request.stage_metadata)
        elif request.completion_notes:
            # Add completion notes to existing metadata
            existing_meta_query = text("SELECT stage_metadata FROM project_stages WHERE id = :stage_id")
            existing_meta = db.execute(existing_meta_query, {"stage_id": stage_id}).fetchone()[0]
            
            meta_dict = existing_meta if isinstance(existing_meta, dict) else (json.loads(existing_meta) if existing_meta else {})
            meta_dict["completion_notes"] = request.completion_notes
            meta_dict["updated_by"] = current_user.email
            meta_dict["updated_at"] = datetime.utcnow().isoformat()
            
            update_parts.append("stage_metadata = :stage_metadata")
            params["stage_metadata"] = json.dumps(meta_dict)
        
        # Execute update
        update_query = text(f"""
        UPDATE project_stages 
        SET {', '.join(update_parts)}
        WHERE id = :stage_id AND project_id = :project_id
        """)
        
        db.execute(update_query, params)
        
        # Auto-advance logic: if completing a stage, activate the next pending stage
        if request.status == "completed":
            next_stage_query = text("""
            UPDATE project_stages 
            SET status = 'active', started_at = CURRENT_TIMESTAMP
            WHERE project_id = :project_id 
            AND stage_order = :next_order 
            AND status = 'pending'
            """)
            
            db.execute(next_stage_query, {
                "project_id": project_id,
                "next_order": stage_order + 1
            })
        
        db.commit()
        
        logger.info(f"Updated stage {stage_id} status to {request.status} by {current_user.email}")
        
        return {"message": f"Stage status updated to {request.status}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating stage {stage_id} status: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update stage status"
        )

@router.post("/projects/{project_id}/reinitialize-stages")
async def reinitialize_project_stages(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Reinitialize project stages from current templates (GP only)"""
    try:
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can reinitialize project stages"
            )
        
        # Check access permissions
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Clear existing stages
        delete_query = text("DELETE FROM project_stages WHERE project_id = :project_id")
        db.execute(delete_query, {"project_id": project_id})
        
        # Reinitialize from templates
        init_query = text("SELECT initialize_project_stages(:project_id)")
        result = db.execute(init_query, {"project_id": project_id})
        stage_count = result.fetchone()[0]
        
        db.commit()
        
        logger.info(f"Reinitialized {stage_count} stages for project {project_id} by {current_user.email}")
        
        return {
            "message": f"Reinitialized {stage_count} stages for project",
            "stages_created": stage_count
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reinitializing stages for project {project_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reinitialize project stages"
        )