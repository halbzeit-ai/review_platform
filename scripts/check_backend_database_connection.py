#!/usr/bin/env python3
"""
Check Backend Database Connection
Verify which database the FastAPI backend is actually using
"""

import sys
import os
sys.path.append('/opt/review-platform/backend')

from datetime import datetime
import psycopg2

def check_backend_config():
    """Check backend configuration"""
    print("🔍 Checking backend configuration...")
    
    try:
        from app.core.config import settings
        
        print(f"   DATABASE_URL: {settings.DATABASE_URL}")
        print(f"   Project name: {settings.PROJECT_NAME}")
        
        # Check if it's pointing to PostgreSQL
        if "postgresql://" in settings.DATABASE_URL:
            print("   ✅ Backend configured for PostgreSQL")
        elif "sqlite://" in settings.DATABASE_URL:
            print("   ❌ Backend still configured for SQLite!")
        else:
            print("   ⚠️  Unknown database configuration")
        
        return settings.DATABASE_URL
        
    except Exception as e:
        print(f"   ❌ Error checking backend config: {e}")
        return None

def test_backend_database_connection():
    """Test the database connection that the backend is using"""
    print("\n🔍 Testing backend database connection...")
    
    try:
        from app.db.database import get_db, engine
        from app.db.models import User
        from sqlalchemy.orm import Session
        
        # Get database session (same as backend)
        db_session = next(get_db())
        
        print(f"   Database engine: {engine.url}")
        print(f"   Database dialect: {engine.dialect.name}")
        
        # Test user query (same as backend auth.py)
        print(f"\n   Testing user query through SQLAlchemy...")
        user = db_session.query(User).filter(User.email == "ramin@halbzeit.ai").first()
        
        if user:
            print(f"   ✅ User found through SQLAlchemy")
            print(f"   User ID: {user.id}")
            print(f"   Email: {user.email}")
            print(f"   Role: {user.role}")
            print(f"   Verified: {user.is_verified}")
            print(f"   Password hash: {user.password_hash[:30]}...")
            
            # Test password verification with backend's context
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            password_valid = pwd_context.verify("test123", user.password_hash)
            print(f"   Password verification: {'✅ SUCCESS' if password_valid else '❌ FAILED'}")
            
            db_session.close()
            return True
        else:
            print(f"   ❌ User NOT found through SQLAlchemy")
            print(f"   This means the backend is reading from a different database!")
            
            # List all users in the backend database
            all_users = db_session.query(User).all()
            print(f"   Users in backend database: {len(all_users)}")
            for u in all_users:
                print(f"     - {u.email} (ID: {u.id})")
            
            db_session.close()
            return False
            
    except Exception as e:
        print(f"   ❌ Error testing backend database: {e}")
        return False

def check_database_file_existence():
    """Check if SQLite database file still exists somewhere"""
    print("\n🔍 Checking for any remaining SQLite database files...")
    
    sqlite_locations = [
        "/opt/review-platform/backend/sql_app.db",
        "/opt/review-platform/backend/app/sql_app.db", 
        "/opt/review-platform/sql_app.db",
        "sql_app.db"
    ]
    
    for location in sqlite_locations:
        if os.path.exists(location):
            print(f"   ⚠️  Found SQLite file: {location}")
            # Check modification time
            mtime = os.path.getmtime(location)
            mod_time = datetime.fromtimestamp(mtime)
            print(f"   Modified: {mod_time}")
        else:
            print(f"   ✅ No SQLite file at: {location}")

def check_environment_variables():
    """Check environment variables that might affect database connection"""
    print("\n🔍 Checking environment variables...")
    
    env_vars = [
        "DATABASE_URL",
        "POSTGRES_DB",
        "POSTGRES_USER", 
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST"
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"   {var}: {value}")
        else:
            print(f"   {var}: Not set")

def test_direct_postgresql_vs_backend():
    """Compare direct PostgreSQL connection with backend connection"""
    print("\n🔍 Comparing direct PostgreSQL vs backend connection...")
    
    # Direct PostgreSQL connection
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE email = %s;", ("ramin@halbzeit.ai",))
        direct_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        print(f"   Direct PostgreSQL: {direct_count} users with email 'ramin@halbzeit.ai'")
        
    except Exception as e:
        print(f"   ❌ Direct PostgreSQL failed: {e}")
        direct_count = -1
    
    # Backend connection
    try:
        from app.db.database import get_db
        from app.db.models import User
        
        db_session = next(get_db())
        backend_count = db_session.query(User).filter(User.email == "ramin@halbzeit.ai").count()
        db_session.close()
        
        print(f"   Backend SQLAlchemy: {backend_count} users with email 'ramin@halbzeit.ai'")
        
    except Exception as e:
        print(f"   ❌ Backend connection failed: {e}")
        backend_count = -1
    
    if direct_count == backend_count and direct_count > 0:
        print(f"   ✅ Both connections return same result")
        return True
    else:
        print(f"   ❌ MISMATCH: Direct={direct_count}, Backend={backend_count}")
        print(f"   🚨 Backend is reading from different database!")
        return False

def main():
    """Main database connection check"""
    print("Backend Database Connection Check")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check backend configuration
    database_url = check_backend_config()
    
    # Check environment variables
    check_environment_variables()
    
    # Check for SQLite files
    check_database_file_existence()
    
    # Test backend database connection
    backend_works = test_backend_database_connection()
    
    # Compare connections
    connections_match = test_direct_postgresql_vs_backend()
    
    print("\n" + "=" * 60)
    print("DATABASE CONNECTION ANALYSIS")
    print("=" * 60)
    
    if backend_works and connections_match:
        print("✅ Backend is correctly connected to PostgreSQL!")
        print("The login issue is something else.")
    else:
        print("❌ BACKEND DATABASE CONNECTION ISSUE FOUND!")
        print("\n🚨 ROOT CAUSE IDENTIFIED:")
        
        if not backend_works:
            print("• Backend cannot find user in its database")
        if not connections_match:
            print("• Backend is reading from different database than expected")
        
        print("\n🔧 SOLUTION:")
        print("• Backend needs to be restarted to pick up new database config")
        print("• Check if there are any remaining SQLite references") 
        print("• Verify DATABASE_URL environment variable")
        print("• Check if backend is still creating/using SQLite database")
        
        print("\n💡 Try restarting the backend service:")
        print("systemctl restart review-platform")
    
    return backend_works and connections_match

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)