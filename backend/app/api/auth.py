
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import re
from typing import List
from ..db.database import get_db
from ..db.models import User
from ..services.email_service import email_service
from ..services.token_service import token_service

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def validate_password_strength(password: str) -> List[str]:
    """
    Validate password strength according to OWASP Authentication Cheat Sheet
    Returns list of error messages, empty list if password is valid
    """
    errors = []
    
    # Minimum length: 8 characters
    if len(password) < 8:
        errors.append("must be at least 8 characters long")
    
    # Maximum length: 128 characters (prevent DoS)
    if len(password) > 128:
        errors.append("must not exceed 128 characters")
    
    # Must contain at least 3 of the following 4 character types:
    checks = {
        'lowercase': bool(re.search(r'[a-z]', password)),
        'uppercase': bool(re.search(r'[A-Z]', password)),
        'digits': bool(re.search(r'[0-9]', password)),
        'special': bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?`~]', password))
    }
    
    complexity_count = sum(checks.values())
    
    if complexity_count < 3:
        missing = []
        if not checks['lowercase']:
            missing.append("lowercase letters")
        if not checks['uppercase']:
            missing.append("uppercase letters") 
        if not checks['digits']:
            missing.append("numbers")
        if not checks['special']:
            missing.append("special characters (!@#$%^&* etc.)")
        
        errors.append(f"must contain at least 3 of: {', '.join(missing)}")
    
    # Check against common passwords (basic check)
    common_passwords = [
        'password', '123456', '123456789', 'qwerty', 'abc123', 
        'password123', '111111', '123123', 'admin', 'letmein',
        'welcome', 'monkey', '1234567890', 'password1'
    ]
    
    if password.lower() in common_passwords:
        errors.append("cannot be a common password")
    
    # No sequential characters (basic check)
    if re.search(r'(012|123|234|345|456|567|678|789|890|abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)', password.lower()):
        errors.append("cannot contain sequential characters (123, abc, etc.)")
    
    # No repeated characters (more than 2 in a row)
    if re.search(r'(.)\1{2,}', password):
        errors.append("cannot contain more than 2 repeated characters in a row")
    
    return errors

def is_first_user(db: Session) -> bool:
    return db.query(User).first() is None

class UpdateRoleData(BaseModel):
    user_email: str
    new_role: str

class LoginData(BaseModel):
    email: str
    password: str

class RegisterData(BaseModel):
    email: str
    password: str
    company_name: str
    role: str

class InviteGPData(BaseModel):
    email: str
    name: str
    preferred_language: str = "de"

class LanguagePreferenceData(BaseModel):
    preferred_language: str

class ForgotPasswordData(BaseModel):
    email: str

class ResetPasswordData(BaseModel):
    token: str
    new_password: str

class ChangePasswordData(BaseModel):
    current_password: str
    new_password: str

class ForcedPasswordChangeData(BaseModel):
    new_password: str

class UpdateProfileData(BaseModel):
    first_name: str = None
    last_name: str = None
    company_name: str = None
    preferred_language: str = None

@router.post("/register")
async def register(data: RegisterData, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Determine role - first user is GP, others are startup by default
    assigned_role = "gp" if is_first_user(db) else "startup"
    
    # Validate language preference
    if data.preferred_language not in ["de", "en"]:
        data.preferred_language = "de"  # Default to German
    
    # Create new user
    new_user = User(
        email=data.email,
        password_hash=pwd_context.hash(data.password),
        company_name=data.company_name,
        role=assigned_role,  # This will now correctly use 'gp' for first user
        preferred_language=data.preferred_language,
        is_verified=False  # Will be set to True after email verification
    )
    
    try:
        # Generate verification token
        verification_token, expires_at = token_service.generate_verification_token()
        token_hash = token_service.hash_token(verification_token)
        
        # Store hashed token in user record
        new_user.verification_token = token_hash
        new_user.verification_token_expires = expires_at
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # Send verification email
        email_sent = email_service.send_verification_email(data.email, verification_token, data.preferred_language)
        
        if not email_sent:
            # If email fails, we still keep the user but warn them
            print(f"Warning: Verification email failed to send to {data.email}")
        
        print(f"User registered successfully: {data.email}")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Registration successful! Please check your email to verify your account before logging in.",
                "email": data.email,
                "company_name": data.company_name,
                "role": assigned_role,
                "email_sent": email_sent
            }
        )
    except Exception as e:
        db.rollback()
        print(f"Registration failed for {data.email}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

from jose import JWTError, jwt
from datetime import datetime, timedelta
from ..core.config import settings
import secrets

@router.post("/login")
async def login(data: LoginData, db: Session = Depends(get_db)):
    # Find user
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not pwd_context.verify(data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    # Check if email is verified
    if not user.is_verified:
        raise HTTPException(
            status_code=403, 
            detail="Please verify your email address before logging in. Check your inbox for the verification email."
        )
    
    # Check if user must change password
    if user.must_change_password:
        # Create temporary token for password change
        access_token_expires = timedelta(minutes=30)  # Short-lived token for password change
        access_token = create_access_token(
            data={"sub": user.email, "role": user.role, "must_change_password": True},
            expires_delta=access_token_expires
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Password change required",
                "email": user.email,
                "role": user.role,
                "must_change_password": True,
                "access_token": access_token,
                "token_type": "Bearer"
            }
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # Update last login time with timezone info
    user.last_login = datetime.now()
    db.commit()
    
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )

    return JSONResponse(
        status_code=200,
        content={
            "message": "Login successful",
            "email": user.email,
            "role": user.role,
            "company_name": user.company_name,
            "preferred_language": user.preferred_language or "de",
            "access_token": access_token,
            "token_type": "Bearer"
        }
    )

def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt

from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Depends, HTTPException, status

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(credentials.credentials, settings.SECRET_KEY, algorithms=["HS256"])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Could not validate credentials")
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

@router.post("/update-role")
async def update_role(data: UpdateRoleData, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Verify the requester is a GP using the validated token
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Only GPs can change user roles")
    
    # Find and update the target user
    target_user = db.query(User).filter(User.email == data.user_email).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent role change for the primary GP admin
    if data.user_email.lower() == "ramin@halbzeit.ai":
        raise HTTPException(status_code=403, detail="Cannot change the role of the primary GP administrator")
    
    if data.new_role not in ["gp", "startup"]:
        raise HTTPException(status_code=400, detail="Invalid role specified")
    
    target_user.role = data.new_role
    db.commit()
    
    return JSONResponse(
        status_code=200,
        content={
            "message": f"Role updated successfully to {data.new_role}",
            "email": data.user_email,
            "new_role": data.new_role
        }
    )

@router.get("/language-preference")
async def get_language_preference(current_user: User = Depends(get_current_user)):
    """Get current user's language preference"""
    return JSONResponse(
        status_code=200,
        content={
            "preferred_language": current_user.preferred_language or "de",
            "email": current_user.email
        }
    )

@router.post("/language-preference")
async def update_language_preference(
    data: LanguagePreferenceData, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Update current user's language preference"""
    # Validate language preference
    if data.preferred_language not in ["de", "en"]:
        raise HTTPException(status_code=400, detail="Invalid language. Must be 'de' or 'en'")
    
    # Update user's language preference
    current_user.preferred_language = data.preferred_language
    db.commit()
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "Language preference updated successfully",
            "preferred_language": data.preferred_language,
            "email": current_user.email
        }
    )

@router.delete("/delete-user")
async def delete_user(
    user_email: str = Query(..., description="Email of user to delete"),
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Delete a user account and cascade delete their projects (GP only)"""
    # Verify the requester is a GP
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Only GPs can delete users")
    
    # Prevent self-deletion
    if current_user.email == user_email:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Prevent deletion of the primary GP admin
    if user_email.lower() == "ramin@halbzeit.ai":
        raise HTTPException(status_code=403, detail="Cannot delete the primary GP administrator")
    
    # Find the user to delete
    print(f"[DEBUG] Attempting to delete user with email: '{user_email}'")
    user_to_delete = db.query(User).filter(User.email == user_email).first()
    
    if not user_to_delete:
        raise HTTPException(status_code=404, detail=f"User not found: {user_email}")
    
    # Import necessary modules for file operations
    import os
    import shutil
    from sqlalchemy import text
    from ..core.config import Settings
    
    settings = Settings()
    
    # Get user's company_id for project cleanup
    from ..api.projects import get_company_id_from_user
    company_id = get_company_id_from_user(user_to_delete)
    
    # Find all pitch decks belonging to this user (by user_id OR company_id)
    pitch_decks = db.execute(
        text("SELECT id, file_name, file_path, results_file_path FROM pitch_decks WHERE user_id = :user_id OR company_id = :company_id"),
        {"user_id": user_to_delete.id, "company_id": company_id}
    ).fetchall()
    
    deleted_files = []
    deleted_folders = []
    
    # Delete all associated pitch decks and their files
    for deck in pitch_decks:
        deck_id, file_name, file_path, results_file_path = deck
        
        # Delete the PDF file
        if file_path:
            if file_path.startswith('/'):
                pdf_full_path = file_path
            else:
                pdf_full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, file_path)
            
            if os.path.exists(pdf_full_path):
                try:
                    os.remove(pdf_full_path)
                    deleted_files.append(pdf_full_path)
                    print(f"[DEBUG] Deleted PDF file: {pdf_full_path}")
                except Exception as e:
                    print(f"[WARNING] Could not delete PDF file {pdf_full_path}: {e}")
        
        # Delete the results file
        if results_file_path:
            if results_file_path.startswith('/'):
                results_full_path = results_file_path
            else:
                results_full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, results_file_path)
            
            if os.path.exists(results_full_path):
                try:
                    os.remove(results_full_path)
                    deleted_files.append(results_full_path)
                    print(f"[DEBUG] Deleted results file: {results_full_path}")
                except Exception as e:
                    print(f"[WARNING] Could not delete results file {results_full_path}: {e}")
        
        # Delete the analysis folder with slide images
        if file_name:
            deck_name = os.path.splitext(file_name)[0]
            analysis_folder = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", company_id, "analysis", deck_name)
            
            if os.path.exists(analysis_folder):
                try:
                    shutil.rmtree(analysis_folder)
                    deleted_folders.append(analysis_folder)
                    print(f"[DEBUG] Deleted analysis folder: {analysis_folder}")
                except Exception as e:
                    print(f"[WARNING] Could not delete analysis folder {analysis_folder}: {e}")
    
    # Delete the entire project directory if it exists and is empty
    project_dir = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", company_id)
    if os.path.exists(project_dir):
        try:
            # Check if directory is empty or only contains empty subdirectories
            if not any(os.listdir(subdir) for subdir in [
                os.path.join(project_dir, "analysis"),
                os.path.join(project_dir, "uploads"),
                os.path.join(project_dir, "exports")
            ] if os.path.exists(subdir)):
                shutil.rmtree(project_dir)
                deleted_folders.append(project_dir)
                print(f"[DEBUG] Deleted project directory: {project_dir}")
        except Exception as e:
            print(f"[WARNING] Could not delete project directory {project_dir}: {e}")
    
    # Delete all database records related to this user
    # Delete in correct order: questions -> reviews -> pitch_decks
    
    # Delete questions (if they exist)
    db.execute(text("DELETE FROM questions WHERE review_id IN (SELECT id FROM reviews WHERE pitch_deck_id IN (SELECT id FROM pitch_decks WHERE user_id = :user_id OR company_id = :company_id))"), {"user_id": user_to_delete.id, "company_id": company_id})
    
    # Delete reviews (if they exist)
    db.execute(text("DELETE FROM reviews WHERE pitch_deck_id IN (SELECT id FROM pitch_decks WHERE user_id = :user_id OR company_id = :company_id)"), {"user_id": user_to_delete.id, "company_id": company_id})
    
    # Delete pitch decks
    db.execute(text("DELETE FROM pitch_decks WHERE user_id = :user_id OR company_id = :company_id"), {"user_id": user_to_delete.id, "company_id": company_id})
    
    # Finally, delete the user
    db.delete(user_to_delete)
    db.commit()
    
    print(f"[DEBUG] User deletion completed: {user_email}")
    print(f"[DEBUG] Deleted {len(pitch_decks)} pitch decks")
    print(f"[DEBUG] Deleted {len(deleted_files)} files")
    print(f"[DEBUG] Deleted {len(deleted_folders)} folders")
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "User and all associated projects deleted successfully",
            "deleted_email": user_email,
            "deleted_projects": len(pitch_decks),
            "deleted_files": len(deleted_files),
            "deleted_folders": len(deleted_folders),
            "company_id": company_id
        }
    )

@router.get("/verify-email")
async def verify_email(token: str = Query(...), db: Session = Depends(get_db)):
    """Verify email address using the token from verification email"""
    if not token:
        raise HTTPException(status_code=400, detail="Verification token is required")
    
    # Hash the provided token to compare with stored hash
    token_hash = token_service.hash_token(token)
    
    # Find user with this verification token
    user = db.query(User).filter(User.verification_token == token_hash).first()
    
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")
    
    # Check if token has expired
    if token_service.is_token_expired(user.verification_token_expires):
        raise HTTPException(status_code=400, detail="Verification token has expired. Please register again.")
    
    # Verify the user
    user.is_verified = True
    user.verification_token = None  # Clear the token
    user.verification_token_expires = None
    db.commit()
    
    # Send welcome email
    email_service.send_welcome_email(user.email, user.company_name, user.preferred_language or "de")
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "Email verified successfully! You can now log in to your account.",
            "email": user.email,
            "verified": True
        }
    )

class ResendVerificationData(BaseModel):
    email: str

@router.post("/resend-verification")
async def resend_verification(data: ResendVerificationData, db: Session = Depends(get_db)):
    """Resend verification email"""
    user = db.query(User).filter(User.email == data.email).first()
    
    if not user:
        # Don't reveal if email exists or not for security
        return JSONResponse(
            status_code=200,
            content={"message": "If an account with this email exists, a verification email has been sent."}
        )
    
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified")
    
    # Generate new verification token
    verification_token, expires_at = token_service.generate_verification_token()
    token_hash = token_service.hash_token(verification_token)
    
    # Update user with new token
    user.verification_token = token_hash
    user.verification_token_expires = expires_at
    db.commit()
    
    # Send verification email
    email_sent = email_service.send_verification_email(data.email, verification_token)
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "If an account with this email exists, a verification email has been sent.",
            "email_sent": email_sent
        }
    )

@router.get("/users")
async def get_all_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Only GPs can view all users")
    
    users = db.query(User).all()
    return [{"email": user.email, "company_name": user.company_name, "role": user.role, "created_at": user.created_at, "last_login": user.last_login, "is_verified": user.is_verified} for user in users]

@router.get("/profile")
async def get_profile(current_user: User = Depends(get_current_user)):
    """Get current user's profile information"""
    return JSONResponse(
        status_code=200,
        content={
            "email": current_user.email,
            "first_name": current_user.first_name,
            "last_name": current_user.last_name,
            "company_name": current_user.company_name,
            "role": current_user.role,
            "preferred_language": current_user.preferred_language or "de",
            "is_verified": current_user.is_verified,
            "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
            "last_login": current_user.last_login.isoformat() if current_user.last_login else None
        }
    )

@router.put("/profile")
async def update_profile(
    data: UpdateProfileData, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Update current user's profile information"""
    updated_fields = []
    
    # Update first_name if provided
    if data.first_name is not None:
        current_user.first_name = data.first_name.strip() if data.first_name.strip() else None
        updated_fields.append("first_name")
    
    # Update last_name if provided
    if data.last_name is not None:
        current_user.last_name = data.last_name.strip() if data.last_name.strip() else None
        updated_fields.append("last_name")
    
    # Update company_name if provided
    if data.company_name is not None:
        current_user.company_name = data.company_name.strip() if data.company_name.strip() else None
        updated_fields.append("company_name")
    
    # Update preferred_language if provided
    if data.preferred_language is not None:
        if data.preferred_language not in ["de", "en"]:
            raise HTTPException(status_code=400, detail="Invalid language. Must be 'de' or 'en'")
        current_user.preferred_language = data.preferred_language
        updated_fields.append("preferred_language")
    
    # Commit changes if any fields were updated
    if updated_fields:
        db.commit()
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "Profile updated successfully",
            "updated_fields": updated_fields,
            "profile": {
                "email": current_user.email,
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "company_name": current_user.company_name,
                "role": current_user.role,
                "preferred_language": current_user.preferred_language or "de",
                "is_verified": current_user.is_verified
            }
        }
    )

@router.get("/company-info")
async def get_company_info(current_user: User = Depends(get_current_user)):
    """Get current user's company information and generated company ID"""
    from ..api.projects import get_company_id_from_user
    
    company_id = get_company_id_from_user(current_user)
    
    return JSONResponse(
        status_code=200,
        content={
            "company_name": current_user.company_name,
            "company_id": company_id,
            "dashboard_path": f"/project/{company_id}" if current_user.role == "startup" else "/dashboard/gp"
        }
    )

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordData, db: Session = Depends(get_db)):
    """Send password reset email"""
    user = db.query(User).filter(User.email == data.email).first()
    
    # Don't reveal if email exists or not for security
    if not user:
        return JSONResponse(
            status_code=200,
            content={"message": "If an account with this email exists, a password reset email has been sent."}
        )
    
    # Generate password reset token
    reset_token, expires_at = token_service.generate_verification_token()
    token_hash = token_service.hash_token(reset_token)
    
    # Update user with reset token (reuse verification fields)
    user.verification_token = token_hash
    user.verification_token_expires = expires_at
    db.commit()
    
    # Send password reset email
    email_sent = email_service.send_password_reset_email(data.email, reset_token)
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "If an account with this email exists, a password reset email has been sent.",
            "email_sent": email_sent
        }
    )

@router.post("/reset-password")
async def reset_password(data: ResetPasswordData, db: Session = Depends(get_db)):
    """Reset password using token"""
    # Hash the provided token
    token_hash = token_service.hash_token(data.token)
    
    # Find user with this token
    user = db.query(User).filter(
        User.verification_token == token_hash,
        User.verification_token_expires > datetime.utcnow()
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=400, 
            detail="Invalid or expired password reset token"
        )
    
    # Validate new password according to OWASP standards
    password_errors = validate_password_strength(data.new_password)
    if password_errors:
        raise HTTPException(
            status_code=400,
            detail=f"Password requirements not met: {', '.join(password_errors)}"
        )
    
    # Update password
    user.password_hash = pwd_context.hash(data.new_password)
    user.verification_token = None
    user.verification_token_expires = None
    db.commit()
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "Password reset successful. You can now login with your new password.",
            "email": user.email
        }
    )

@router.post("/change-password")
async def change_password(
    data: ChangePasswordData, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Change password (for forced password changes or user-initiated changes)"""
    
    # Verify current password
    if not pwd_context.verify(data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=400, 
            detail="Current password is incorrect"
        )
    
    # Validate new password according to OWASP standards
    password_errors = validate_password_strength(data.new_password)
    if password_errors:
        raise HTTPException(
            status_code=400,
            detail=f"Password requirements not met: {', '.join(password_errors)}"
        )
    
    if data.current_password == data.new_password:
        raise HTTPException(
            status_code=400,
            detail="New password must be different from current password"
        )
    
    # Update password and clear must_change_password flag
    current_user.password_hash = pwd_context.hash(data.new_password)
    current_user.must_change_password = False
    db.commit()
    
    # Generate new access token without must_change_password flag
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.email, "role": current_user.role},
        expires_delta=access_token_expires
    )
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "Password changed successfully",
            "email": current_user.email,
            "role": current_user.role,
            "access_token": access_token,
            "token_type": "Bearer"
        }
    )

@router.post("/change-password-forced")
async def change_password_forced(
    data: ForcedPasswordChangeData, 
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """Change password for users with must_change_password=True (no current password required)"""
    
    # Verify this user actually needs to change password
    if not current_user.must_change_password:
        raise HTTPException(
            status_code=400, 
            detail="Password change not required for this user"
        )
    
    # Validate new password according to OWASP standards
    password_errors = validate_password_strength(data.new_password)
    if password_errors:
        raise HTTPException(
            status_code=400,
            detail=f"Password requirements not met: {', '.join(password_errors)}"
        )
    
    # Update password and clear must_change_password flag
    current_user.password_hash = pwd_context.hash(data.new_password)
    current_user.must_change_password = False
    # Update last login time since this is effectively their first real login
    current_user.last_login = datetime.now()
    db.commit()
    
    # Generate new access token without must_change_password flag
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.email, "role": current_user.role},
        expires_delta=access_token_expires
    )
    
    return JSONResponse(
        status_code=200,
        content={
            "message": "Password changed successfully",
            "email": current_user.email,
            "role": current_user.role,
            "access_token": access_token,
            "token_type": "Bearer"
        }
    )

@router.post("/invite-gp")
async def invite_gp(
    data: InviteGPData,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invite a new GP to the platform (GP only)"""
    # Verify the requester is a GP
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Only GPs can invite other GPs")
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Generate a temporary password
    import secrets
    temp_password = secrets.token_urlsafe(12)
    
    # Create the new GP user
    new_user = User(
        email=data.email,
        password_hash=pwd_context.hash(temp_password),
        company_name=data.name,  # For GPs, we use their name as company name
        role="gp",
        first_name=data.name.split()[0] if " " in data.name else data.name,
        last_name=" ".join(data.name.split()[1:]) if " " in data.name else "",
        preferred_language=data.preferred_language,
        is_verified=False,
        must_change_password=True  # Force password change on first login
    )
    
    # Generate verification token
    verification_token, expires_at = token_service.generate_verification_token()
    token_hash = token_service.hash_token(verification_token)
    new_user.verification_token = token_hash
    new_user.verification_token_expires = expires_at
    
    db.add(new_user)
    db.commit()
    
    # Send invitation email with temporary password and verification link
    email_sent = email_service.send_gp_invitation_email(
        email=data.email,
        name=data.name,
        temp_password=temp_password,
        verification_token=verification_token,
        invited_by=current_user.company_name or current_user.email,
        language=data.preferred_language
    )
    
    return JSONResponse(
        status_code=201,
        content={
            "message": "GP invitation sent successfully",
            "email": data.email,
            "name": data.name,
            "email_sent": email_sent
        }
    )
