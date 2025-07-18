#!/usr/bin/env python3
"""
Professional migration script for startup name extraction feature
Handles both database schema migration and prompt insertion
"""

import sys
import os
sys.path.append('/home/ramin/halbzeit-ai/review_platform/backend')

from app.db.database import get_db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_database_migration():
    """Add ai_extracted_startup_name column to pitch_decks table"""
    try:
        db = next(get_db())
        
        # Check if column already exists
        check_column_query = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'pitch_decks' 
        AND column_name = 'ai_extracted_startup_name'
        """)
        
        existing_column = db.execute(check_column_query).fetchone()
        
        if existing_column:
            logger.info("✅ Column ai_extracted_startup_name already exists")
            return True
        
        # Add the column
        alter_query = text("""
        ALTER TABLE pitch_decks 
        ADD COLUMN ai_extracted_startup_name VARCHAR(255) DEFAULT NULL
        """)
        
        db.execute(alter_query)
        
        # Add index for efficient searching
        index_query = text("""
        CREATE INDEX IF NOT EXISTS idx_pitch_decks_ai_extracted_startup_name 
        ON pitch_decks(ai_extracted_startup_name)
        """)
        
        db.execute(index_query)
        
        db.commit()
        logger.info("✅ Successfully added ai_extracted_startup_name column and index")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")
        db.rollback()
        return False

def add_startup_name_prompt():
    """Add startup name extraction prompt to pipeline_prompts table"""
    try:
        db = next(get_db())
        
        # Check if prompt already exists
        check_query = text("""
        SELECT id FROM pipeline_prompts 
        WHERE stage_name = 'startup_name_extraction' AND is_active = TRUE
        """)
        
        existing = db.execute(check_query).fetchone()
        
        if existing:
            logger.info("✅ startup_name_extraction prompt already exists")
            return True
        
        # Insert new prompt
        insert_query = text("""
        INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by, created_at, updated_at)
        VALUES (
            'startup_name_extraction',
            'Please find the name of the startup in the pitchdeck. Deliver only the name, no conversational text around it.',
            TRUE,
            'system',
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
        """)
        
        db.execute(insert_query)
        db.commit()
        
        logger.info("✅ Successfully added startup_name_extraction prompt")
        
        # Verify insertion
        verify_query = text("""
        SELECT stage_name, prompt_text FROM pipeline_prompts 
        WHERE stage_name = 'startup_name_extraction' AND is_active = TRUE
        """)
        
        result = db.execute(verify_query).fetchone()
        if result:
            logger.info(f"✅ Verified: {result[0]} - {result[1]}")
            return True
        else:
            logger.error("❌ Failed to verify prompt insertion")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error adding startup name prompt: {e}")
        db.rollback()
        return False

def main():
    """Run complete migration for startup name extraction feature"""
    logger.info("🚀 Starting startup name extraction feature migration")
    logger.info("=" * 60)
    
    # Step 1: Run database migration
    logger.info("Step 1: Running database schema migration...")
    migration_success = run_database_migration()
    
    if not migration_success:
        logger.error("❌ Database migration failed, aborting")
        return False
    
    # Step 2: Add startup name prompt
    logger.info("Step 2: Adding startup name extraction prompt...")
    prompt_success = add_startup_name_prompt()
    
    if not prompt_success:
        logger.error("❌ Prompt insertion failed, aborting")
        return False
    
    # Success summary
    logger.info("=" * 60)
    logger.info("🎉 Startup name extraction feature migration completed successfully!")
    logger.info("✅ Database schema updated")
    logger.info("✅ Pipeline prompt added")
    logger.info("✅ Ready for frontend deployment")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Restart backend service")
    logger.info("2. Restart frontend service")
    logger.info("3. Test the new startup name extraction in the web UI")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)