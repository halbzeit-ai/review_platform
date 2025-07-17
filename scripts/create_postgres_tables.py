#!/usr/bin/env python3
"""
Create PostgreSQL tables using SQLAlchemy models
This script creates the database schema before data migration
"""

import sys
import os
sys.path.append('/opt/review-platform/backend')

from sqlalchemy import create_engine
from app.db.database import Base
from app.db import models  # This imports all models

def create_tables():
    """Create all tables in PostgreSQL database"""
    
    # Database connection
    DATABASE_URL = "postgresql://review_user:review_password@localhost:5432/review-platform"
    
    print("Creating PostgreSQL tables...")
    print(f"Database URL: {DATABASE_URL}")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL)
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        print("✅ All tables created successfully!")
        
        # List created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        print(f"Created tables: {tables}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def main():
    """Main function"""
    print("PostgreSQL Table Creation Tool")
    print("=" * 50)
    
    success = create_tables()
    
    if success:
        print("\n✅ Database schema created successfully!")
        print("You can now run the migration script to copy data.")
        sys.exit(0)
    else:
        print("\n❌ Failed to create database schema!")
        sys.exit(1)

if __name__ == "__main__":
    main()