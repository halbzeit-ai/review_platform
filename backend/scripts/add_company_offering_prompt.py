#!/usr/bin/env python3
"""
Script to add company_offering prompt to database
Run this on the production server - uses FastAPI database configuration
"""

import os
import sys
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.core.config import settings
from app.db.database import SessionLocal

def add_company_offering_prompt():
    """Add company_offering prompt to pipeline_prompts table"""
    
    # The complete prompt including role context from pitch_deck_analyzer.py
    company_offering_prompt = """You are an analyst working at a Venture Capital company. Here is the descriptions of a startup's pitchdeck. Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company."""
    
    try:
        # Use FastAPI database connection (same as the application)
        print("Connecting to database...")
        print(f"Database URL: {settings.DATABASE_URL}")
        
        db = SessionLocal()
        
        # Check if company_offering prompt already exists
        check_query = text("""
        SELECT id FROM pipeline_prompts 
        WHERE stage_name = :stage_name AND is_active = TRUE
        """)
        
        result = db.execute(check_query, {"stage_name": "company_offering"}).fetchone()
        
        if result:
            print("company_offering prompt already exists in database")
            print(f"Existing prompt ID: {result[0]}")
            
            # Update the existing prompt
            update_query = text("""
            UPDATE pipeline_prompts 
            SET prompt_text = :prompt_text, updated_at = CURRENT_TIMESTAMP 
            WHERE stage_name = :stage_name AND is_active = TRUE
            """)
            
            db.execute(update_query, {
                "prompt_text": company_offering_prompt,
                "stage_name": "company_offering"
            })
            print("Updated existing company_offering prompt")
            
        else:
            # Insert new company_offering prompt
            insert_query = text("""
            INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by, created_at, updated_at) 
            VALUES (:stage_name, :prompt_text, :is_active, :created_by, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """)
            
            db.execute(insert_query, {
                "stage_name": "company_offering",
                "prompt_text": company_offering_prompt,
                "is_active": True,
                "created_by": "system"
            })
            print("Inserted new company_offering prompt")
        
        # Commit the transaction
        db.commit()
        
        # Verify the insertion/update
        verify_query = text("""
        SELECT id, stage_name, SUBSTR(prompt_text, 1, 100) as prompt_preview, is_active, created_by, created_at, updated_at
        FROM pipeline_prompts 
        WHERE stage_name = :stage_name
        """)
        
        result = db.execute(verify_query, {"stage_name": "company_offering"}).fetchone()
        
        if result:
            print("\n✅ Success! company_offering prompt is now in database:")
            print(f"  ID: {result[0]}")
            print(f"  Stage: {result[1]}")
            print(f"  Prompt preview: {result[2]}...")
            print(f"  Active: {result[3]}")
            print(f"  Created by: {result[4]}")
            print(f"  Created at: {result[5]}")
            print(f"  Updated at: {result[6]}")
        else:
            print("❌ Error: Failed to verify prompt insertion")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"Error type: {type(e)}")
        if 'db' in locals():
            db.rollback()
        return False
    finally:
        if 'db' in locals():
            db.close()
        print("Database connection closed")
    
    return True

if __name__ == "__main__":
    print("🚀 Adding company_offering prompt to PostgreSQL database")
    print("=" * 60)
    
    success = add_company_offering_prompt()
    
    if success:
        print("\n🎉 Script completed successfully!")
        print("The company_offering prompt is now available in the UI")
        sys.exit(0)
    else:
        print("\n💥 Script failed!")
        sys.exit(1)