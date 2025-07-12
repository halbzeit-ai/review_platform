#!/usr/bin/env python3
"""
Database migration script to add email verification fields to User table
"""
import sqlite3
import os
from datetime import datetime

def migrate_database():
    """Add email verification fields to existing User table"""
    
    # Path to the SQLite database
    db_path = "sql_app.db"
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found. Creating new database with full schema.")
        return True
    
    print(f"Migrating database: {db_path}")
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if the new columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        print(f"Current columns in users table: {columns}")
        
        # Add verification_token column if it doesn't exist
        if 'verification_token' not in columns:
            print("Adding verification_token column...")
            cursor.execute("ALTER TABLE users ADD COLUMN verification_token TEXT")
            print("✓ Added verification_token column")
        else:
            print("✓ verification_token column already exists")
        
        # Add verification_token_expires column if it doesn't exist
        if 'verification_token_expires' not in columns:
            print("Adding verification_token_expires column...")
            cursor.execute("ALTER TABLE users ADD COLUMN verification_token_expires DATETIME")
            print("✓ Added verification_token_expires column")
        else:
            print("✓ verification_token_expires column already exists")
        
        # Commit changes
        conn.commit()
        
        # Verify the migration
        cursor.execute("PRAGMA table_info(users)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        print(f"Updated columns in users table: {updated_columns}")
        
        # Count users and show verification status
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_verified = 1")
        verified_count = cursor.fetchone()[0]
        
        print(f"\nDatabase migration completed successfully!")
        print(f"Total users: {user_count}")
        print(f"Verified users: {verified_count}")
        print(f"Unverified users: {user_count - verified_count}")
        
        if user_count > verified_count:
            print("\n⚠️  Note: Existing users are unverified by default.")
            print("   They will need to use the 'resend verification' feature to verify their emails.")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"Migration failed: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("=== Email Verification Migration ===")
    success = migrate_database()
    if success:
        print("\n🎉 Migration completed successfully!")
        print("\nNext steps:")
        print("1. Add SMTP credentials to your .env file:")
        print("   SMTP_PASSWORD=your_hetzner_email_password")
        print("2. Test the email verification flow")
    else:
        print("\n❌ Migration failed!")
        exit(1)