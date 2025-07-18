#!/usr/bin/env python3
"""
Add data_source field to pitch_decks table for dojo feature
"""

import sys
import os
import logging

# Add the parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.insert(0, backend_dir)

try:
    from app.db.database import get_db
    from sqlalchemy import text
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this script from the backend directory")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_data_source_field():
    """Add data_source field to pitch_decks table"""
    try:
        db = next(get_db())
        
        # Check if column already exists
        check_column_query = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'pitch_decks' 
        AND column_name = 'data_source'
        """)
        
        existing_column = db.execute(check_column_query).fetchone()
        
        if existing_column:
            logger.info("✅ Column data_source already exists")
            return True
        
        # Add the column
        alter_query = text("""
        ALTER TABLE pitch_decks 
        ADD COLUMN data_source VARCHAR(50) DEFAULT 'startup'
        """)
        
        db.execute(alter_query)
        
        # Add index for efficient filtering
        index_query = text("""
        CREATE INDEX IF NOT EXISTS idx_pitch_decks_data_source 
        ON pitch_decks(data_source)
        """)
        
        db.execute(index_query)
        
        # Add check constraint to ensure valid values
        constraint_query = text("""
        ALTER TABLE pitch_decks ADD CONSTRAINT chk_data_source 
        CHECK (data_source IN ('startup', 'dojo'))
        """)
        
        db.execute(constraint_query)
        
        # Update existing records to have 'startup' as default
        update_query = text("""
        UPDATE pitch_decks SET data_source = 'startup' WHERE data_source IS NULL
        """)
        
        db.execute(update_query)
        
        db.commit()
        logger.info("✅ Successfully added data_source field with constraints and index")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        db.rollback()
        return False

def main():
    """Run data_source field migration"""
    logger.info("🚀 Adding data_source field to pitch_decks table")
    logger.info("=" * 60)
    
    success = add_data_source_field()
    
    logger.info("=" * 60)
    if success:
        logger.info("🎉 Data source field migration completed successfully!")
        logger.info("✅ Added data_source column with 'startup' default")
        logger.info("✅ Added index for efficient filtering")
        logger.info("✅ Added check constraint for valid values")
        logger.info("✅ Updated existing records")
    else:
        logger.error("❌ Migration failed")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)