#!/usr/bin/env python3
"""
Import prompts into development database from production export
Run this on the DEVELOPMENT server after copying the export file
"""

import psycopg2
import os
import sys

DEV_DB_URL = "postgresql://dev_user:!dev_Halbzeit1024@localhost:5432/review_dev"
IMPORT_FILE = "/tmp/production_prompts.sql"

def import_prompts():
    """Import prompts from production export"""
    
    if not os.path.exists(IMPORT_FILE):
        print(f"❌ Import file not found: {IMPORT_FILE}")
        print("   Please copy the export file from production first:")
        print("   scp root@65.108.32.168:/tmp/production_prompts.sql /tmp/")
        sys.exit(1)
    
    try:
        print("🔗 Connecting to development database...")
        conn = psycopg2.connect(DEV_DB_URL)
        cur = conn.cursor()
        
        # Check if pipeline_prompts table exists
        print("🔍 Checking pipeline_prompts table...")
        try:
            cur.execute("SELECT COUNT(*) FROM pipeline_prompts")
            print("✅ Pipeline_prompts table exists")
        except psycopg2.Error:
            print("❌ Pipeline_prompts table does not exist")
            print("Please run: sudo -u postgres psql review_dev -c \"CREATE TABLE pipeline_prompts...\"")
            sys.exit(1)
        
        # Clear existing prompts
        print("🧹 Clearing existing prompts...")
        cur.execute("DELETE FROM pipeline_prompts")
        
        # Read and execute import file
        print("📤 Importing prompts...")
        with open(IMPORT_FILE, 'r') as f:
            sql_content = f.read()
            
        # Execute the SQL
        cur.execute(sql_content)
        conn.commit()
        
        # Verify import
        print("\n🔍 Verifying imported prompts...")
        cur.execute("""
            SELECT stage_name, is_active,
                   LENGTH(prompt_text) as content_length
            FROM pipeline_prompts
            WHERE is_active = true
            ORDER BY stage_name
        """)
        
        prompts = cur.fetchall()
        print(f"\n✅ Imported {len(prompts)} active prompts:")
        for stage_name, is_active, length in prompts:
            print(f"   • {stage_name} ({length} chars)")
        
        # Show all prompt names
        cur.execute("SELECT DISTINCT stage_name FROM pipeline_prompts ORDER BY stage_name")
        all_names = [row[0] for row in cur.fetchall()]
        
        print(f"\n📋 All prompt types: {', '.join(all_names)}")
        
        cur.close()
        conn.close()
        
        print("\n✅ Prompts imported successfully!")
        print("🚀 The GPU server should now find all prompts in the database")
        
    except Exception as e:
        print(f"❌ Error importing prompts: {e}")
        sys.exit(1)

if __name__ == "__main__":
    import_prompts()