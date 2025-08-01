#!/usr/bin/env python3
"""
Migrate pipeline prompts from development to production database
Run this script from the development machine
"""

import psycopg2
import sys
import os

def migrate_pipeline_prompts():
    """Copy pipeline prompts from development to production database"""
    
    # Development database connection
    dev_conn_str = "postgresql://dev_user:!dev_Halbzeit1024@65.108.32.143:5432/review_dev"
    
    # Production database connection  
    prod_conn_str = "postgresql://review_user:SecureProductionPassword2024!@65.108.32.168:5432/review-platform"
    
    try:
        # Connect to development database
        print("Connecting to development database...")
        dev_conn = psycopg2.connect(dev_conn_str)
        dev_cur = dev_conn.cursor()
        
        # Connect to production database
        print("Connecting to production database...")
        prod_conn = psycopg2.connect(prod_conn_str)
        prod_cur = prod_conn.cursor()
        
        # Get all pipeline prompts from development
        print("Fetching pipeline prompts from development...")
        dev_cur.execute("SELECT stage_name, prompt_text, description, created_at FROM pipeline_prompts ORDER BY stage_name")
        prompts = dev_cur.fetchall()
        
        print(f"Found {len(prompts)} pipeline prompts in development")
        
        # Insert into production database
        print("Migrating to production...")
        migrated_count = 0
        
        for stage_name, prompt_text, description, created_at in prompts:
            try:
                prod_cur.execute(
                    """INSERT INTO pipeline_prompts (stage_name, prompt_text, description, created_at) 
                       VALUES (%s, %s, %s, %s) 
                       ON CONFLICT (stage_name) DO UPDATE SET
                       prompt_text = EXCLUDED.prompt_text,
                       description = EXCLUDED.description""",
                    (stage_name, prompt_text, description, created_at)
                )
                migrated_count += 1
                print(f"  ✅ {stage_name}")
            except Exception as e:
                print(f"  ❌ {stage_name}: {e}")
        
        # Commit changes
        prod_conn.commit()
        
        # Verify migration
        prod_cur.execute("SELECT COUNT(*) FROM pipeline_prompts")
        prod_count = prod_cur.fetchone()[0]
        
        print(f"\n✅ Migration completed!")
        print(f"   Migrated: {migrated_count} prompts")
        print(f"   Production total: {prod_count} prompts")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
        
    finally:
        if 'dev_conn' in locals():
            dev_conn.close()
        if 'prod_conn' in locals():
            prod_conn.close()

if __name__ == "__main__":
    migrate_pipeline_prompts()