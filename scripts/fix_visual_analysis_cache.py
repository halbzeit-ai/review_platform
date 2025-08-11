#!/usr/bin/env python3
"""
Migration script to fix visual_analysis_cache table structure.
Updates from pitch_deck_id to document_id to match current model definition.
"""

import sys
import os

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.config import get_settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    settings = get_settings()
    
    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    with SessionLocal() as db:
        logger.info("Starting visual_analysis_cache migration...")
        
        try:
            # Check current table structure
            result = db.execute(text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'visual_analysis_cache'
                AND column_name IN ('pitch_deck_id', 'document_id')
                ORDER BY column_name
            """)).fetchall()
            
            current_columns = [row[0] for row in result]
            logger.info(f"Current columns in visual_analysis_cache: {current_columns}")
            
            if 'pitch_deck_id' in current_columns and 'document_id' not in current_columns:
                logger.info("Migration needed: Adding document_id column and updating references")
                
                # Step 1: Add the new document_id column
                logger.info("Adding document_id column...")
                db.execute(text("""
                    ALTER TABLE visual_analysis_cache 
                    ADD COLUMN document_id INTEGER
                """))
                db.commit()
                
                # Step 2: Update document_id based on pitch_deck_id mapping
                # For this migration, we'll set document_id to NULL since we don't have a direct mapping
                # This is acceptable since these are cache entries that can be regenerated
                logger.info("Setting document_id values...")
                db.execute(text("""
                    UPDATE visual_analysis_cache 
                    SET document_id = NULL
                    WHERE document_id IS NULL
                """))
                db.commit()
                
                # Step 3: Drop the old pitch_deck_id column
                logger.info("Dropping pitch_deck_id column...")
                db.execute(text("""
                    ALTER TABLE visual_analysis_cache 
                    DROP COLUMN pitch_deck_id
                """))
                db.commit()
                
                # Step 4: Add foreign key constraint to document_id
                logger.info("Adding foreign key constraint...")
                db.execute(text("""
                    ALTER TABLE visual_analysis_cache 
                    ALTER COLUMN document_id SET NOT NULL,
                    ADD CONSTRAINT fk_visual_analysis_cache_document_id 
                    FOREIGN KEY (document_id) REFERENCES project_documents(id) ON DELETE CASCADE
                """))
                db.commit()
                
                # Step 5: Add index on document_id
                logger.info("Adding index on document_id...")
                db.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_visual_analysis_cache_document_id 
                    ON visual_analysis_cache(document_id)
                """))
                db.commit()
                
                logger.info("✅ Migration completed successfully!")
                
            elif 'document_id' in current_columns and 'pitch_deck_id' not in current_columns:
                logger.info("✅ Table already migrated - document_id column exists")
                
            elif 'pitch_deck_id' in current_columns and 'document_id' in current_columns:
                logger.info("⚠️  Both columns exist - manual cleanup may be needed")
                
            else:
                logger.info("❌ Unexpected table structure")
                
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            db.rollback()
            raise
            
        finally:
            logger.info("Migration script completed")

if __name__ == "__main__":
    main()