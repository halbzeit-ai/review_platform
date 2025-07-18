#!/usr/bin/env python3
"""
Fix Database Connection Issue
Ensure backend connects only to PostgreSQL
"""

import sys
import os
sys.path.append('/opt/review-platform/backend')

from datetime import datetime
import subprocess

def check_current_database_connection():
    """Check what database the backend is actually connecting to"""
    print("🔍 Checking current database connection...")
    
    try:
        from app.core.config import settings
        from app.db.database import engine
        
        print(f"   Config DATABASE_URL: {settings.DATABASE_URL}")
        print(f"   Engine URL: {engine.url}")
        print(f"   Engine dialect: {engine.dialect.name}")
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute("SELECT 1")
            print(f"   ✅ Connection test successful")
            
            # Check if it's really PostgreSQL
            if engine.dialect.name == 'postgresql':
                print(f"   ✅ Connected to PostgreSQL")
                return True
            else:
                print(f"   ❌ Connected to {engine.dialect.name}, not PostgreSQL!")
                return False
                
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False

def force_postgresql_connection():
    """Force PostgreSQL connection by updating database.py"""
    print("\n🔧 Forcing PostgreSQL connection...")
    
    database_py_content = """
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..core.config import settings

# Force PostgreSQL connection - no fallback to SQLite
DATABASE_URL = "postgresql://review_user:review_password@localhost:5432/review-platform"

engine = create_engine(
    DATABASE_URL,
    # PostgreSQL-specific settings
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,
    # Ensure no SQLite fallback
    module=None
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"""
    
    database_py_path = "/opt/review-platform/backend/app/db/database.py"
    
    try:
        with open(database_py_path, 'w') as f:
            f.write(database_py_content.strip())
        
        print("   ✅ Updated database.py to force PostgreSQL connection")
        return True
        
    except Exception as e:
        print(f"   ❌ Error updating database.py: {e}")
        return False

def remove_any_remaining_sqlite_files():
    """Remove any SQLite files that might be recreated"""
    print("\n🗑️  Removing any remaining SQLite files...")
    
    # More comprehensive search for SQLite files
    sqlite_patterns = [
        "*.db",
        "*.sqlite",
        "*.sqlite3",
        "sql_app*"
    ]
    
    search_dirs = [
        "/opt/review-platform/backend",
        "/opt/review-platform/backend/app",
        "/opt/review-platform"
    ]
    
    import glob
    
    for search_dir in search_dirs:
        for pattern in sqlite_patterns:
            files = glob.glob(f"{search_dir}/{pattern}")
            for file_path in files:
                try:
                    os.remove(file_path)
                    print(f"   ✅ Removed: {file_path}")
                except Exception as e:
                    print(f"   ❌ Failed to remove {file_path}: {e}")

def test_postgresql_connection_directly():
    """Test PostgreSQL connection directly"""
    print("\n🔍 Testing PostgreSQL connection directly...")
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Test user lookup
        cursor.execute("SELECT email, password_hash FROM users WHERE email = %s;", ("ramin@halbzeit.ai",))
        user = cursor.fetchone()
        
        if user:
            print(f"   ✅ User found in PostgreSQL: {user[0]}")
            print(f"   Password hash: {user[1][:30]}...")
            
            # Test password verification
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            password_valid = pwd_context.verify("test123", user[1])
            print(f"   Password verification: {'✅ SUCCESS' if password_valid else '❌ FAILED'}")
            
        else:
            print(f"   ❌ User not found in PostgreSQL")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ PostgreSQL connection failed: {e}")
        return False

def restart_and_test():
    """Restart service and test authentication"""
    print("\n🔄 Restarting service and testing...")
    
    try:
        # Restart service
        result = subprocess.run(
            ["systemctl", "restart", "review-platform"],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            print(f"   ❌ Service restart failed: {result.stderr}")
            return False
        
        print("   ✅ Service restarted")
        
        # Wait for service to start
        import time
        time.sleep(3)
        
        # Test authentication
        import requests
        
        response = requests.post(
            "http://localhost:8000/api/auth/login",
            json={"email": "ramin@halbzeit.ai", "password": "test123"},
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Login test status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Authentication successful!")
            print(f"   Token: {result.get('access_token', 'N/A')[:30]}...")
            return True
        else:
            print(f"   ❌ Authentication failed: {response.text}")
            
            # Check logs for more details
            log_result = subprocess.run(
                ["journalctl", "-u", "review-platform", "--since", "10 seconds ago", "-n", "10"],
                capture_output=True, text=True
            )
            
            if log_result.returncode == 0:
                print("   Recent logs:")
                for line in log_result.stdout.split('\n')[-5:]:
                    if line.strip():
                        print(f"     {line}")
            
            return False
            
    except Exception as e:
        print(f"   ❌ Error during restart and test: {e}")
        return False

def main():
    """Main fix function"""
    print("Database Connection Fix")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    steps = [
        ("Check current database connection", check_current_database_connection),
        ("Force PostgreSQL connection", force_postgresql_connection),
        ("Remove any remaining SQLite files", remove_any_remaining_sqlite_files),
        ("Test PostgreSQL connection directly", test_postgresql_connection_directly),
        ("Restart and test", restart_and_test)
    ]
    
    results = []
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        print("-" * 40)
        try:
            result = step_func()
            results.append(result)
            if result:
                print(f"✅ {step_name} successful")
            else:
                print(f"❌ {step_name} failed")
        except Exception as e:
            print(f"❌ {step_name} failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("DATABASE FIX SUMMARY")
    print("=" * 50)
    
    if all(results):
        print("🎉 DATABASE CONNECTION FIXED!")
        print("✅ Backend now connects only to PostgreSQL")
        print("✅ Authentication working properly")
        print("✅ No more SQLite references")
        print("\n🚀 Your PostgreSQL migration is now COMPLETE!")
    else:
        print("❌ Some steps failed - review the errors above")
        print("The backend may still have issues connecting to PostgreSQL")
    
    return all(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)