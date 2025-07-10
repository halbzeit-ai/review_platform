#!/usr/bin/env python3
"""
Database migration script to update schema
"""
import os
import sqlite3
from pathlib import Path

# Database path
DB_PATH = Path("./sql_app.db")

def migrate_database():
    """Migrate database to add missing columns"""
    print("Starting database migration...")
    
    if not DB_PATH.exists():
        print("Database does not exist - will be created automatically")
        return
    
    # Connect to database
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    try:
        # Check if file_path column exists
        cursor.execute("PRAGMA table_info(pitch_decks)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'file_path' not in columns:
            print("Adding file_path column to pitch_decks table...")
            cursor.execute("ALTER TABLE pitch_decks ADD COLUMN file_path TEXT")
            conn.commit()
            print("✅ Added file_path column")
        else:
            print("✅ file_path column already exists")
            
        # Check if processing_status column exists
        if 'processing_status' not in columns:
            print("Adding processing_status column to pitch_decks table...")
            cursor.execute("ALTER TABLE pitch_decks ADD COLUMN processing_status TEXT DEFAULT 'pending'")
            conn.commit()
            print("✅ Added processing_status column")
        else:
            print("✅ processing_status column already exists")
            
        print("Database migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()