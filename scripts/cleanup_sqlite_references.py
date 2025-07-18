#!/usr/bin/env python3
"""
Cleanup SQLite References
Remove all SQLite references and ensure PostgreSQL-only setup
"""

import os
import sys
import shutil
import subprocess
from datetime import datetime

def remove_sqlite_files():
    """Remove all SQLite database files"""
    print("🗑️  Removing SQLite database files...")
    
    sqlite_files = [
        "/opt/review-platform/backend/sql_app.db",
        "/opt/review-platform/backend/app/sql_app.db",
        "/opt/review-platform/sql_app.db",
        "sql_app.db"
    ]
    
    for file_path in sqlite_files:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                print(f"   ✅ Removed: {file_path}")
            except Exception as e:
                print(f"   ❌ Failed to remove {file_path}: {e}")
        else:
            print(f"   ✅ Not found: {file_path}")

def clean_database_configuration():
    """Clean up database configuration to be PostgreSQL-only"""
    print("\n🔧 Cleaning database configuration...")
    
    # Check current database.py
    database_py_path = "/opt/review-platform/backend/app/db/database.py"
    
    try:
        with open(database_py_path, 'r') as f:
            content = f.read()
        
        print(f"   Current database.py content:")
        print(f"   " + "-" * 40)
        print(content)
        print(f"   " + "-" * 40)
        
        # Check if it contains any SQLite references
        if "sqlite" in content.lower():
            print("   ⚠️  Found SQLite references in database.py")
        else:
            print("   ✅ No SQLite references in database.py")
            
    except Exception as e:
        print(f"   ❌ Error reading database.py: {e}")

def check_main_app_initialization():
    """Check main app initialization for database creation"""
    print("\n🔍 Checking main app initialization...")
    
    main_py_path = "/opt/review-platform/backend/app/main.py"
    
    try:
        with open(main_py_path, 'r') as f:
            content = f.read()
        
        print(f"   Current main.py content:")
        print(f"   " + "-" * 40)
        print(content)
        print(f"   " + "-" * 40)
        
        # Check for Base.metadata.create_all
        if "Base.metadata.create_all" in content:
            print("   ⚠️  Found Base.metadata.create_all - this creates tables automatically")
            print("   This might be creating SQLite tables!")
        else:
            print("   ✅ No automatic table creation found")
            
    except Exception as e:
        print(f"   ❌ Error reading main.py: {e}")

def update_main_app_for_postgresql_only():
    """Update main.py to be PostgreSQL-only"""
    print("\n🔧 Updating main.py for PostgreSQL-only setup...")
    
    main_py_path = "/opt/review-platform/backend/app/main.py"
    
    try:
        with open(main_py_path, 'r') as f:
            content = f.read()
        
        # Remove or comment out automatic table creation
        if "Base.metadata.create_all(bind=engine)" in content:
            print("   Commenting out automatic table creation...")
            
            new_content = content.replace(
                "Base.metadata.create_all(bind=engine)",
                "# Base.metadata.create_all(bind=engine)  # Disabled - using PostgreSQL with manual migrations"
            )
            
            # Write the updated content
            with open(main_py_path, 'w') as f:
                f.write(new_content)
            
            print("   ✅ Updated main.py to disable automatic table creation")
            return True
        else:
            print("   ✅ No automatic table creation to disable")
            return True
            
    except Exception as e:
        print(f"   ❌ Error updating main.py: {e}")
        return False

def verify_postgresql_connection():
    """Verify PostgreSQL connection is working"""
    print("\n🔍 Verifying PostgreSQL connection...")
    
    try:
        import psycopg2
        
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"   ✅ PostgreSQL connection successful")
        print(f"   Found {len(tables)} tables: {tables}")
        
        # Check user data
        cursor.execute("SELECT COUNT(*) FROM users;")
        user_count = cursor.fetchone()[0]
        print(f"   Users in PostgreSQL: {user_count}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ PostgreSQL connection failed: {e}")
        return False

def create_postgresql_only_database_py():
    """Create a clean PostgreSQL-only database.py"""
    print("\n📝 Creating PostgreSQL-only database configuration...")
    
    database_py_content = '''
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from ..core.config import settings

# PostgreSQL-only configuration
engine = create_engine(
    settings.DATABASE_URL,
    # PostgreSQL-specific optimizations
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False  # Set to True for SQL debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
'''
    
    database_py_path = "/opt/review-platform/backend/app/db/database.py"
    
    try:
        with open(database_py_path, 'w') as f:
            f.write(database_py_content.strip())
        
        print("   ✅ Created PostgreSQL-only database.py")
        return True
        
    except Exception as e:
        print(f"   ❌ Error creating database.py: {e}")
        return False

def restart_application():
    """Restart the application service"""
    print("\n🔄 Restarting application service...")
    
    try:
        result = subprocess.run(
            ["systemctl", "restart", "review-platform"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            print("   ✅ Application service restarted successfully")
            
            # Check status
            status_result = subprocess.run(
                ["systemctl", "is-active", "review-platform"],
                capture_output=True, text=True
            )
            
            if status_result.returncode == 0:
                print("   ✅ Application service is active")
                return True
            else:
                print("   ❌ Application service failed to start")
                return False
        else:
            print(f"   ❌ Failed to restart service: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"   ❌ Error restarting service: {e}")
        return False

def test_authentication_after_cleanup():
    """Test authentication after cleanup"""
    print("\n🔍 Testing authentication after cleanup...")
    
    try:
        import requests
        import time
        
        # Wait a moment for service to fully start
        time.sleep(2)
        
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
            return False
            
    except Exception as e:
        print(f"   ❌ Authentication test error: {e}")
        return False

def main():
    """Main cleanup function"""
    print("SQLite References Cleanup")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    steps = [
        ("Remove SQLite files", remove_sqlite_files),
        ("Check database configuration", clean_database_configuration),
        ("Check main app initialization", check_main_app_initialization),
        ("Update main.py for PostgreSQL-only", update_main_app_for_postgresql_only),
        ("Create PostgreSQL-only database.py", create_postgresql_only_database_py),
        ("Verify PostgreSQL connection", verify_postgresql_connection),
        ("Restart application service", restart_application),
        ("Test authentication after cleanup", test_authentication_after_cleanup)
    ]
    
    results = []
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        print("-" * 50)
        try:
            result = step_func()
            results.append(result)
            if result:
                print(f"✅ {step_name} completed successfully")
            else:
                print(f"❌ {step_name} failed")
        except Exception as e:
            print(f"❌ {step_name} failed with error: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print("SQLITE CLEANUP SUMMARY")
    print("=" * 60)
    
    success_count = sum(results)
    total_count = len(results)
    
    if success_count == total_count:
        print("🎉 SQLITE CLEANUP COMPLETE!")
        print("✅ All SQLite references removed")
        print("✅ PostgreSQL-only configuration active")
        print("✅ Authentication should now work properly")
        print("\n🚀 Your system is now 100% PostgreSQL!")
    else:
        print(f"⚠️  {success_count}/{total_count} steps completed")
        print("Some cleanup steps failed - please review the errors above")
    
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)