#!/usr/bin/env python3
"""
Fix PostgreSQL Schema Inconsistencies
Fixes column name mismatches between migration scripts and verification script
"""

import psycopg2
import sys
from datetime import datetime

def check_table_schema(table_name):
    """Check the actual schema of a table"""
    print(f"Checking schema for table: {table_name}")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Get column information
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = %s AND table_schema = 'public'
            ORDER BY ordinal_position;
        """, (table_name,))
        
        columns = cursor.fetchall()
        
        if columns:
            print(f"   Columns in {table_name}:")
            for col in columns:
                col_name, data_type, nullable, default = col
                nullable_str = "NULL" if nullable == "YES" else "NOT NULL"
                default_str = f", default: {default}" if default else ""
                print(f"     - {col_name}: {data_type} {nullable_str}{default_str}")
        else:
            print(f"   ❌ Table {table_name} not found or has no columns")
        
        cursor.close()
        conn.close()
        return columns
        
    except Exception as e:
        print(f"   ❌ Error checking schema for {table_name}: {e}")
        return None

def fix_template_chapters_schema():
    """Fix the template_chapters table schema"""
    print("\n1. Fixing template_chapters table schema...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Check if analysis_template_id column exists
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'template_chapters' AND column_name = 'analysis_template_id';
        """)
        has_analysis_template_id = cursor.fetchone() is not None
        
        if not has_analysis_template_id:
            print("   Adding missing analysis_template_id column...")
            cursor.execute("""
                ALTER TABLE template_chapters 
                ADD COLUMN analysis_template_id INTEGER REFERENCES analysis_templates(id);
            """)
            
            # Update existing records if needed
            cursor.execute("""
                UPDATE template_chapters 
                SET analysis_template_id = 1 
                WHERE analysis_template_id IS NULL;
            """)
            
            print("   ✅ Added analysis_template_id column")
        else:
            print("   ✅ analysis_template_id column already exists")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error fixing template_chapters schema: {e}")
        return False

def fix_pipeline_prompts_schema():
    """Fix the pipeline_prompts table schema"""
    print("\n2. Fixing pipeline_prompts table schema...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Check current columns
        cursor.execute("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'pipeline_prompts';
        """)
        columns = [row[0] for row in cursor.fetchall()]
        
        print(f"   Current columns: {columns}")
        
        # Add missing columns if needed
        missing_columns = []
        
        if 'prompt_type' not in columns:
            missing_columns.append(('prompt_type', 'VARCHAR(50)'))
        
        if 'prompt_name' not in columns:
            missing_columns.append(('prompt_name', 'VARCHAR(255)'))
        
        if 'is_enabled' not in columns:
            missing_columns.append(('is_enabled', 'BOOLEAN DEFAULT TRUE'))
        
        for col_name, col_type in missing_columns:
            print(f"   Adding missing column: {col_name}")
            cursor.execute(f"""
                ALTER TABLE pipeline_prompts 
                ADD COLUMN {col_name} {col_type};
            """)
        
        if missing_columns:
            # Update existing records with default values
            cursor.execute("""
                UPDATE pipeline_prompts 
                SET prompt_type = 'extraction', 
                    prompt_name = 'Default Prompt',
                    is_enabled = TRUE
                WHERE prompt_type IS NULL;
            """)
            print("   ✅ Added missing columns and updated existing data")
        else:
            print("   ✅ All required columns already exist")
        
        conn.commit()
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error fixing pipeline_prompts schema: {e}")
        return False

def verify_fixes():
    """Verify that the fixes worked"""
    print("\n3. Verifying schema fixes...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Test the queries that were failing
        print("   Testing template_chapters query...")
        cursor.execute("""
            SELECT tc.id, tc.title, at.name as template_name, tc.order_index
            FROM template_chapters tc
            JOIN analysis_templates at ON tc.analysis_template_id = at.id
            ORDER BY at.name, tc.order_index
            LIMIT 3;
        """)
        chapters = cursor.fetchall()
        print(f"   ✅ template_chapters query works - found {len(chapters)} chapters")
        
        print("   Testing pipeline_prompts query...")
        cursor.execute("""
            SELECT id, prompt_type, prompt_name, is_enabled, created_at
            FROM pipeline_prompts 
            ORDER BY prompt_type, prompt_name
            LIMIT 3;
        """)
        prompts = cursor.fetchall()
        print(f"   ✅ pipeline_prompts query works - found {len(prompts)} prompts")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Verification failed: {e}")
        return False

def main():
    """Main schema fix function"""
    print("PostgreSQL Schema Inconsistencies Fix")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check current schemas
    print("Current table schemas:")
    print("-" * 30)
    check_table_schema('template_chapters')
    check_table_schema('pipeline_prompts')
    
    # Apply fixes
    print("\nApplying schema fixes:")
    print("-" * 30)
    
    fixes = [
        fix_template_chapters_schema(),
        fix_pipeline_prompts_schema(),
        verify_fixes()
    ]
    
    print("\n" + "=" * 50)
    print("SCHEMA FIX SUMMARY")
    print("=" * 50)
    
    if all(fixes):
        print("✅ All schema fixes applied successfully!")
        print("\nYou can now run the data integrity verification script again:")
        print("python scripts/verify_data_integrity.py")
        return True
    else:
        print("❌ Some schema fixes failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)