#!/usr/bin/env python3
"""
Check user authentication and reset password if needed
Run this on production server to debug login issues
"""

import sqlite3
import os
import sys
import hashlib
from passlib.context import CryptContext

def check_user_auth():
    """Check user authentication in database"""
    
    db_path = "/opt/review-platform/backend/sql_app.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check users table schema
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    print("Users table columns:")
    for col in columns:
        print(f"  {col[1]} ({col[2]})")
    
    # Get all users
    cursor.execute("SELECT * FROM users ORDER BY id DESC")
    users = cursor.fetchall()
    
    print(f"\nFound {len(users)} users:")
    for user in users:
        print(f"  User {user[0]}: {user[1]} ({user[2]}) - Verified: {user[4] if len(user) > 4 else 'N/A'}")
    
    # Check specific user
    email = "ramin@assadollahi.de"
    cursor.execute("SELECT id, email, role, password_hash, is_verified FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    
    if user:
        user_id, email, role, password_hash, is_verified = user
        print(f"\nUser details for {email}:")
        print(f"  ID: {user_id}")
        print(f"  Role: {role}")
        print(f"  Verified: {is_verified}")
        print(f"  Password hash: {password_hash[:50]}...")
        
        if not is_verified:
            print("  ⚠️  User is not verified! This might be the issue.")
            
            # Verify the user
            cursor.execute("UPDATE users SET is_verified = 1 WHERE email = ?", (email,))
            conn.commit()
            print("  ✅ User verified!")
        
        # Option to reset password
        print(f"\nTo reset password for {email}:")
        print("1. Choose a new password")
        print("2. Run this script with the new password")
        
    else:
        print(f"\n❌ User {email} not found in database")
    
    conn.close()

def reset_password(email, new_password):
    """Reset password for a user"""
    
    db_path = "/opt/review-platform/backend/sql_app.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    try:
        # Use the same password hashing as the backend
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_password = pwd_context.hash(new_password)
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update password and verify user
        cursor.execute(
            "UPDATE users SET password_hash = ?, is_verified = 1 WHERE email = ?",
            (hashed_password, email)
        )
        
        if cursor.rowcount > 0:
            conn.commit()
            print(f"✅ Password reset successfully for {email}")
            print("✅ User verified")
        else:
            print(f"❌ User {email} not found")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Error resetting password: {e}")

if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "reset":
        email = "ramin@assadollahi.de"
        new_password = sys.argv[2]
        reset_password(email, new_password)
    else:
        check_user_auth()
        print("\nTo reset password, run:")
        print("python3 scripts/check_user_auth.py reset YOUR_NEW_PASSWORD")