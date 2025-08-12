"""
Project Stages API Endpoints
Handles funding process stage management and progression tracking
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import json
import logging

from ..db.database import get_db
from ..db.models import User
from .auth import get_current_user
from ..core.access_control import check_project_access  # Use centralized access control

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/project-stages", tags=["project-stages"])

# Pydantic models for API requests/responses
class ProjectStageResponse(BaseModel):
    id: int
    project_id: int
    stage_name: str
    stage_order: int
    status: str
    stage_metadata: Dict[str, Any] = {}
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

class CreateStageRequest(BaseModel):
    stage_name: str
    stage_order: int
    stage_metadata: Optional[Dict[str, Any]] = {}

class UpdateStageRequest(BaseModel):
    stage_name: Optional[str] = None
    stage_order: Optional[int] = None
    status: Optional[str] = None  # pending, active, completed, skipped
    stage_metadata: Optional[Dict[str, Any]] = None

class StageProgressRequest(BaseModel):
    status: str  # active, completed, skipped
    completion_notes: Optional[str] = None

# REMOVED: Old check_project_access function that used company_id matching
# Now using centralized access control from ..core.access_control

@router.get("/projects/{project_id}/stages", response_model=List[ProjectStageResponse])
async def get_project_stages(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all stages for a specific project"""
    try:
        # Check access permissions
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get project stages
        query = text("""
        SELECT id, project_id, stage_name, stage_order, status, stage_metadata,
               started_at, completed_at, created_at
        FROM project_stages
        WHERE project_id = :project_id
        ORDER BY stage_order, created_at
        """)
        
        results = db.execute(query, {"project_id": project_id}).fetchall()
        
        stages = []
        for row in results:
            stages.append(ProjectStageResponse(
                id=row[0],
                project_id=row[1],
                stage_name=row[2],
                stage_order=row[3],
                status=row[4],
                stage_metadata=json.loads(row[5]) if row[5] else {},
                started_at=row[6],
                completed_at=row[7],
                created_at=row[8]
            ))
        
        return stages
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stages for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project stages"
        )

@router.post("/projects/{project_id}/stages", response_model=ProjectStageResponse)
async def create_project_stage(
    project_id: int,
    request: CreateStageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new stage for a project (GP only)"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can create project stages"
            )
        
        # Check access permissions
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Check if project exists
        project_query = text("SELECT id FROM projects WHERE id = :project_id AND is_active = TRUE")
        project_result = db.execute(project_query, {"project_id": project_id}).fetchone()
        
        if not project_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        # Create the stage
        insert_query = text("""
        INSERT INTO project_stages (project_id, stage_name, stage_order, status, stage_metadata, created_at)
        VALUES (:project_id, :stage_name, :stage_order, 'pending', :stage_metadata, CURRENT_TIMESTAMP)
        RETURNING id, created_at
        """)
        
        result = db.execute(insert_query, {
            "project_id": project_id,
            "stage_name": request.stage_name,
            "stage_order": request.stage_order,
            "stage_metadata": json.dumps(request.stage_metadata or {})
        })
        
        stage_data = result.fetchone()
        stage_id = stage_data[0]
        db.commit()
        
        logger.info(f"Created stage {stage_id} for project {project_id} by {current_user.email}")
        
        return ProjectStageResponse(
            id=stage_id,
            project_id=project_id,
            stage_name=request.stage_name,
            stage_order=request.stage_order,
            status="pending",
            stage_metadata=request.stage_metadata or {},
            started_at=None,
            completed_at=None,
            created_at=stage_data[1]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating stage for project {project_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project stage"
        )

@router.put("/projects/{project_id}/stages/{stage_id}", response_model=ProjectStageResponse)
async def update_project_stage(
    project_id: int,
    stage_id: int,
    request: UpdateStageRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a project stage (GP only)"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can update project stages"
            )
        
        # Check access permissions
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Check if stage exists and belongs to the project
        stage_check_query = text("""
        SELECT id, stage_name, stage_order, status, stage_metadata, started_at, completed_at, created_at
        FROM project_stages
        WHERE id = :stage_id AND project_id = :project_id
        """)
        
        stage_result = db.execute(stage_check_query, {
            "stage_id": stage_id,
            "project_id": project_id
        }).fetchone()
        
        if not stage_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stage {stage_id} not found in project {project_id}"
            )
        
        # Build update query dynamically
        update_fields = []
        params = {"stage_id": stage_id, "project_id": project_id}
        
        if request.stage_name is not None:
            update_fields.append("stage_name = :stage_name")
            params["stage_name"] = request.stage_name
            
        if request.stage_order is not None:
            update_fields.append("stage_order = :stage_order")
            params["stage_order"] = request.stage_order
            
        if request.status is not None:
            update_fields.append("status = :status")
            params["status"] = request.status
            
            # Handle timestamp updates based on status
            if request.status == "active" and not stage_result[5]:  # started_at is None
                update_fields.append("started_at = CURRENT_TIMESTAMP")
            elif request.status == "completed" and not stage_result[6]:  # completed_at is None
                update_fields.append("completed_at = CURRENT_TIMESTAMP")
            
        if request.stage_metadata is not None:
            update_fields.append("stage_metadata = :stage_metadata")
            params["stage_metadata"] = json.dumps(request.stage_metadata)
        
        if not update_fields:
            # No fields to update, return current stage
            return ProjectStageResponse(
                id=stage_result[0],
                project_id=project_id,
                stage_name=stage_result[1],
                stage_order=stage_result[2],
                status=stage_result[3],
                stage_metadata=json.loads(stage_result[4]) if stage_result[4] else {},
                started_at=stage_result[5],
                completed_at=stage_result[6],
                created_at=stage_result[7]
            )
        
        update_query = text(f"""
        UPDATE project_stages 
        SET {', '.join(update_fields)}
        WHERE id = :stage_id AND project_id = :project_id
        RETURNING stage_name, stage_order, status, stage_metadata, started_at, completed_at, created_at
        """)
        
        result = db.execute(update_query, params)
        updated_stage = result.fetchone()
        db.commit()
        
        logger.info(f"Updated stage {stage_id} for project {project_id} by {current_user.email}")
        
        return ProjectStageResponse(
            id=stage_id,
            project_id=project_id,
            stage_name=updated_stage[0],
            stage_order=updated_stage[1],
            status=updated_stage[2],
            stage_metadata=json.loads(updated_stage[3]) if updated_stage[3] else {},
            started_at=updated_stage[4],
            completed_at=updated_stage[5],
            created_at=updated_stage[6]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating stage {stage_id} for project {project_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project stage"
        )

@router.post("/projects/{project_id}/stages/{stage_id}/progress")
async def update_stage_progress(
    project_id: int,
    stage_id: int,
    request: StageProgressRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update stage progress (GP only)"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can update stage progress"
            )
        
        # Use the existing update stage endpoint with progress-specific logic
        update_request = UpdateStageRequest(
            status=request.status,
            stage_metadata={
                "completion_notes": request.completion_notes,
                "updated_by": current_user.email,
                "updated_at": datetime.utcnow().isoformat()
            } if request.completion_notes else {
                "updated_by": current_user.email,
                "updated_at": datetime.utcnow().isoformat()
            }
        )
        
        return await update_project_stage(project_id, stage_id, update_request, db, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating progress for stage {stage_id} in project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update stage progress"
        )

@router.delete("/projects/{project_id}/stages/{stage_id}")
async def delete_project_stage(
    project_id: int,
    stage_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a project stage (GP only)"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can delete project stages"
            )
        
        # Check access permissions
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Check if stage exists and belongs to the project
        stage_check_query = text("""
        SELECT stage_name FROM project_stages
        WHERE id = :stage_id AND project_id = :project_id
        """)
        
        stage_result = db.execute(stage_check_query, {
            "stage_id": stage_id,
            "project_id": project_id
        }).fetchone()
        
        if not stage_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Stage {stage_id} not found in project {project_id}"
            )
        
        stage_name = stage_result[0]
        
        # Delete the stage
        delete_query = text("""
        DELETE FROM project_stages
        WHERE id = :stage_id AND project_id = :project_id
        """)
        
        db.execute(delete_query, {"stage_id": stage_id, "project_id": project_id})
        db.commit()
        
        logger.info(f"Deleted stage {stage_id} ({stage_name}) from project {project_id} by {current_user.email}")
        
        return {"message": f"Stage '{stage_name}' deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting stage {stage_id} from project {project_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project stage"
        )