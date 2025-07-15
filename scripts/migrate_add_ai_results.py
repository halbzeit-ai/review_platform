#!/usr/bin/env python3
"""
Migration script to add ai_analysis_results column to pitch_decks table
Run this on production server to fix the database schema
"""

import sqlite3
import os
import sys

def migrate_database():
    """Add ai_analysis_results column to pitch_decks table"""
    
    db_path = "/opt/review-platform/backend/sql_app.db"
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return False
    
    print(f"✅ Database found: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(pitch_decks)")
        columns = [row[1] for row in cursor.fetchall()]
        
        print(f"Current columns: {columns}")
        
        if 'ai_analysis_results' in columns:
            print("✅ Column 'ai_analysis_results' already exists")
            conn.close()
            return True
        
        # Add the missing column
        print("Adding ai_analysis_results column...")
        cursor.execute("ALTER TABLE pitch_decks ADD COLUMN ai_analysis_results TEXT")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(pitch_decks)")
        columns_after = [row[1] for row in cursor.fetchall()]
        
        print(f"Columns after migration: {columns_after}")
        
        if 'ai_analysis_results' in columns_after:
            conn.commit()
            print("✅ Successfully added ai_analysis_results column")
            success = True
        else:
            print("❌ Failed to add ai_analysis_results column")
            success = False
            
        conn.close()
        return success
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("=== MIGRATING DATABASE SCHEMA ===")
    success = migrate_database()
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("You can now run: python3 scripts/debug_results_issue.py")
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)