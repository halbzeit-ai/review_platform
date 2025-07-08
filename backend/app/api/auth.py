
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from ..db.database import get_db
from ..db.models import User

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

@router.post("/register")
async def register(data: RegisterData, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == data.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Determine role - first user is GP, others are startup by default
    assigned_role = "gp" if is_first_user(db) else "startup"
    
    # Create new user
    new_user = User(
        email=data.email,
        password_hash=pwd_context.hash(data.password),
        company_name=data.company_name,
        role=assigned_role,  # This will now correctly use 'gp' for first user
        is_verified=False  # Will be set to True after email verification
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        # TODO: Send verification email
        print(f"User registered successfully: {data.email}")
        
        return JSONResponse(
            status_code=200,
            content={
                "message": "Registration successful. Please check your email for verification.",
                "email": data.email,
                "company_name": data.company_name,
                "role": assigned_role
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

@router.get("/users")
async def get_all_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Only GPs can view all users")
    
    users = db.query(User).all()
    return [{"email": user.email, "company_name": user.company_name, "role": user.role, "created_at": user.created_at, "last_login": user.last_login} for user in users]
