#!/usr/bin/env python3
"""
Development script to manually verify a user account
Bypasses email verification for development
"""

import sys
import os

# Change to backend directory
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
os.chdir(backend_dir)
sys.path.insert(0, backend_dir)

from app.db.database import SessionLocal
from app.db.models import User
from sqlalchemy.orm import Session

def verify_user(email: str):
    """Manually verify a user account"""
    db: Session = SessionLocal()
    
    try:
        user = db.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"❌ User with email '{email}' not found")
            return False
        
        if user.is_verified:
            print(f"✅ User '{email}' is already verified")
            return True
        
        # Verify the user
        user.is_verified = True
        db.commit()
        
        print(f"✅ Successfully verified user '{email}'")
        print(f"   Company: {user.company_name}")
        print(f"   Role: {user.role}")
        return True
        
    except Exception as e:
        print(f"❌ Error verifying user: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python dev-verify-user.py <email>")
        print("Example: python dev-verify-user.py ramin@halbzeit.ai")
        sys.exit(1)
    
    email = sys.argv[1]
    verify_user(email)