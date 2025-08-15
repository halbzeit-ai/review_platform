"""
Project Management API Endpoints
Handles multi-project funding management, document uploads, and stage progression
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
from ..core.access_control import check_project_access, check_project_access_by_company_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/project-management", tags=["project-management"])

# Pydantic models for API requests/responses
class DocumentResponse(BaseModel):
    id: int
    file_name: str
    document_type: str
    file_path: Optional[str] = None
    upload_date: datetime

class ProjectResponse(BaseModel):
    id: int
    company_id: str
    project_name: str
    funding_round: Optional[str] = None
    current_stage_id: Optional[int] = None
    funding_sought: Optional[str] = None
    healthcare_sector_id: Optional[int] = None
    company_offering: Optional[str] = None
    project_metadata: Dict[str, Any] = {}
    is_active: bool
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    interaction_count: int = 0
    documents: List[DocumentResponse] = []

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

class ProjectDocumentResponse(BaseModel):
    id: int
    project_id: int
    document_type: str
    file_name: str
    file_path: str
    original_filename: Optional[str] = None
    file_size: Optional[int] = None
    processing_status: str
    upload_date: datetime
    uploaded_by: int
    uploader_name: Optional[str] = None
    analysis_completed: bool = False

class ProjectInteractionResponse(BaseModel):
    id: int
    project_id: int
    interaction_type: str
    title: Optional[str] = None
    content: str
    document_id: Optional[int] = None
    created_by: int
    creator_name: Optional[str] = None
    status: str
    interaction_metadata: Dict[str, Any] = {}
    created_at: datetime
    updated_at: datetime

class CreateProjectRequest(BaseModel):
    project_name: str
    funding_round: str
    funding_sought: Optional[str] = None
    company_offering: Optional[str] = None

class UpdateProjectRequest(BaseModel):
    project_name: Optional[str] = None
    funding_round: Optional[str] = None
    funding_sought: Optional[str] = None
    company_offering: Optional[str] = None
    current_stage_id: Optional[int] = None

def get_company_id_from_user(user: User) -> str:
    """Extract company_id from user based on company name"""
    if user.company_name:
        import re
        return re.sub(r'[^a-z0-9-]', '', re.sub(r'\s+', '-', user.company_name.lower()))
    return user.email.split('@')[0]

# Legacy function removed - now using unified access control from core.access_control

# Company-level endpoints for managing multiple projects
@router.get("/companies/{company_id}/projects", response_model=List[ProjectResponse])
async def get_company_projects(
    company_id: str,
    include_test_data: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all projects for a specific company"""
    try:
        # Check access permissions
        if current_user.role == "startup" and get_company_id_from_user(current_user) != company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this company's projects"
            )
        
        # Build query with optional test data filtering
        base_query = """
        SELECT p.id, p.company_id, p.project_name, p.funding_round, p.current_stage_id,
               p.funding_sought, p.healthcare_sector_id, p.company_offering, 
               p.project_metadata, p.is_active, p.created_at, p.updated_at,
               COUNT(DISTINCT pd.id) as document_count,
               COUNT(DISTINCT pi.id) as interaction_count
        FROM projects p
        LEFT JOIN project_documents pd ON p.id = pd.project_id AND pd.is_active = TRUE
        LEFT JOIN project_interactions pi ON p.id = pi.project_id AND pi.status = 'active'
        WHERE p.company_id = :company_id AND p.is_active = TRUE
        """
        
        # Add test data filtering for GPs
        if current_user.role == "gp" and not include_test_data:
            base_query += " AND (p.is_test = FALSE OR p.is_test IS NULL)"
        
        base_query += """
        GROUP BY p.id, p.company_id, p.project_name, p.funding_round, p.current_stage_id,
                 p.funding_sought, p.healthcare_sector_id, p.company_offering, 
                 p.project_metadata, p.is_active, p.created_at, p.updated_at
        ORDER BY p.created_at DESC
        """
        
        query = text(base_query)
        
        results = db.execute(query, {"company_id": company_id}).fetchall()
        
        projects = []
        for row in results:
            projects.append(ProjectResponse(
                id=row[0],
                company_id=row[1],
                project_name=row[2],
                funding_round=row[3],
                current_stage_id=row[4],
                funding_sought=row[5],
                healthcare_sector_id=row[6],
                company_offering=row[7],
                project_metadata=row[8] if isinstance(row[8], dict) else (json.loads(row[8]) if row[8] else {}),
                is_active=row[9],
                created_at=row[10],
                updated_at=row[11],
                document_count=row[12] or 0,
                interaction_count=row[13] or 0
            ))
        
        return projects
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting projects for company {company_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve company projects"
        )

@router.post("/companies/{company_id}/projects", response_model=ProjectResponse)
async def create_project(
    company_id: str,
    request: CreateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new project for a company"""
    try:
        # Check access permissions
        if current_user.role == "startup" and get_company_id_from_user(current_user) != company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only create projects for your own company"
            )
        
        # Create the project
        insert_query = text("""
        INSERT INTO projects (company_id, project_name, funding_round, funding_sought, 
                             company_offering, project_metadata, created_at, updated_at)
        VALUES (:company_id, :project_name, :funding_round, :funding_sought, 
                :company_offering, :project_metadata, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        RETURNING id, created_at, updated_at
        """)
        
        result = db.execute(insert_query, {
            "company_id": company_id,
            "project_name": request.project_name,
            "funding_round": request.funding_round,
            "funding_sought": request.funding_sought,
            "company_offering": request.company_offering,
            "project_metadata": json.dumps({"created_by": current_user.email})
        })
        
        project_data = result.fetchone()
        project_id = project_data[0]
        db.commit()
        
        logger.info(f"Created project {project_id} for company {company_id} by {current_user.email}")
        
        return ProjectResponse(
            id=project_id,
            company_id=company_id,
            project_name=request.project_name,
            funding_round=request.funding_round,
            current_stage_id=None,
            funding_sought=request.funding_sought,
            healthcare_sector_id=None,
            company_offering=request.company_offering,
            project_metadata={"created_by": current_user.email},
            is_active=True,
            created_at=project_data[1],
            updated_at=project_data[2],
            document_count=0,
            interaction_count=0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating project for company {company_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create project"
        )

# Project-specific endpoints
@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed information about a specific project"""
    try:
        # Check access permissions
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get project details with counts
        query = text("""
        SELECT p.id, p.company_id, p.project_name, p.funding_round, p.current_stage_id,
               p.funding_sought, p.healthcare_sector_id, p.company_offering, 
               p.project_metadata, p.is_active, p.created_at, p.updated_at,
               COUNT(DISTINCT pd.id) as document_count,
               COUNT(DISTINCT pi.id) as interaction_count
        FROM projects p
        LEFT JOIN project_documents pd ON p.id = pd.project_id AND pd.is_active = TRUE
        LEFT JOIN project_interactions pi ON p.id = pi.project_id AND pi.status = 'active'
        WHERE p.id = :project_id AND p.is_active = TRUE
        GROUP BY p.id, p.company_id, p.project_name, p.funding_round, p.current_stage_id,
                 p.funding_sought, p.healthcare_sector_id, p.company_offering, 
                 p.project_metadata, p.is_active, p.created_at, p.updated_at
        """)
        
        result = db.execute(query, {"project_id": project_id}).fetchone()
        
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        return ProjectResponse(
            id=result[0],
            company_id=result[1],
            project_name=result[2],
            funding_round=result[3],
            current_stage_id=result[4],
            funding_sought=result[5],
            healthcare_sector_id=result[6],
            company_offering=result[7],
            project_metadata=result[8] if isinstance(result[8], dict) else (json.loads(result[8]) if result[8] else {}),
            is_active=result[9],
            created_at=result[10],
            updated_at=result[11],
            document_count=result[12] or 0,
            interaction_count=result[13] or 0
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project"
        )

@router.put("/projects/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    request: UpdateProjectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update project information"""
    try:
        # Check access permissions
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Build update query dynamically based on provided fields
        update_fields = []
        params = {"project_id": project_id}
        
        if request.project_name is not None:
            update_fields.append("project_name = :project_name")
            params["project_name"] = request.project_name
            
        if request.funding_round is not None:
            update_fields.append("funding_round = :funding_round")
            params["funding_round"] = request.funding_round
            
        if request.funding_sought is not None:
            update_fields.append("funding_sought = :funding_sought")
            params["funding_sought"] = request.funding_sought
            
        if request.company_offering is not None:
            update_fields.append("company_offering = :company_offering")
            params["company_offering"] = request.company_offering
            
        if request.current_stage_id is not None:
            update_fields.append("current_stage_id = :current_stage_id")
            params["current_stage_id"] = request.current_stage_id
        
        if not update_fields:
            # No fields to update
            return await get_project(project_id, db, current_user)
        
        update_query = text(f"""
        UPDATE projects 
        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
        WHERE id = :project_id AND is_active = TRUE
        """)
        
        db.execute(update_query, params)
        db.commit()
        
        logger.info(f"Updated project {project_id} by {current_user.email}")
        
        # Return updated project
        return await get_project(project_id, db, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating project {project_id}: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project"
        )

@router.get("/projects/{project_id}/documents", response_model=List[ProjectDocumentResponse])
async def get_project_documents(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all documents for a specific project"""
    try:
        # Check access permissions
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get project documents
        query = text("""
        SELECT pd.id, pd.project_id, pd.document_type, pd.file_name, pd.file_path,
               pd.original_filename, pd.file_size, pd.processing_status, pd.upload_date,
               pd.uploaded_by, pd.analysis_results_path,
               u.first_name, u.last_name, u.email
        FROM project_documents pd
        JOIN users u ON pd.uploaded_by = u.id
        WHERE pd.project_id = :project_id AND pd.is_active = TRUE
        ORDER BY pd.upload_date DESC
        """)
        
        results = db.execute(query, {"project_id": project_id}).fetchall()
        
        documents = []
        for row in results:
            uploader_name = f"{row[11] or ''} {row[12] or ''}".strip() or row[13]
            analysis_completed = bool(row[10])  # analysis_results_path exists
            
            documents.append(ProjectDocumentResponse(
                id=row[0],
                project_id=row[1],
                document_type=row[2],
                file_name=row[3],
                file_path=row[4],
                original_filename=row[5],
                file_size=row[6],
                processing_status=row[7],
                upload_date=row[8],
                uploaded_by=row[9],
                uploader_name=uploader_name,
                analysis_completed=analysis_completed
            ))
        
        return documents
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting documents for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project documents"
        )

@router.get("/projects/{project_id}/interactions", response_model=List[ProjectInteractionResponse])
async def get_project_interactions(
    project_id: int,
    interaction_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all interactions for a specific project"""
    try:
        # Check access permissions
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Build query with optional interaction type filter
        base_query = """
        SELECT pi.id, pi.project_id, pi.interaction_type, pi.title, pi.content,
               pi.document_id, pi.created_by, pi.status, pi.interaction_metadata,
               pi.created_at, pi.updated_at,
               u.first_name, u.last_name, u.email
        FROM project_interactions pi
        JOIN users u ON pi.created_by = u.id
        WHERE pi.project_id = :project_id AND pi.status = 'active'
        """
        
        params = {"project_id": project_id}
        
        if interaction_type:
            base_query += " AND pi.interaction_type = :interaction_type"
            params["interaction_type"] = interaction_type
        
        base_query += " ORDER BY pi.created_at DESC"
        
        query = text(base_query)
        results = db.execute(query, params).fetchall()
        
        interactions = []
        for row in results:
            creator_name = f"{row[11] or ''} {row[12] or ''}".strip() or row[13]
            
            interactions.append(ProjectInteractionResponse(
                id=row[0],
                project_id=row[1],
                interaction_type=row[2],
                title=row[3],
                content=row[4],
                document_id=row[5],
                created_by=row[6],
                creator_name=creator_name,
                status=row[7],
                interaction_metadata=row[8] if isinstance(row[8], dict) else (json.loads(row[8]) if row[8] else {}),
                created_at=row[9],
                updated_at=row[10]
            ))
        
        return interactions
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting interactions for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project interactions"
        )

@router.get("/all-projects", response_model=List[ProjectResponse])
async def get_all_projects(
    include_test_data: bool = False,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all projects (GP only) with optional test data filtering"""
    try:
        # Check if user is GP
        if current_user.role != "gp":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only GPs can view all projects"
            )
        
        # Build query with test data filtering
        base_query = """
        SELECT p.id, p.company_id, p.project_name, p.funding_round, p.current_stage_id,
               p.funding_sought, p.healthcare_sector_id, p.company_offering, 
               p.project_metadata, p.is_active, p.created_at, p.updated_at,
               COUNT(DISTINCT pd.id) as document_count,
               COUNT(DISTINCT pi.id) as interaction_count
        FROM projects p
        LEFT JOIN project_documents pd ON p.id = pd.project_id AND pd.is_active = TRUE
        LEFT JOIN project_interactions pi ON p.id = pi.project_id AND pi.status = 'active'
        WHERE p.is_active = TRUE
        """
        
        # Add test data filtering
        if not include_test_data:
            base_query += " AND (p.is_test = FALSE OR p.is_test IS NULL)"
        
        base_query += """
        GROUP BY p.id, p.company_id, p.project_name, p.funding_round, p.current_stage_id,
                 p.funding_sought, p.healthcare_sector_id, p.company_offering, 
                 p.project_metadata, p.is_active, p.created_at, p.updated_at
        ORDER BY p.updated_at DESC
        LIMIT :limit OFFSET :offset
        """
        
        query = text(base_query)
        results = db.execute(query, {"limit": limit, "offset": offset}).fetchall()
        
        projects = []
        for row in results:
            project_id = row[0]
            
            # Fetch documents for this project
            docs_query = text("""
                SELECT pd.id, pd.file_name, pd.document_type, pd.file_path, pd.upload_date
                FROM project_documents pd
                WHERE pd.project_id = :project_id AND pd.is_active = TRUE
                ORDER BY pd.upload_date DESC
            """)
            
            docs_results = db.execute(docs_query, {"project_id": project_id}).fetchall()
            documents = []
            for doc_row in docs_results:
                documents.append(DocumentResponse(
                    id=doc_row[0],
                    file_name=doc_row[1],
                    document_type=doc_row[2],
                    file_path=doc_row[3],
                    upload_date=doc_row[4]
                ))
            
            projects.append(ProjectResponse(
                id=project_id,
                company_id=row[1],
                project_name=row[2],
                funding_round=row[3],
                current_stage_id=row[4],
                funding_sought=row[5],
                healthcare_sector_id=row[6],
                company_offering=row[7],
                project_metadata=row[8] if isinstance(row[8], dict) else (json.loads(row[8]) if row[8] else {}),
                is_active=row[9],
                created_at=row[10],
                updated_at=row[11],
                document_count=row[12] or 0,
                interaction_count=row[13] or 0,
                documents=documents
            ))
        
        return projects
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting all projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve all projects"
        )

@router.get("/my-projects", response_model=List[ProjectResponse])
async def get_my_projects(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get projects for the current user (startup only)"""
    try:
        # Check if user is startup
        if current_user.role != "startup":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only startup users can access their projects"
            )
        
        # Build query for user's projects using project membership (modern architecture)
        # This supports the project-based system where users are explicitly added as members
        base_query = """
        SELECT p.id, p.company_id, p.project_name, p.funding_round, p.current_stage_id,
               p.funding_sought, p.healthcare_sector_id, p.company_offering, 
               p.project_metadata, p.is_active, p.created_at, p.updated_at,
               COUNT(DISTINCT pd.id) as document_count,
               COUNT(DISTINCT pi.id) as interaction_count
        FROM projects p
        INNER JOIN project_members pm ON p.id = pm.project_id
        LEFT JOIN project_documents pd ON p.id = pd.project_id AND pd.is_active = TRUE
        LEFT JOIN project_interactions pi ON p.id = pi.project_id AND pi.status = 'active'
        WHERE p.is_active = TRUE AND pm.user_id = :user_id
        GROUP BY p.id, p.company_id, p.project_name, p.funding_round, p.current_stage_id,
                 p.funding_sought, p.healthcare_sector_id, p.company_offering, 
                 p.project_metadata, p.is_active, p.created_at, p.updated_at
        ORDER BY p.updated_at DESC
        LIMIT :limit OFFSET :offset
        """
        
        query = text(base_query)
        results = db.execute(query, {
            "user_id": current_user.id,
            "limit": limit, 
            "offset": offset
        }).fetchall()
        
        projects = []
        for row in results:
            project_id = row[0]
            
            # Fetch documents for this project (same logic as all-projects endpoint)
            docs_query = text("""
                SELECT pd.id, pd.file_name, pd.document_type, pd.file_path, pd.upload_date
                FROM project_documents pd
                WHERE pd.project_id = :project_id AND pd.is_active = TRUE
                  AND pd.document_type = 'pitch_deck'
                ORDER BY pd.upload_date DESC
            """)
            
            docs_results = db.execute(docs_query, {"project_id": project_id}).fetchall()
            documents = []
            for doc_row in docs_results:
                documents.append(DocumentResponse(
                    id=doc_row[0],
                    file_name=doc_row[1],
                    document_type=doc_row[2],
                    file_path=doc_row[3],
                    upload_date=doc_row[4]
                ))
            
            projects.append(ProjectResponse(
                id=row[0],
                company_id=row[1],
                project_name=row[2],
                funding_round=row[3],
                current_stage_id=row[4],
                funding_sought=row[5],
                healthcare_sector_id=row[6],
                company_offering=row[7],
                project_metadata=row[8] if isinstance(row[8], dict) else (json.loads(row[8]) if row[8] else {}),
                is_active=row[9],
                created_at=row[10],
                updated_at=row[11],
                document_count=row[12] or 0,
                interaction_count=row[13] or 0,
                documents=documents
            ))
        
        logger.info(f"Retrieved {len(projects)} projects for user {current_user.email}")
        return projects
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting my projects for user {current_user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve your projects"
        )

@router.get("/projects/{project_id}/decks")
async def get_project_decks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get pitch decks for a specific project (GPs can access any, startups can access their own)"""
    try:
        # Get project info to verify it exists
        project_query = text("""
            SELECT id, company_id, project_name 
            FROM projects 
            WHERE id = :project_id AND is_active = TRUE
        """)
        
        project_result = db.execute(project_query, {"project_id": project_id}).fetchone()
        
        if not project_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        
        # Check access permissions using unified access control
        if not check_project_access(current_user, project_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this project"
            )
        
        # Get all project documents (pitch decks) for this project
        # Use LEFT JOIN with documents to get the correct deck ID for deck viewer
        decks_query = text("""
            SELECT 
                pd.id,
                pd.uploaded_by as user_id,
                p.company_id,
                pd.file_name,
                pd.file_path,
                (SELECT file_path FROM project_documents pd2 
                 WHERE pd2.project_id = pd.project_id 
                 AND pd2.document_type = 'analysis_results' 
                 AND pd2.is_active = TRUE 
                 LIMIT 1) as results_file_path,
                pd.processing_status,
                NULL as ai_analysis_results,
                NULL as ai_extracted_startup_name,
                'project_documents' as data_source,
                pd.upload_date as created_at,
                u.email as user_email,
                u.first_name,
                u.last_name,
                NULL as original_document_id
            FROM project_documents pd
            JOIN projects p ON pd.project_id = p.id
            LEFT JOIN users u ON pd.uploaded_by = u.id
            WHERE pd.project_id = :project_id 
            AND pd.document_type = 'pitch_deck'
            AND pd.is_active = TRUE
            ORDER BY pd.upload_date DESC
        """)
        
        decks_results = db.execute(decks_query, {"project_id": project_id}).fetchall()
        
        decks = []
        for row in decks_results:
            # Check if visual analysis is completed by multiple methods
            visual_analysis_completed = False
            deck_id = row[0]
            company_id = row[2]
            file_name = row[3]
            original_document_id = row[14] if len(row) > 14 else None
            
            if company_id and file_name:
                try:
                    deck_name = os.path.splitext(file_name)[0]
                    
                    # Method 1: Check for database-stored analysis results
                    # Check using both the new ID and original document_id if available
                    try:
                        check_ids = [str(deck_id)]
                        if original_document_id:
                            check_ids.append(str(original_document_id))
                        
                        for check_id in check_ids:
                            extraction_check = db.execute(text("""
                                SELECT 1 FROM extraction_experiments 
                                WHERE document_ids LIKE '%' || :deck_id || '%'
                                AND results_json IS NOT NULL
                                LIMIT 1
                            """), {"deck_id": check_id}).fetchone()
                            
                            if extraction_check:
                                visual_analysis_completed = True
                                logger.info(f"Visual analysis completed for document {deck_id} (checked ID: {check_id}) - found extraction experiments")
                                break
                    except Exception as e:
                        logger.error(f"Error checking extraction experiments for deck {deck_id}: {e}")
                    
                    # Method 2: Check dojo directory structure for slide images (if not found in database)
                    if not visual_analysis_completed:
                        dojo_analysis_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", "dojo", "analysis")
                        logger.info(f"Checking visual analysis for document {deck_id}: deck_name='{deck_name}', dojo_path='{dojo_analysis_path}'")
                        
                        if os.path.exists(dojo_analysis_path):
                            # Create filesystem-safe version (spaces -> underscores)
                            filesystem_deck_name = deck_name.replace(' ', '_')
                            logger.info(f"Looking for directories containing: '{deck_name}' or '{filesystem_deck_name}'")
                            
                            # Look for directories containing the deck name (with UUID prefix)
                            for dir_name in os.listdir(dojo_analysis_path):
                                # Check if directory name contains the deck name (original or filesystem-safe)
                                if (deck_name in dir_name or filesystem_deck_name in dir_name):
                                    potential_dir = os.path.join(dojo_analysis_path, dir_name)
                                    logger.info(f"Found matching directory: {dir_name}")
                                    if os.path.exists(potential_dir):
                                        # Check for slide images
                                        slide_files = [f for f in os.listdir(potential_dir) if f.startswith('slide_') and f.endswith(('.jpg', '.png'))]
                                        logger.info(f"Found {len(slide_files)} slide files in {dir_name}")
                                        if slide_files:
                                            visual_analysis_completed = True
                                            logger.info(f"Visual analysis completed for document {deck_id} - found slide images")
                                            break
                            
                            if not visual_analysis_completed:
                                logger.warning(f"No slide images found for document {deck_id} with deck_name '{deck_name}'")
                        else:
                            logger.warning(f"Dojo analysis path does not exist: {dojo_analysis_path}")
                            
                except Exception as e:
                    logger.error(f"Error checking visual analysis for document {deck_id}: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
            
            deck_data = {
                "id": row[0],
                "user_id": row[1],
                "company_id": row[2],
                "file_name": row[3],
                "file_path": row[4],
                "results_file_path": row[5],
                "processing_status": row[6],
                "ai_analysis_results": row[7],
                "ai_extracted_startup_name": row[8],
                "data_source": row[9],
                "created_at": row[10],
                "user_email": row[11],
                "user_first_name": row[12],
                "user_last_name": row[13],
                "visual_analysis_completed": visual_analysis_completed
            }
            decks.append(deck_data)
        
        return {
            "project_id": project_id,
            "project_name": project_result[2],
            "company_id": project_result[1],
            "decks": decks
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project decks for project {project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project decks"
        )

class OrphanedProjectResponse(BaseModel):
    id: int
    company_id: str
    project_name: str
    funding_round: Optional[str] = None
    deleted_user_emails: Optional[str] = None
    company_offering: Optional[str] = None
    created_at: datetime
    member_count: int = 0
    invitation_count: int = 0
    document_count: int = 0

@router.get("/orphaned-projects", response_model=List[OrphanedProjectResponse])
async def get_orphaned_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get projects that have no members and no pending invitations (GP only)"""
    if current_user.role != "gp":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only GPs can view orphaned projects"
        )
    
    try:
        query = text("""
        SELECT 
            p.id,
            p.company_id,
            p.project_name,
            p.funding_round,
            STRING_AGG(DISTINCT u_deleted.email, ', ') as deleted_user_emails,
            p.company_offering,
            p.created_at,
            COUNT(pm.id) as member_count,
            COUNT(pi.id) as invitation_count,
            COUNT(pd_doc.id) as document_count
        FROM projects p
        LEFT JOIN project_members pm ON p.id = pm.project_id
        LEFT JOIN project_invitations pi ON p.id = pi.project_id AND pi.status = 'pending'
        LEFT JOIN project_documents pd_doc ON p.id = pd_doc.project_id
        -- Look for users who uploaded documents for this project but are not members
        LEFT JOIN users u_deleted ON u_deleted.id = pd_doc.uploaded_by 
            AND u_deleted.id NOT IN (
                SELECT DISTINCT user_id FROM project_members WHERE project_id = p.id
                UNION
                SELECT DISTINCT accepted_by_id FROM project_invitations WHERE project_id = p.id AND accepted_by_id IS NOT NULL
            )
        WHERE p.is_active = TRUE
        GROUP BY p.id, p.company_id, p.project_name, p.funding_round, p.company_offering, p.created_at
        HAVING COUNT(pm.id) = 0 AND COUNT(pi.id) = 0
        ORDER BY p.created_at DESC
        """)
        
        results = db.execute(query).fetchall()
        
        orphaned_projects = []
        for row in results:
            orphaned_projects.append(OrphanedProjectResponse(
                id=row[0],
                company_id=row[1],
                project_name=row[2],
                funding_round=row[3],
                deleted_user_emails=row[4],
                company_offering=row[5],
                created_at=row[6],
                member_count=row[7],
                invitation_count=row[8],
                document_count=row[9]
            ))
        
        logger.info(f"Found {len(orphaned_projects)} orphaned projects")
        return orphaned_projects
        
    except Exception as e:
        logger.error(f"Error getting orphaned projects: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve orphaned projects"
        )


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    COMPLETELY delete a project and ALL associated data including:
    - Project documents (files on filesystem)
    - Project members and invitations
    - Project stages and progress 
    - Computed results (reviews, analysis, extraction results)
    - Associated users (startup users that only exist for this project)
    - All database references
    
    This is a DESTRUCTIVE operation that cannot be undone.
    Only GPs can perform this operation.
    """
    # Verify GP permissions
    if current_user.role != "gp":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only General Partners can delete projects"
        )
    
    try:
        # Step 1: Get project information first
        project_query = text("""
            SELECT p.id, p.company_id, p.project_name, p.is_test,
                   COUNT(pm.user_id) as member_count,
                   COUNT(pd.id) as document_count
            FROM projects p
            LEFT JOIN project_members pm ON p.id = pm.project_id
            LEFT JOIN project_documents pd ON p.id = pd.project_id
            WHERE p.id = :project_id
            GROUP BY p.id, p.company_id, p.project_name, p.is_test
        """)
        
        project_result = db.execute(project_query, {"project_id": project_id}).fetchone()
        
        if not project_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            )
        
        company_id = project_result[1]
        project_name = project_result[2]
        is_test = project_result[3]
        member_count = project_result[4]
        document_count = project_result[5]
        
        logger.info(f"Starting COMPLETE deletion of project {project_id} ({company_id} - {project_name})")
        logger.info(f"Project has {member_count} members and {document_count} documents")
        
        # Track deletion statistics
        deleted_counts = {
            "project_documents": 0,
            "project_members": 0,
            "project_invitations": 0,
            "project_stages": 0,
            "users_deleted": 0,
            "reviews_deleted": 0,
            "questions_deleted": 0,
            "documents_deleted": 0,
            "analysis_results_deleted": 0,
            "extraction_results_deleted": 0,
            "files_deleted": 0,
            "filesystem_errors": []
        }
        
        # Step 2: Delete physical files from filesystem
        try:
            # Get all document file paths for this project
            doc_files_query = text("""
                SELECT file_path, file_name 
                FROM project_documents 
                WHERE project_id = :project_id AND file_path IS NOT NULL
            """)
            
            doc_files = db.execute(doc_files_query, {"project_id": project_id}).fetchall()
            
            for file_path, file_name in doc_files:
                try:
                    full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, file_path.lstrip('/'))
                    if os.path.exists(full_path):
                        os.remove(full_path)
                        deleted_counts["files_deleted"] += 1
                        logger.info(f"Deleted file: {full_path}")
                    else:
                        logger.warning(f"File not found for deletion: {full_path}")
                        
                    # Also try to delete any associated result/thumbnail directories
                    file_base = os.path.splitext(file_name)[0]
                    results_dir = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "results", file_base)
                    if os.path.exists(results_dir):
                        shutil.rmtree(results_dir)
                        logger.info(f"Deleted results directory: {results_dir}")
                        
                except Exception as file_error:
                    logger.error(f"Error deleting file {file_path}: {file_error}")
                    deleted_counts["filesystem_errors"].append(f"Failed to delete {file_path}: {str(file_error)}")
                    
        except Exception as e:
            logger.error(f"Error during filesystem cleanup: {e}")
            deleted_counts["filesystem_errors"].append(f"Filesystem cleanup error: {str(e)}")
        
        # Step 3: Find users that should be deleted (startup users only associated with this project)
        users_to_delete_query = text("""
            SELECT DISTINCT u.id, u.email, u.role
            FROM users u
            JOIN project_members pm ON u.id = pm.user_id
            WHERE pm.project_id = :project_id 
            AND u.role = 'startup'
            AND u.id NOT IN (
                -- Don't delete users who are members of other projects
                SELECT DISTINCT pm2.user_id
                FROM project_members pm2
                WHERE pm2.project_id != :project_id
                UNION
                -- Don't delete users who have accepted invitations to other projects
                SELECT DISTINCT pi.accepted_by_id
                FROM project_invitations pi
                WHERE pi.project_id != :project_id AND pi.accepted_by_id IS NOT NULL
            )
        """)
        
        users_to_delete = db.execute(users_to_delete_query, {"project_id": project_id}).fetchall()
        
        # Step 4: Delete computed results and analysis data (with savepoints for error handling)
        
        # Helper function to execute SQL with savepoints
        def safe_execute(query, params, description):
            try:
                # Create savepoint
                savepoint_name = f"sp_{description.replace(' ', '_')}"
                db.execute(text(f"SAVEPOINT {savepoint_name}"))
                
                # Execute the query
                result = db.execute(query, params)
                
                # Release savepoint on success
                db.execute(text(f"RELEASE SAVEPOINT {savepoint_name}"))
                return result.rowcount
                
            except Exception as e:
                # Roll back to savepoint on error
                try:
                    db.execute(text(f"ROLLBACK TO SAVEPOINT {savepoint_name}"))
                    db.execute(text(f"RELEASE SAVEPOINT {savepoint_name}"))
                except:
                    pass  # Savepoint may not exist
                
                logger.warning(f"Error {description}: {e}")
                return 0
        
        # Delete extraction experiment results that reference this project's documents
        extraction_cleanup_query = text("""
            UPDATE extraction_experiments 
            SET results_json = NULL,
                classification_results_json = NULL,
                company_name_results_json = NULL,
                funding_amount_results_json = NULL,
                deck_date_results_json = NULL,
                template_processing_results_json = NULL
            WHERE document_ids && ARRAY(
                SELECT pd.id
                FROM project_documents pd 
                WHERE pd.project_id = :project_id
            )
        """)
        
        extraction_count = safe_execute(extraction_cleanup_query, {"project_id": project_id}, "cleaning extraction experiments")
        if extraction_count > 0:
            deleted_counts["extraction_results_deleted"] = extraction_count
        
        # Delete specialized analysis results 
        analysis_cleanup_query = text("""
            DELETE FROM specialized_analysis_results 
            WHERE document_id IN (
                SELECT pd.id 
                FROM project_documents pd 
                WHERE pd.project_id = :project_id
            )
        """)
        
        deleted_counts["analysis_results_deleted"] = safe_execute(
            analysis_cleanup_query, {"project_id": project_id}, "deleting specialized analysis results"
        )
        
        # Delete visual analysis cache
        visual_cache_query = text("""
            DELETE FROM visual_analysis_cache 
            WHERE document_id IN (
                SELECT pd.id 
                FROM project_documents pd 
                WHERE pd.project_id = :project_id
            )
        """)
        
        safe_execute(visual_cache_query, {"project_id": project_id}, "deleting visual analysis cache")
        
        # Delete questions and reviews for project documents
        questions_cleanup_query = text("""
            DELETE FROM questions 
            WHERE review_id IN (
                SELECT r.id FROM reviews r
                WHERE r.document_id IN (
                    SELECT pd.id 
                    FROM project_documents pd 
                    WHERE pd.project_id = :project_id
                )
            )
        """)
        
        deleted_counts["questions_deleted"] = safe_execute(
            questions_cleanup_query, {"project_id": project_id}, "deleting questions"
        )
        
        reviews_cleanup_query = text("""
            DELETE FROM reviews 
            WHERE document_id IN (
                SELECT pd.id 
                FROM project_documents pd 
                WHERE pd.project_id = :project_id
            )
        """)
        
        deleted_counts["reviews_deleted"] = safe_execute(
            reviews_cleanup_query, {"project_id": project_id}, "deleting reviews"
        )
        
        # Note: documents table no longer exists - all data is in project_documents
        deleted_counts["documents_deleted"] = 0
        
        # Step 5: Delete project-specific data (in dependency order)
        
        # Delete project documents
        delete_docs_query = text("DELETE FROM project_documents WHERE project_id = :project_id")
        deleted_counts["project_documents"] = db.execute(delete_docs_query, {"project_id": project_id}).rowcount
        
        # Delete project stages
        delete_stages_query = text("DELETE FROM project_stages WHERE project_id = :project_id")
        deleted_counts["project_stages"] = db.execute(delete_stages_query, {"project_id": project_id}).rowcount
        
        # Delete project invitations
        delete_invitations_query = text("DELETE FROM project_invitations WHERE project_id = :project_id")
        deleted_counts["project_invitations"] = db.execute(delete_invitations_query, {"project_id": project_id}).rowcount
        
        # Delete project members
        delete_members_query = text("DELETE FROM project_members WHERE project_id = :project_id")
        deleted_counts["project_members"] = db.execute(delete_members_query, {"project_id": project_id}).rowcount
        
        # Step 6: Delete users that were only associated with this project
        for user_id, user_email, user_role in users_to_delete:
            try:
                # Final safety check - ensure user has no other project associations
                safety_check_query = text("""
                    SELECT COUNT(*) as count FROM (
                        SELECT 1 FROM project_members pm WHERE pm.user_id = :user_id
                        UNION ALL
                        SELECT 1 FROM project_invitations pi WHERE pi.accepted_by_id = :user_id
                        UNION ALL
                        SELECT 1 FROM project_documents pd WHERE pd.uploaded_by = :user_id
                    ) as associations
                """)
                
                safety_result = db.execute(safety_check_query, {"user_id": user_id}).fetchone()
                
                if safety_result and safety_result[0] == 0:
                    # Safe to delete this user
                    delete_user_query = text("DELETE FROM users WHERE id = :user_id")
                    db.execute(delete_user_query, {"user_id": user_id})
                    deleted_counts["users_deleted"] += 1
                    logger.info(f"Deleted user {user_email} (ID: {user_id}) - was only associated with this project")
                else:
                    logger.info(f"Preserved user {user_email} (ID: {user_id}) - has other associations")
                    
            except Exception as e:
                logger.error(f"Error deleting user {user_email}: {e}")
                # Continue without failing the entire deletion
        
        # Step 7: Finally, delete the project itself
        delete_project_query = text("DELETE FROM projects WHERE id = :project_id")
        project_deleted = db.execute(delete_project_query, {"project_id": project_id}).rowcount
        
        if project_deleted == 0:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete project - may have been deleted by another process"
            )
        
        # Commit all changes
        db.commit()
        
        logger.info(f"Successfully COMPLETELY deleted project {project_id} ({company_id} - {project_name})")
        logger.info(f"Deletion statistics: {deleted_counts}")
        
        return {
            "message": f"Successfully deleted project '{project_name}' (ID: {project_id}) and all associated data",
            "project_id": project_id,
            "company_id": company_id,
            "project_name": project_name,
            "is_test": is_test,
            "deletion_statistics": deleted_counts,
            "warning": "This operation is irreversible - all project data has been permanently removed"
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions (like 404, 403)
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error during project deletion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )