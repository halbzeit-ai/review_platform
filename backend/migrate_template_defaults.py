#!/usr/bin/env python3
"""
Production migration script to convert templates to regular (non-default)
This will convert all templates except "Standard Seven-Chapter Review" to regular templates

IMPORTANT: Run production_check_templates.py first to see what will be changed!
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
    print("🔄 Template Default Status Migration")
    print("=" * 60)
    print("⚠️  This will convert all templates except 'Standard Seven-Chapter Review' to regular templates")
    print("⚠️  Regular templates can be edited and deleted by GPs")
    print()
    
    # Confirmation prompt
    confirm = input("Are you sure you want to proceed? Type 'YES' to continue: ")
    if confirm != 'YES':
        print("❌ Migration cancelled")
        return
    
    # Connect to database
    conn = get_db_connection()
    if not conn:
        print("❌ Could not connect to database")
        return
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        # Start transaction
        conn.autocommit = False
        
        # First, check current status
        cursor.execute("""
        SELECT id, name, is_default, healthcare_sector_id
        FROM analysis_templates
        WHERE is_active = TRUE AND is_default = TRUE
        ORDER BY name
        """)
        
        default_templates = cursor.fetchall()
        
        print(f"\n📊 Found {len(default_templates)} current default templates:")
        for template in default_templates:
            print(f"  - ID {template['id']}: {template['name']}")
        
        # Find templates to convert (all except Standard Seven-Chapter Review)
        templates_to_convert = []
        standard_template = None
        
        for template in default_templates:
            if "standard seven-chapter review" in template['name'].lower():
                standard_template = template
                print(f"\n🔒 KEEPING as default: {template['name']} (ID: {template['id']})")
            else:
                templates_to_convert.append(template)
        
        if not standard_template:
            print("\n⚠️  WARNING: Could not find 'Standard Seven-Chapter Review' template!")
            print("Available templates:", [t['name'] for t in default_templates])
            rollback_confirm = input("Continue anyway? Type 'YES' to proceed: ")
            if rollback_confirm != 'YES':
                print("❌ Migration cancelled")
                conn.rollback()
                return
        
        if not templates_to_convert:
            print("\n✅ No templates need to be converted")
            conn.rollback()
            return
        
        print(f"\n🔄 CONVERTING {len(templates_to_convert)} templates to regular:")
        
        # Convert templates to regular (is_default = FALSE)
        template_ids = [t['id'] for t in templates_to_convert]
        
        for template in templates_to_convert:
            print(f"  🔄 Converting: {template['name']} (ID: {template['id']})")
        
        # Execute the migration
        cursor.execute("""
        UPDATE analysis_templates 
        SET is_default = FALSE 
        WHERE id = ANY(%s) AND is_active = TRUE
        """, (template_ids,))
        
        updated_count = cursor.rowcount
        print(f"\n✅ Successfully updated {updated_count} templates")
        
        # Verify the changes
        cursor.execute("""
        SELECT id, name, is_default
        FROM analysis_templates
        WHERE id = ANY(%s)
        ORDER BY name
        """, (template_ids,))
        
        updated_templates = cursor.fetchall()
        print(f"\n🔍 VERIFICATION - Updated templates:")
        for template in updated_templates:
            status = "DEFAULT" if template['is_default'] else "REGULAR"
            print(f"  ✅ ID {template['id']}: {template['name']} -> {status}")
        
        # Show final summary
        cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE is_default = TRUE) as default_count,
            COUNT(*) FILTER (WHERE is_default = FALSE) as regular_count
        FROM analysis_templates
        WHERE is_active = TRUE
        """)
        
        summary = cursor.fetchone()
        print(f"\n📈 FINAL SUMMARY:")
        print(f"  - Total active templates: {summary['total']}")
        print(f"  - Default templates: {summary['default_count']}")
        print(f"  - Regular templates: {summary['regular_count']}")
        
        # Commit the transaction
        conn.commit()
        print(f"\n🎉 Migration completed successfully!")
        print(f"✅ {updated_count} templates are now editable and deletable by GPs")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        import traceback
        traceback.print_exc()
    
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()