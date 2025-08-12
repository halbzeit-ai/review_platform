"""
Invitation service for beta startup onboarding
"""
import secrets
import string
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db.models import ProjectInvitation, Project, User, ProjectMember
from app.services.email_service import email_service
from app.core.config import settings
from app.core.logging_config import get_shared_logger

logger = get_shared_logger(__name__)


def generate_invitation_token(length: int = 32) -> str:
    """Generate a secure random invitation token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_project_invitation(
    db: Session,
    project_id: int,
    email: str,
    invited_by_id: int
) -> ProjectInvitation:
    """Create a new project invitation"""
    
    # Check if invitation already exists for this email and project
    existing = db.query(ProjectInvitation).filter(
        and_(
            ProjectInvitation.project_id == project_id,
            ProjectInvitation.email == email,
            ProjectInvitation.status == "pending"
        )
    ).first()
    
    if existing:
        logger.info(f"Invitation already exists for {email} to project {project_id}")
        return existing
    
    # Create new invitation
    invitation = ProjectInvitation(
        invitation_token=generate_invitation_token(),
        project_id=project_id,
        email=email,
        invited_by_id=invited_by_id,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    
    logger.info(f"Created invitation for {email} to project {project_id}")
    return invitation


def send_invitation_email(
    invitation: ProjectInvitation,
    project: Project,
    inviter: User,
    language: str = "en"
) -> bool:
    """Send invitation email to the invitee"""
    
    invitation_url = f"{settings.FRONTEND_URL}/invitation/{invitation.invitation_token}"
    gp_name = f"{inviter.first_name} {inviter.last_name}" if inviter.first_name else inviter.email
    
    success = email_service.send_invitation_email(
        email=invitation.email,
        gp_name=gp_name,
        project_name=project.project_name,
        invitation_url=invitation_url,
        language=language
    )
    
    if success:
        logger.info(f"Sent invitation email to {invitation.email}")
    else:
        logger.error(f"Failed to send invitation email to {invitation.email}")
    
    return success


def invite_users_to_project(
    db: Session,
    project_id: int,
    emails: List[str],
    invited_by: User
) -> List[ProjectInvitation]:
    """Invite multiple users to a project"""
    
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError(f"Project {project_id} not found")
    
    invitations = []
    for email in emails[:5]:  # Limit to 5 invitations per project
        invitation = create_project_invitation(
            db=db,
            project_id=project_id,
            email=email.lower().strip(),
            invited_by_id=invited_by.id
        )
        
        # Send invitation email
        send_invitation_email(
            invitation=invitation,
            project=project,
            inviter=invited_by,
            language=invited_by.preferred_language
        )
        
        invitations.append(invitation)
    
    return invitations


def validate_invitation(db: Session, token: str) -> Optional[ProjectInvitation]:
    """Validate an invitation token"""
    
    invitation = db.query(ProjectInvitation).filter(
        ProjectInvitation.invitation_token == token
    ).first()
    
    if not invitation:
        logger.warning(f"Invalid invitation token: {token}")
        return None
    
    if invitation.status != "pending":
        logger.warning(f"Invitation {token} already used with status: {invitation.status}")
        return None
    
    if invitation.expires_at < datetime.utcnow():
        invitation.status = "expired"
        db.commit()
        logger.warning(f"Invitation {token} has expired")
        return None
    
    return invitation


def accept_invitation(
    db: Session,
    invitation: ProjectInvitation,
    user: User
) -> ProjectMember:
    """Accept an invitation and add user to project"""
    
    # Update invitation
    invitation.status = "accepted"
    invitation.accepted_at = datetime.utcnow()
    invitation.accepted_by_id = user.id
    
    # BUSINESS RULE: GP remains owner initially, ownership transfers only when user leaves
    # This preserves data retention capability - GP can always re-invite users
    
    # Add user as project member
    member = ProjectMember(
        project_id=invitation.project_id,
        user_id=user.id,
        role="member",
        added_by_id=invitation.invited_by_id
    )
    
    db.add(member)
    db.commit()
    db.refresh(member)
    
    logger.info(f"User {user.id} accepted invitation to project {invitation.project_id}")
    return member


def cancel_invitation(db: Session, invitation_id: int) -> bool:
    """Cancel a pending invitation"""
    
    invitation = db.query(ProjectInvitation).filter(
        ProjectInvitation.id == invitation_id
    ).first()
    
    if not invitation or invitation.status != "pending":
        return False
    
    invitation.status = "cancelled"
    db.commit()
    
    logger.info(f"Cancelled invitation {invitation_id}")
    return True