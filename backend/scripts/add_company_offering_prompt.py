#!/usr/bin/env python3
"""
Script to add company_offering prompt to PostgreSQL database
Run this on the production server with PostgreSQL connection
"""

import os
import sys
import psycopg2
from datetime import datetime

def add_company_offering_prompt():
    """Add company_offering prompt to pipeline_prompts table"""
    
    # Database connection parameters
    db_params = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': os.getenv('DB_PORT', '5432'),
        'database': os.getenv('DB_NAME', 'review_platform'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASSWORD', '')
    }
    
    # The complete prompt including role context from pitch_deck_analyzer.py
    company_offering_prompt = """You are an analyst working at a Venture Capital company. Here is the descriptions of a startup's pitchdeck. Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company."""
    
    try:
        # Connect to PostgreSQL
        print("Connecting to PostgreSQL database...")
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Check if company_offering prompt already exists
        check_query = """
        SELECT id FROM pipeline_prompts 
        WHERE stage_name = %s AND is_active = TRUE
        """
        
        cursor.execute(check_query, ('company_offering',))
        existing = cursor.fetchone()
        
        if existing:
            print("company_offering prompt already exists in database")
            print(f"Existing prompt ID: {existing[0]}")
            
            # Update the existing prompt
            update_query = """
            UPDATE pipeline_prompts 
            SET prompt_text = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE stage_name = %s AND is_active = TRUE
            """
            
            cursor.execute(update_query, (company_offering_prompt, 'company_offering'))
            print("Updated existing company_offering prompt")
            
        else:
            # Insert new company_offering prompt
            insert_query = """
            INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by, created_at, updated_at) 
            VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """
            
            cursor.execute(insert_query, (
                'company_offering',
                company_offering_prompt,
                True,
                'system'
            ))
            print("Inserted new company_offering prompt")
        
        # Commit the transaction
        conn.commit()
        
        # Verify the insertion/update
        verify_query = """
        SELECT id, stage_name, LEFT(prompt_text, 100) as prompt_preview, is_active, created_by, created_at, updated_at
        FROM pipeline_prompts 
        WHERE stage_name = %s
        """
        
        cursor.execute(verify_query, ('company_offering',))
        result = cursor.fetchone()
        
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
            
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
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