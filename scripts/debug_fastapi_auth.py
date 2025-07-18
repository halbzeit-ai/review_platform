#!/usr/bin/env python3
"""
Debug FastAPI Authentication Issue
Check why FastAPI auth is failing when direct database access works
"""

import sys
import os
sys.path.append('/opt/review-platform/backend')

from datetime import datetime
import requests
import json

def test_fastapi_auth_endpoint_directly():
    """Test the FastAPI auth endpoint by making requests with debugging"""
    print("🔍 Testing FastAPI auth endpoint with detailed debugging...")
    
    try:
        # Test the exact request format
        login_data = {
            "email": "ramin@halbzeit.ai",
            "password": "test123"
        }
        
        print(f"   Sending login request...")
        print(f"   Data: {login_data}")
        
        # Make request with detailed debugging
        response = requests.post(
            "http://localhost:8000/api/auth/login",
            json=login_data,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        )
        
        print(f"   Response status: {response.status_code}")
        print(f"   Response headers: {dict(response.headers)}")
        print(f"   Response body: {response.text}")
        
        # Check if it's a detailed error
        if response.status_code == 400:
            try:
                error_data = response.json()
                print(f"   Error detail: {error_data.get('detail', 'No detail')}")
            except:
                print(f"   Error body (not JSON): {response.text}")
        
        return response.status_code == 200
        
    except Exception as e:
        print(f"   ❌ Error testing FastAPI auth: {e}")
        return False

def check_fastapi_logs_realtime():
    """Check FastAPI logs in real-time during authentication"""
    print("\n🔍 Checking FastAPI logs during authentication...")
    
    try:
        import subprocess
        import time
        
        # Start log monitoring in background
        print("   Starting log monitoring...")
        
        # Make the login request
        print("   Making login request...")
        response = requests.post(
            "http://localhost:8000/api/auth/login",
            json={"email": "ramin@halbzeit.ai", "password": "test123"},
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Login response: {response.status_code}")
        
        # Get logs from the last few seconds
        time.sleep(1)
        result = subprocess.run(
            ["journalctl", "-u", "review-platform", "--since", "10 seconds ago", "-n", "50"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            logs = result.stdout
            print("   Recent logs during authentication:")
            print("   " + "-" * 50)
            for line in logs.split('\n'):
                if line.strip():
                    print(f"   {line}")
            print("   " + "-" * 50)
        else:
            print("   ❌ Could not retrieve logs")
            
    except Exception as e:
        print(f"   ❌ Error checking logs: {e}")

def test_auth_with_backend_imports():
    """Test authentication by importing the backend auth logic directly"""
    print("\n🔍 Testing authentication with backend imports...")
    
    try:
        from app.api.auth import pwd_context
        from app.db.database import get_db
        from app.db.models import User
        from sqlalchemy.orm import Session
        
        # Get database session
        db_session = next(get_db())
        
        # Find user (exactly like backend does)
        print("   Finding user in database...")
        user = db_session.query(User).filter(User.email == "ramin@halbzeit.ai").first()
        
        if not user:
            print("   ❌ User not found")
            return False
            
        print(f"   ✅ User found: {user.email}")
        print(f"   User verified: {user.is_verified}")
        print(f"   Password hash: {user.password_hash[:30]}...")
        
        # Test password verification (exactly like backend does)
        print("   Testing password verification...")
        password_valid = pwd_context.verify("test123", user.password_hash)
        print(f"   Password verification: {'✅ SUCCESS' if password_valid else '❌ FAILED'}")
        
        # Test email verification check
        if not user.is_verified:
            print("   ❌ Email not verified - would return 403")
            return False
        
        print("   ✅ All authentication checks pass!")
        
        db_session.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing with backend imports: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_database_table_in_sqlite():
    """Check if the recreated SQLite database has the user table"""
    print("\n🔍 Checking recreated SQLite database...")
    
    try:
        import sqlite3
        
        sqlite_path = "/opt/review-platform/backend/sql_app.db"
        if not os.path.exists(sqlite_path):
            print("   ✅ No SQLite database found")
            return True
        
        conn = sqlite3.connect(sqlite_path)
        cursor = conn.cursor()
        
        # Check if users table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        table_exists = cursor.fetchone() is not None
        
        if table_exists:
            print("   ⚠️  Users table exists in SQLite")
            
            # Check if there are any users
            cursor.execute("SELECT COUNT(*) FROM users;")
            user_count = cursor.fetchone()[0]
            print(f"   SQLite users count: {user_count}")
            
            if user_count > 0:
                cursor.execute("SELECT email FROM users;")
                emails = [row[0] for row in cursor.fetchall()]
                print(f"   SQLite user emails: {emails}")
                
                # This would explain the issue!
                if "ramin@halbzeit.ai" in emails:
                    print("   🚨 FOUND THE ISSUE: User exists in SQLite with potentially different password!")
                    
                    cursor.execute("SELECT password_hash FROM users WHERE email = ?;", ("ramin@halbzeit.ai",))
                    sqlite_hash = cursor.fetchone()[0]
                    print(f"   SQLite password hash: {sqlite_hash[:30]}...")
                    
                    return False
        else:
            print("   ✅ No users table in SQLite")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking SQLite: {e}")
        return False

def main():
    """Main FastAPI authentication debug"""
    print("FastAPI Authentication Debug")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test authentication endpoint
    auth_works = test_fastapi_auth_endpoint_directly()
    
    # Check logs during authentication
    check_fastapi_logs_realtime()
    
    # Test with backend imports
    backend_auth_works = test_auth_with_backend_imports()
    
    # Check SQLite database
    no_sqlite_conflict = check_database_table_in_sqlite()
    
    print("\n" + "=" * 60)
    print("FASTAPI AUTHENTICATION DEBUG SUMMARY")
    print("=" * 60)
    
    if auth_works:
        print("✅ FastAPI authentication is working!")
    else:
        print("❌ FastAPI authentication is failing")
        
        if backend_auth_works:
            print("✅ Backend authentication logic works correctly")
            print("🤔 The issue is in the FastAPI request handling")
        else:
            print("❌ Backend authentication logic has issues")
        
        if not no_sqlite_conflict:
            print("🚨 SQLITE CONFLICT DETECTED!")
            print("The backend might be reading from PostgreSQL but writing to SQLite")
            print("Or there's a dual database situation")
    
    return auth_works

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)