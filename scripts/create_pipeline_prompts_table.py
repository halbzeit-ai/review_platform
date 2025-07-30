#!/usr/bin/env python3
"""
Create pipeline_prompts table in development database
"""

import psycopg2
import sys

DEV_DB_URL = "postgresql://dev_user:!dev_Halbzeit1024@localhost:5432/review_dev"

def create_pipeline_prompts_table():
    """Create the pipeline_prompts table"""
    
    try:
        print("🔗 Connecting to development database...")
        conn = psycopg2.connect(DEV_DB_URL)
        cur = conn.cursor()
        
        print("📋 Creating pipeline_prompts table...")
        cur.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_prompts (
                id SERIAL PRIMARY KEY,
                stage_name VARCHAR(255) NOT NULL,
                prompt_text TEXT NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT true,
                created_by VARCHAR(255) DEFAULT 'system',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        print("📋 Creating index...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_pipeline_prompts_stage_active 
            ON pipeline_prompts(stage_name, is_active);
        """)
        
        conn.commit()
        print("✅ Table and index created successfully")
        
        # Verify table exists
        cur.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'pipeline_prompts' 
            ORDER BY ordinal_position;
        """)
        
        columns = cur.fetchall()
        print(f"\n📋 Table structure ({len(columns)} columns):")
        for col_name, data_type in columns:
            print(f"   • {col_name}: {data_type}")
        
        cur.close()
        conn.close()
        
        print("\n✅ Pipeline prompts table is ready!")
        print("📌 Now you can run: python scripts/import_prompts_development.py")
        
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_pipeline_prompts_table()