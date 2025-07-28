#!/usr/bin/env python3
"""
Database migration script to add preferred_language column to users table.
Run this script to update the database schema for language support.
"""

import sqlite3
import sys
from pathlib import Path

def add_language_preference_column():
    """Add preferred_language column to users table with default 'de'"""
    
    # Database path
    db_path = Path(__file__).parent / "sql_app.db"
    
    if not db_path.exists():
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'preferred_language' in columns:
            print("✅ preferred_language column already exists")
            conn.close()
            return True
        
        # Add the column
        print("🔄 Adding preferred_language column to users table...")
        cursor.execute("""
            ALTER TABLE users 
            ADD COLUMN preferred_language TEXT DEFAULT 'de'
        """)
        
        # Update existing users to have German as default
        cursor.execute("""
            UPDATE users 
            SET preferred_language = 'de' 
            WHERE preferred_language IS NULL
        """)
        
        # Commit changes
        conn.commit()
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'preferred_language' in columns:
            print("✅ preferred_language column added successfully")
            
            # Show current user count
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"📊 Updated {user_count} existing users with German default")
            
            conn.close()
            return True
        else:
            print("❌ Failed to add preferred_language column")
            conn.close()
            return False
            
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting database migration for language preferences...")
    
    success = add_language_preference_column()
    
    if success:
        print("🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        print("💥 Migration failed!")
        sys.exit(1)