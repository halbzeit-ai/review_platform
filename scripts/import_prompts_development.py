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
        
        # Check if prompts table exists
        print("🔍 Checking prompts table...")
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'prompts'
            );
        """)
        
        if not cur.fetchone()[0]:
            print("📋 Creating prompts table...")
            cur.execute("""
                CREATE TABLE prompts (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    content TEXT NOT NULL,
                    version INTEGER DEFAULT 1,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX idx_prompts_name_active ON prompts(name, is_active);
            """)
            conn.commit()
            print("✅ Table created")
        
        # Clear existing prompts
        print("🧹 Clearing existing prompts...")
        cur.execute("DELETE FROM prompts")
        
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
            SELECT name, version, is_active,
                   LENGTH(content) as content_length
            FROM prompts
            WHERE is_active = true
            ORDER BY name
        """)
        
        prompts = cur.fetchall()
        print(f"\n✅ Imported {len(prompts)} active prompts:")
        for name, version, is_active, length in prompts:
            print(f"   • {name} v{version} ({length} chars)")
        
        # Show all prompt names
        cur.execute("SELECT DISTINCT name FROM prompts ORDER BY name")
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