#!/usr/bin/env python3
"""
Database reset script - completely wipes and recreates the database
WARNING: This will delete ALL data!
Uses only standard library - no virtual environment required
"""
import os
import sys
import sqlite3
import time

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
    
    # Create new database with all tables using raw SQL
    print("\n🔨 Creating new database with schema...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create Users table with email verification fields
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email VARCHAR UNIQUE NOT NULL,
            password_hash VARCHAR NOT NULL,
            company_name VARCHAR,
            role VARCHAR,
            is_verified BOOLEAN DEFAULT 0,
            verification_token VARCHAR,
            verification_token_expires DATETIME,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            last_login DATETIME
        )
    """)
    
    # Create PitchDecks table with all current fields
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pitch_decks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_name VARCHAR,
            file_path VARCHAR,
            s3_url VARCHAR,
            processing_status VARCHAR DEFAULT 'pending',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Create Reviews table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pitch_deck_id INTEGER NOT NULL,
            review_data TEXT,
            s3_review_url VARCHAR,
            status VARCHAR,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (pitch_deck_id) REFERENCES pitch_decks (id)
        )
    """)
    
    # Create Questions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_id INTEGER NOT NULL,
            question_text TEXT,
            asked_by INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (review_id) REFERENCES reviews (id),
            FOREIGN KEY (asked_by) REFERENCES users (id)
        )
    """)
    
    # Create Answers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id INTEGER NOT NULL,
            answer_text TEXT,
            answered_by INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (question_id) REFERENCES questions (id),
            FOREIGN KEY (answered_by) REFERENCES users (id)
        )
    """)
    
    conn.commit()
    conn.close()
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