#!/usr/bin/env python3
"""
Database reset script - completely wipes and recreates the database
WARNING: This will delete ALL data!
"""
import os
import sys
import sqlite3
from sqlalchemy import create_engine

# Add backend to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.db.models import Base
from app.core.config import settings

def reset_database():
    """Completely reset the database - delete all tables and data"""
    
    # Change to backend directory for database operations
    backend_dir = os.path.join(os.path.dirname(__file__), '..', 'backend')
    os.chdir(backend_dir)
    db_path = "sql_app.db"
    
    print("🗑️  Database Reset Script")
    print("=" * 50)
    print(f"Database file: {db_path}")
    
    # Confirm deletion
    print("\n⚠️  WARNING: This will DELETE ALL DATA!")
    print("- All users will be removed")
    print("- All pitch decks will be removed") 
    print("- All reviews will be removed")
    print("- All questions/answers will be removed")
    
    confirm = input("\nType 'DELETE' to confirm: ")
    if confirm != "DELETE":
        print("❌ Reset cancelled")
        return False
    
    # Backup existing database
    if os.path.exists(db_path):
        backup_path = f"{db_path}.backup.{int(__import__('time').time())}"
        print(f"\n📦 Creating backup: {backup_path}")
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Backup created: {backup_path}")
    
    # Delete existing database
    if os.path.exists(db_path):
        print(f"\n🗑️  Deleting existing database: {db_path}")
        os.remove(db_path)
        print("✅ Database file deleted")
    else:
        print(f"\n📝 No existing database found at {db_path}")
    
    # Create new database with all tables
    print("\n🔨 Creating new database with schema...")
    engine = create_engine(settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    print("✅ New database created with all tables")
    
    # Verify database structure
    print("\n🔍 Verifying database structure...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print(f"📋 Created tables: {[table[0] for table in tables]}")
    
    # Check Users table structure
    cursor.execute("PRAGMA table_info(users)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    print(f"👤 Users table columns: {column_names}")
    
    # Verify email verification fields are present
    required_fields = ['verification_token', 'verification_token_expires', 'is_verified']
    missing_fields = [field for field in required_fields if field not in column_names]
    
    if missing_fields:
        print(f"❌ Missing required fields: {missing_fields}")
        conn.close()
        return False
    else:
        print("✅ All email verification fields present")
    
    conn.close()
    
    print("\n🎉 Database reset completed successfully!")
    print("\nNext steps:")
    print("1. Restart your backend service:")
    print("   sudo systemctl restart review-platform")
    print("2. Register as the first user (will be assigned GP role)")
    print("3. Verify your email address")
    print("4. Start testing the platform")
    
    return True

if __name__ == "__main__":
    success = reset_database()
    exit(0 if success else 1)