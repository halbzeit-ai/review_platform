#!/usr/bin/env python3
"""
Migration runner script to execute SQL migrations via FastAPI database connection
"""

import sys
import os
from sqlalchemy import text

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.database import SessionLocal

def run_migration(sql_file_path):
    """Run a SQL migration file"""
    print(f"🚀 Running migration: {sql_file_path}")
    
    # Read the SQL file
    try:
        with open(sql_file_path, 'r') as f:
            sql_content = f.read()
    except FileNotFoundError:
        print(f"❌ Migration file not found: {sql_file_path}")
        return False
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Execute the SQL
        print("📝 Executing SQL migration...")
        db.execute(text(sql_content))
        db.commit()
        print("✅ Migration executed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python run_migration.py <sql_file_path>")
        print("Example: python run_migration.py migrations/add_standard_template.sql")
        sys.exit(1)
    
    sql_file = sys.argv[1]
    success = run_migration(sql_file)
    sys.exit(0 if success else 1)