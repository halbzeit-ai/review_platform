#!/usr/bin/env python3
"""
Add startup name extraction prompt to pipeline_prompts table
"""

import sys
import os
sys.path.append('/home/ramin/halbzeit-ai/review_platform/backend')

from app.db.database import get_db
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_startup_name_prompt():
    """Add startup name extraction prompt to database"""
    try:
        db = next(get_db())
        
        # Check if prompt already exists
        check_query = text("""
        SELECT id FROM pipeline_prompts 
        WHERE stage_name = 'startup_name_extraction' AND is_active = TRUE
        """)
        
        existing = db.execute(check_query).fetchone()
        
        if existing:
            logger.info("startup_name_extraction prompt already exists")
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

if __name__ == "__main__":
    success = add_startup_name_prompt()
    sys.exit(0 if success else 1)