"""
Unified Access Control System

This module provides the single source of truth for project access control.
All project-related access checks MUST use these functions.
"""

import logging
from sqlalchemy.orm import Session
from sqlalchemy import text
from ..db.models import User

logger = logging.getLogger(__name__)

def check_project_access(user: User, project_id: int, db: Session) -> bool:
    """
    Unified project access control - SINGLE SOURCE OF TRUTH
    
    Args:
        user: The authenticated user
        project_id: The project ID to check access for
        db: Database session
        
    Returns:
        bool: True if user has access to the project, False otherwise
        
    Rules:
        - GPs can access any project
        - Startups can only access projects they are explicitly members of
        - Access is determined by project_members table ONLY
        - Company names are NOT used for access control
    """
    try:
        # GPs have universal access
        if user.role == "gp":
            logger.debug(f"GP user {user.email} granted access to project {project_id}")
            return True
        
        # For startups: ONLY check explicit project membership
        if user.role == "startup":
            member_query = text("""
                SELECT 1 FROM project_members pm
                JOIN projects p ON pm.project_id = p.id
                WHERE pm.user_id = :user_id 
                AND p.id = :project_id 
                AND p.is_active = TRUE
            """)
            
            result = db.execute(member_query, {
                "user_id": user.id, 
                "project_id": project_id
            }).fetchone()
            
            has_access = result is not None
            
            if has_access:
                logger.debug(f"Startup user {user.email} granted access to project {project_id} via membership")
            else:
                logger.debug(f"Startup user {user.email} denied access to project {project_id} - not a member")
            
            return has_access
        
        # Unknown roles are denied
        logger.warning(f"Unknown user role {user.role} for user {user.email}")
        return False
        
    except Exception as e:
        logger.error(f"Error checking project access for user {user.email}, project {project_id}: {e}")
        return False

def check_project_access_by_company_id(user: User, company_id: str, db: Session) -> bool:
    """
    Check project access using company_id (transitional function)
    
    This function will be deprecated in Phase 2 when we move to project_id-based routes.
    It finds the project_id from company_id and uses the unified access control.
    
    Args:
        user: The authenticated user  
        company_id: The company ID to find project for
        db: Database session
        
    Returns:
        bool: True if user has access to any project with this company_id
    """
    try:
        # GPs have universal access
        if user.role == "gp":
            return True
            
        # Find project_id from company_id
        project_query = text("""
            SELECT id FROM projects 
            WHERE company_id = :company_id AND is_active = TRUE
            LIMIT 1
        """)
        
        project_result = db.execute(project_query, {"company_id": company_id}).fetchone()
        
        if not project_result:
            logger.debug(f"No active project found for company_id {company_id}")
            return False
            
        project_id = project_result[0]
        
        # Use the unified access control
        return check_project_access(user, project_id, db)
        
    except Exception as e:
        logger.error(f"Error checking project access by company_id for user {user.email}, company_id {company_id}: {e}")
        return False

def get_user_project_ids(user: User, db: Session) -> list[int]:
    """
    Get all project IDs that a user has access to
    
    Args:
        user: The authenticated user
        db: Database session
        
    Returns:
        List of project IDs the user can access
    """
    try:
        if user.role == "gp":
            # GPs can access all active projects
            query = text("SELECT id FROM projects WHERE is_active = TRUE")
            results = db.execute(query).fetchall()
            return [row[0] for row in results]
        
        elif user.role == "startup":
            # Startups can only access projects they're members of
            query = text("""
                SELECT p.id FROM projects p
                JOIN project_members pm ON p.id = pm.project_id
                WHERE pm.user_id = :user_id AND p.is_active = TRUE
            """)
            results = db.execute(query, {"user_id": user.id}).fetchall()
            return [row[0] for row in results]
            
        return []
        
    except Exception as e:
        logger.error(f"Error getting project IDs for user {user.email}: {e}")
        return []