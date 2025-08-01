#!/usr/bin/env python3
"""
Export pipeline prompts from development database to SQL file
Run this on development machine
"""

import psycopg2
import sys

def export_pipeline_prompts():
    """Export pipeline prompts to SQL insert statements"""
    
    dev_conn_str = "postgresql://dev_user:!dev_Halbzeit1024@65.108.32.143:5432/review_dev"
    
    try:
        print("Connecting to development database...")
        dev_conn = psycopg2.connect(dev_conn_str)
        dev_cur = dev_conn.cursor()
        
        # Get all pipeline prompts
        dev_cur.execute("SELECT stage_name, prompt_text, is_active, created_by, prompt_type, prompt_name, is_enabled FROM pipeline_prompts ORDER BY stage_name")
        prompts = dev_cur.fetchall()
        
        print(f"Found {len(prompts)} pipeline prompts")
        
        # Generate SQL file
        sql_file = "/opt/review-platform-dev/scripts/pipeline_prompts_production.sql"
        with open(sql_file, 'w') as f:
            f.write("-- Pipeline prompts for production database\n")
            f.write("-- Generated from development database\n\n")
            
            for stage_name, prompt_text, is_active, created_by, prompt_type, prompt_name, is_enabled in prompts:
                # Escape single quotes
                stage_name_escaped = stage_name.replace("'", "''") if stage_name else ''
                prompt_text_escaped = prompt_text.replace("'", "''") if prompt_text else ''
                created_by_escaped = created_by.replace("'", "''") if created_by else 'system'
                prompt_type_escaped = prompt_type.replace("'", "''") if prompt_type else 'extraction'
                prompt_name_escaped = prompt_name.replace("'", "''") if prompt_name else 'Default Prompt'
                
                f.write(f"INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by, prompt_type, prompt_name, is_enabled) VALUES\n")
                f.write(f"('{stage_name_escaped}', '{prompt_text_escaped}', {is_active}, '{created_by_escaped}', '{prompt_type_escaped}', '{prompt_name_escaped}', {is_enabled})\n")
                f.write(f"ON CONFLICT (stage_name) DO UPDATE SET\n")
                f.write(f"prompt_text = EXCLUDED.prompt_text, is_active = EXCLUDED.is_active, prompt_type = EXCLUDED.prompt_type, prompt_name = EXCLUDED.prompt_name, is_enabled = EXCLUDED.is_enabled;\n\n")
        
        print(f"✅ Exported to: {sql_file}")
        print(f"Copy this file to production and run: psql review-platform < pipeline_prompts_production.sql")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")
        sys.exit(1)
        
    finally:
        if 'dev_conn' in locals():
            dev_conn.close()

if __name__ == "__main__":
    export_pipeline_prompts()