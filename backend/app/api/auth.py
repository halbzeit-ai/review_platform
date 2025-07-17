
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from ..db.database import get_db
from ..db.models import User
from ..services.email_service import email_service
from ..services.token_service import token_service

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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
    preferred_language: str = "de"

class LanguagePreferenceData(BaseModel):
    preferred_language: str

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
    
    # Find all pitch decks belonging to this user
    pitch_decks = db.execute(
        text("SELECT id, file_name, file_path, results_file_path FROM pitch_decks WHERE user_id = :user_id"),
        {"user_id": user_to_delete.id}
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
    db.execute(text("DELETE FROM questions WHERE review_id IN (SELECT id FROM reviews WHERE pitch_deck_id IN (SELECT id FROM pitch_decks WHERE user_id = :user_id))"), {"user_id": user_to_delete.id})
    
    # Delete reviews (if they exist)
    db.execute(text("DELETE FROM reviews WHERE pitch_deck_id IN (SELECT id FROM pitch_decks WHERE user_id = :user_id)"), {"user_id": user_to_delete.id})
    
    # Delete pitch decks
    db.execute(text("DELETE FROM pitch_decks WHERE user_id = :user_id"), {"user_id": user_to_delete.id})
    
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
