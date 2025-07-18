#!/usr/bin/env python3
"""
Script to manually verify a user account
Run this on the production server if email verification is not working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine
from app.db.models import User
from sqlalchemy.orm import sessionmaker

def verify_user(email: str):
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Find user
        user = session.query(User).filter(User.email == email).first()
        
        if not user:
            print(f"✗ User {email} not found in database")
            return False
            
        if user.is_verified:
            print(f"✓ User {email} is already verified")
            return True
            
        # Verify the user
        user.is_verified = True
        user.email_verification_token = None  # Clear the token
        session.commit()
        
        print(f"✓ User {email} has been manually verified")
        return True
        
    except Exception as e:
        print(f"✗ Error verifying user {email}: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python verify_user.py <email>")
        print("Example: python verify_user.py ramin@assadollahi.de")
        sys.exit(1)
    
    email = sys.argv[1]
    verify_user(email)