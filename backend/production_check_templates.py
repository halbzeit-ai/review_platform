#!/usr/bin/env python3
"""
Production script to check current template status
Run this on the production server to see what templates exist and their default status
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    """Get PostgreSQL database connection from environment variables"""
    try:
        # Try to get database URL from environment
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            return psycopg2.connect(db_url)
        
        # Fallback to individual environment variables
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432'),
            database=os.getenv('DB_NAME', 'postgres'),
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', '')
        )
        return conn
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return None

def main():
    print("🔍 Production Template Status Check")
    print("=" * 60)
    
    # Connect to database
    conn = get_db_connection()
    if not conn:
        print("❌ Could not connect to database")
        return
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Check all templates with their default status
        cursor.execute("""
        SELECT id, name, is_default, is_active, healthcare_sector_id
        FROM analysis_templates
        WHERE is_active = TRUE
        ORDER BY is_default DESC, name
        """)
        
        result = cursor.fetchall()
        
        print(f"\n📊 Found {len(result)} active templates:")
        
        print("\n🔒 DEFAULT TEMPLATES (is_default = TRUE):")
        default_templates = []
        for row in result:
            if row['is_default']:
                print(f"  ✅ ID {row['id']}: {row['name']} (sector: {row['healthcare_sector_id']})")
                default_templates.append(row)
        
        print(f"\n📝 REGULAR TEMPLATES (is_default = FALSE):")
        regular_templates = []
        for row in result:
            if not row['is_default']:
                print(f"  📄 ID {row['id']}: {row['name']} (sector: {row['healthcare_sector_id']})")
                regular_templates.append(row)
        
        print(f"\n📈 SUMMARY:")
        print(f"  - Default templates: {len(default_templates)}")
        print(f"  - Regular templates: {len(regular_templates)}")
        print(f"  - Total active templates: {len(result)}")
        
        # Find Standard Seven-Chapter Review
        standard_template = None
        for row in result:
            if "standard seven-chapter review" in row['name'].lower():
                standard_template = row
                break
        
        if standard_template:
            print(f"\n🎯 FOUND 'Standard Seven-Chapter Review':")
            print(f"  - ID: {standard_template['id']}")
            print(f"  - Name: {standard_template['name']}")
            print(f"  - is_default: {standard_template['is_default']}")
            print(f"  - Sector ID: {standard_template['healthcare_sector_id']}")
        else:
            print(f"\n⚠️  COULD NOT FIND 'Standard Seven-Chapter Review'")
            print("Available template names:")
            for row in result:
                print(f"  - '{row['name']}'")
        
        # Show what the migration would do
        print(f"\n🔄 MIGRATION PREVIEW:")
        print("Templates that would be converted from DEFAULT to REGULAR:")
        templates_to_convert = []
        for row in result:
            if row['is_default'] and "standard seven-chapter review" not in row['name'].lower():
                print(f"  🔄 ID {row['id']}: {row['name']}")
                templates_to_convert.append(row)
        
        if not templates_to_convert:
            print("  ✅ No templates need to be converted")
        else:
            print(f"\n📋 MIGRATION SUMMARY:")
            print(f"  - Templates to convert: {len(templates_to_convert)}")
            print(f"  - Standard Seven-Chapter Review will remain DEFAULT")
            print(f"  - All others will become REGULAR (editable/deletable)")
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        cursor.close()
        conn.close()
    
    print(f"\n✅ Template status check completed!")

if __name__ == "__main__":
    main()