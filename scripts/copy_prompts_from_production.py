#!/usr/bin/env python3
"""
Copy prompts from production database to development database
"""

import psycopg2
import sys
from datetime import datetime

# Database configurations
PROD_DB_URL = "postgresql://review_user:review_password@65.108.32.168:5432/review-platform"
DEV_DB_URL = "postgresql://dev_user:!dev_Halbzeit1024@localhost:5432/review_dev"

def copy_prompts():
    """Copy all prompts from production to development"""
    
    try:
        print("🔗 Connecting to production database...")
        prod_conn = psycopg2.connect(PROD_DB_URL)
        prod_cur = prod_conn.cursor()
        
        print("🔗 Connecting to development database...")
        dev_conn = psycopg2.connect(DEV_DB_URL)
        dev_cur = dev_conn.cursor()
        
        # First, check if prompts table exists in dev
        print("🔍 Checking if prompts table exists in development...")
        dev_cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'prompts'
            );
        """)
        
        table_exists = dev_cur.fetchone()[0]
        
        if not table_exists:
            print("📋 Creating prompts table in development...")
            # Get the table structure from production
            prod_cur.execute("""
                SELECT column_name, data_type, character_maximum_length, 
                       is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'prompts'
                ORDER BY ordinal_position;
            """)
            
            columns = prod_cur.fetchall()
            
            # Build CREATE TABLE statement
            create_sql = "CREATE TABLE prompts ("
            col_defs = []
            
            for col in columns:
                col_name, data_type, max_length, is_nullable, default = col
                col_def = f"{col_name} {data_type}"
                
                if max_length:
                    col_def += f"({max_length})"
                    
                if is_nullable == 'NO':
                    col_def += " NOT NULL"
                    
                if default:
                    col_def += f" DEFAULT {default}"
                    
                col_defs.append(col_def)
            
            create_sql += ", ".join(col_defs) + ");"
            
            dev_cur.execute(create_sql)
            dev_conn.commit()
            print("✅ Prompts table created")
        else:
            print("✅ Prompts table already exists")
            
        # Clear existing prompts in development
        print("🧹 Clearing existing prompts in development...")
        dev_cur.execute("DELETE FROM prompts")
        
        # Fetch all prompts from production
        print("📥 Fetching prompts from production...")
        prod_cur.execute("""
            SELECT name, content, version, is_active, created_at, updated_at
            FROM prompts
            ORDER BY name, version
        """)
        
        prompts = prod_cur.fetchall()
        print(f"📊 Found {len(prompts)} prompts in production")
        
        # Insert prompts into development
        print("📤 Copying prompts to development...")
        for prompt in prompts:
            name, content, version, is_active, created_at, updated_at = prompt
            
            dev_cur.execute("""
                INSERT INTO prompts (name, content, version, is_active, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (name, content, version, is_active, created_at, updated_at))
            
            status = "✅ active" if is_active else "⏸️  inactive"
            print(f"   {status} {name} v{version}")
        
        dev_conn.commit()
        
        # Verify the copy
        print("\n🔍 Verifying prompts in development...")
        dev_cur.execute("""
            SELECT name, version, is_active, 
                   CASE WHEN LENGTH(content) > 50 
                        THEN SUBSTRING(content, 1, 50) || '...' 
                        ELSE content 
                   END as content_preview
            FROM prompts
            WHERE is_active = true
            ORDER BY name
        """)
        
        active_prompts = dev_cur.fetchall()
        print(f"\n📋 Active prompts in development ({len(active_prompts)}):")
        for prompt in active_prompts:
            name, version, is_active, preview = prompt
            print(f"   • {name} v{version}: {preview}")
        
        print(f"\n✅ Successfully copied {len(prompts)} prompts from production to development!")
        
        # Close connections
        prod_cur.close()
        prod_conn.close()
        dev_cur.close()
        dev_conn.close()
        
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection error: {e}")
        print("\n🔍 Troubleshooting:")
        print("   1. Check if production allows connections from dev server")
        print("   2. Verify database credentials")
        print("   3. Check network connectivity")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error copying prompts: {e}")
        sys.exit(1)

if __name__ == "__main__":
    copy_prompts()