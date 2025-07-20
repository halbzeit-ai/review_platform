#!/usr/bin/env python3
"""
Run migration to add extraction testing tables for dojo functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal, engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the extraction testing tables migration"""
    
    # Read migration SQL
    migration_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "migrations",
        "add_extraction_testing_tables.sql"
    )
    
    if not os.path.exists(migration_file):
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    with open(migration_file, 'r') as f:
        migration_sql = f.read()
    
    db = SessionLocal()
    try:
        logger.info("Running extraction testing tables migration...")
        
        # Execute migration in a transaction
        db.execute(text(migration_sql))
        db.commit()
        
        logger.info("✅ Migration completed successfully!")
        
        # Verify tables were created
        result = db.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('visual_analysis_cache', 'extraction_experiments')
        """)).fetchall()
        
        created_tables = [row[0] for row in result]
        logger.info(f"Created tables: {created_tables}")
        
        if len(created_tables) == 2:
            logger.info("✅ All required tables created successfully")
            return True
        else:
            logger.warning(f"⚠️  Expected 2 tables, created {len(created_tables)}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)