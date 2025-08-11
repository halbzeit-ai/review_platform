#!/usr/bin/env python3
"""
Script to clear visual_analysis_cache table and update its structure.
Since we're migrating from pitch_decks to project_documents, 
it's safer to clear the cache than try to migrate references.
Cache entries can be regenerated as needed.
"""

import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        logger.info("Starting visual_analysis_cache cleanup...")
        
        try:
            # Check current record count
            result = db.execute(text("SELECT COUNT(*) FROM visual_analysis_cache")).scalar()
            logger.info(f"Current visual_analysis_cache records: {result}")
            
            # Check current table structure
            columns_result = db.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'visual_analysis_cache'
                AND column_name IN ('pitch_deck_id', 'document_id')
                ORDER BY column_name
            """)).fetchall()
            
            current_columns = [row[0] for row in columns_result]
            logger.info(f"Current columns: {current_columns}")
            
            if 'pitch_deck_id' in current_columns:
                logger.info("Clearing visual_analysis_cache table...")
                db.execute(text("DELETE FROM visual_analysis_cache"))
                db.commit()
                
                logger.info("Updating table structure...")
                
                # Add document_id column if it doesn't exist
                if 'document_id' not in current_columns:
                    db.execute(text("""
                        ALTER TABLE visual_analysis_cache 
                        ADD COLUMN document_id INTEGER
                    """))
                    db.commit()
                
                # Drop pitch_deck_id column
                db.execute(text("""
                    ALTER TABLE visual_analysis_cache 
                    DROP COLUMN pitch_deck_id
                """))
                db.commit()
                
                # Set document_id constraints
                db.execute(text("""
                    ALTER TABLE visual_analysis_cache 
                    ALTER COLUMN document_id SET NOT NULL
                """))
                db.commit()
                
                # Add foreign key constraint
                db.execute(text("""
                    ALTER TABLE visual_analysis_cache 
                    ADD CONSTRAINT fk_visual_analysis_cache_document_id 
                    FOREIGN KEY (document_id) REFERENCES project_documents(id) ON DELETE CASCADE
                """))
                db.commit()
                
                # Add index
                db.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_visual_analysis_cache_document_id 
                    ON visual_analysis_cache(document_id)
                """))
                db.commit()
                
                logger.info("✅ visual_analysis_cache successfully updated!")
                
            else:
                logger.info("✅ visual_analysis_cache already has correct structure")
                
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            db.rollback()
            raise
            
    logger.info("Cleanup completed successfully")

if __name__ == "__main__":
    main()