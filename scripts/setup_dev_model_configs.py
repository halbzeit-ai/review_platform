#!/usr/bin/env python3
"""
Set up model configurations in development database
Matches production behavior but with smaller models for development
"""

import psycopg2
import os
import sys
from datetime import datetime

# Development database configuration
DEV_DB_URL = "postgresql://dev_user:!dev_Halbzeit1024@localhost:5432/review_dev"

def setup_model_configs():
    """Create model_configs table and insert development models"""
    
    try:
        # Connect to development database
        conn = psycopg2.connect(DEV_DB_URL)
        cur = conn.cursor()
        
        print("🔍 Checking if model_configs table exists...")
        
        # Check if table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'model_configs'
            );
        """)
        
        table_exists = cur.fetchone()[0]
        
        if not table_exists:
            print("📋 Creating model_configs table...")
            cur.execute("""
                CREATE TABLE model_configs (
                    id SERIAL PRIMARY KEY,
                    model_name VARCHAR(255) NOT NULL,
                    model_type VARCHAR(50) NOT NULL,
                    is_active BOOLEAN DEFAULT true,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            print("✅ Table created successfully")
        else:
            print("✅ Table already exists")
        
        # Clear existing configurations
        print("🧹 Clearing existing model configurations...")
        cur.execute("DELETE FROM model_configs")
        
        # Insert development model configurations
        print("📝 Inserting development model configurations...")
        
        models = [
            ('gemma2:2b', 'vision'),
            ('gemma2:2b', 'text'),
            ('phi3:mini', 'scoring')
        ]
        
        for model_name, model_type in models:
            cur.execute("""
                INSERT INTO model_configs (model_name, model_type, is_active)
                VALUES (%s, %s, true)
            """, (model_name, model_type))
            print(f"   ✅ Added {model_type} model: {model_name}")
        
        conn.commit()
        
        # Verify configurations
        print("\n🔍 Verifying model configurations:")
        cur.execute("""
            SELECT model_type, model_name, is_active 
            FROM model_configs 
            WHERE is_active = true
            ORDER BY model_type
        """)
        
        for row in cur.fetchall():
            model_type, model_name, is_active = row
            print(f"   {model_type}: {model_name} (active: {is_active})")
        
        print("\n✅ Model configurations set up successfully!")
        print("\n📌 Next steps:")
        print("   1. Make sure these models are installed on GPU: ollama pull gemma2:2b phi3:mini")
        print("   2. Update GPU .env.development to use correct database connection")
        print("   3. Remove SKIP_DB_MODEL_CONFIG from environment")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error setting up model configs: {e}")
        sys.exit(1)

if __name__ == "__main__":
    setup_model_configs()