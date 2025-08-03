"""
Invitation API endpoints for beta startup onboarding
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.api.auth import get_current_user, get_db
from app.db.models import User, Project, ProjectInvitation, ProjectMember
from app.services.invitation_service import (
    invite_users_to_project,
    validate_invitation,
    accept_invitation,
    cancel_invitation
)
from app.core.logging_config import get_shared_logger

logger = get_shared_logger(__name__)
router = APIRouter()


class InvitationRequest(BaseModel):
    emails: List[EmailStr]
    language: Optional[str] = "en"


class InvitationResponse(BaseModel):
    id: int
    email: str
    status: str
    expires_at: str
    created_at: str
    invitation_token: str


class InvitationDetails(BaseModel):
    project_name: str
    gp_name: str
    email: str
    expires_at: str
    status: str


class AcceptInvitationRequest(BaseModel):
    first_name: str
    last_name: str
    company_name: str
    password: str
    preferred_language: Optional[str] = "en"


@router.post("/projects/{project_id}/invite", response_model=List[InvitationResponse])
def send_project_invitations(
    project_id: int,
    request: InvitationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Send invitations to multiple users for a project"""
    
    # Verify user owns the project
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have permission to invite users"
        )
    
    # Check if user is a GP
    if current_user.role != "gp":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only GPs can send project invitations"
        )
    
    try:
        invitations = invite_users_to_project(
            db=db,
            project_id=project_id,
            emails=[str(email) for email in request.emails],
            invited_by=current_user
        )
        
        return [
            InvitationResponse(
                id=inv.id,
                email=inv.email,
                status=inv.status,
                expires_at=inv.expires_at.isoformat(),
                created_at=inv.created_at.isoformat(),
                invitation_token=inv.invitation_token
            )
            for inv in invitations
        ]
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error sending invitations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send invitations"
        )


@router.get("/invitation/{token}", response_model=InvitationDetails)
def get_invitation_details(token: str, db: Session = Depends(get_db)):
    """Get details for an invitation token"""
    
    invitation = validate_invitation(db, token)
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid, expired, or already used invitation"
        )
    
    # Get project and inviter details
    project = db.query(Project).filter(Project.id == invitation.project_id).first()
    inviter = db.query(User).filter(User.id == invitation.invited_by_id).first()
    
    if not project or not inviter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or inviter not found"
        )
    
    gp_name = f"{inviter.first_name} {inviter.last_name}" if inviter.first_name else inviter.email
    
    return InvitationDetails(
        project_name=project.project_name,
        gp_name=gp_name,
        email=invitation.email,
        expires_at=invitation.expires_at.isoformat(),
        status=invitation.status
    )


@router.post("/invitation/{token}/accept")
def accept_project_invitation(
    token: str,
    request: AcceptInvitationRequest,
    db: Session = Depends(get_db)
):
    """Accept an invitation and create user account"""
    
    invitation = validate_invitation(db, token)
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid, expired, or already used invitation"
        )
    
    # Check if user already exists with this email
    existing_user = db.query(User).filter(User.email == invitation.email).first()
    
    if existing_user:
        # If user exists and is verified, just add them to project
        if existing_user.is_verified:
            try:
                member = accept_invitation(db, invitation, existing_user)
                return {
                    "message": "Invitation accepted successfully",
                    "user_id": existing_user.id,
                    "project_id": invitation.project_id,
                    "redirect_url": f"/project/{member.project.company_id}"
                }
            except Exception as e:
                logger.error(f"Error accepting invitation for existing user: {e}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to accept invitation"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User exists but is not verified. Please verify your email first."
            )
    
    # Create new user account
    try:
        from passlib.context import CryptContext
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        new_user = User(
            email=invitation.email,
            password_hash=pwd_context.hash(request.password),
            first_name=request.first_name,
            last_name=request.last_name,
            company_name=request.company_name,
            role="startup",
            preferred_language=request.preferred_language,
            is_verified=True  # Auto-verify invited users
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Accept invitation and add to project
        member = accept_invitation(db, invitation, new_user)
        
        logger.info(f"Created new user {new_user.id} and accepted invitation to project {invitation.project_id}")
        
        return {
            "message": "Account created and invitation accepted successfully",
            "user_id": new_user.id,
            "project_id": invitation.project_id,
            "redirect_url": f"/project/{member.project.company_id}"
        }
        
    except Exception as e:
        logger.error(f"Error creating user and accepting invitation: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create account and accept invitation"
        )


@router.delete("/invitation/{invitation_id}")
def cancel_project_invitation(
    invitation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a pending invitation"""
    
    # Verify user owns the project that the invitation belongs to
    invitation = db.query(ProjectInvitation).filter(
        ProjectInvitation.id == invitation_id
    ).first()
    
    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )
    
    project = db.query(Project).filter(
        Project.id == invitation.project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to cancel this invitation"
        )
    
    success = cancel_invitation(db, invitation_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation cannot be cancelled (already accepted/expired/cancelled)"
        )
    
    return {"message": "Invitation cancelled successfully"}


@router.get("/projects/{project_id}/invitations", response_model=List[InvitationResponse])
def get_project_invitations(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all invitations for a project"""
    
    # Verify user owns the project
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found or you don't have permission to view invitations"
        )
    
    invitations = db.query(ProjectInvitation).filter(
        ProjectInvitation.project_id == project_id
    ).order_by(ProjectInvitation.created_at.desc()).all()
    
    return [
        InvitationResponse(
            id=inv.id,
            email=inv.email,
            status=inv.status,
            expires_at=inv.expires_at.isoformat(),
            created_at=inv.created_at.isoformat(),
            invitation_token=inv.invitation_token
        )
        for inv in invitations
    ]