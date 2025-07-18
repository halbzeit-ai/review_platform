#!/usr/bin/env python3
"""
Script to check user status in production database
Run this on the production server to diagnose login issues
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine
from app.db.models import User
from sqlalchemy.orm import sessionmaker

def check_user_status():
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check specific user
        user_email = 'ramin@assadollahi.de'
        user = session.query(User).filter(User.email == user_email).first()
        
        print(f"=== User Status Check ===")
        print(f"Email: {user_email}")
        
        if user:
            print(f"✓ User found in database")
            print(f"  Role: {user.role}")
            print(f"  Is verified: {user.is_verified}")
            print(f"  Has password hash: {bool(user.password_hash)}")
            print(f"  Created at: {user.created_at}")
            print(f"  Last login: {user.last_login}")
            print(f"  Company: {user.company_name}")
            print(f"  Preferred language: {user.preferred_language}")
        else:
            print(f"✗ User not found in database")
            
        # Check total user count
        total_users = session.query(User).count()
        print(f"\n=== Database Statistics ===")
        print(f"Total users in database: {total_users}")
        
        # List all users
        print(f"\n=== All Users ===")
        all_users = session.query(User).all()
        for u in all_users:
            status = "✓ verified" if u.is_verified else "✗ unverified"
            print(f"  {u.email} ({u.role}) - {status}")
        
        # Check database connection
        print(f"\n=== Database Connection ===")
        print(f"Database engine: {engine}")
        print(f"Connection successful: ✓")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    check_user_status()