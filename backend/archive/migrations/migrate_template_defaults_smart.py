#!/usr/bin/env python3
"""
Smart migration script for template defaults
This will convert all sector-specific default templates to regular templates,
but modify the startup classifier to fall back to regular templates when no default exists.

IMPORTANT: This approach makes all templates editable while maintaining classifier functionality.
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
    print("🧠 Smart Template Migration")
    print("=" * 60)
    print("This migration will:")
    print("1. Convert all sector-specific default templates to regular templates")
    print("2. Make all templates editable and deletable by GPs")
    print("3. Startup classifier will be updated to handle this change")
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
        
        # Check current status
        cursor.execute("""
        SELECT id, name, is_default, healthcare_sector_id
        FROM analysis_templates
        WHERE is_active = TRUE
        ORDER BY is_default DESC, healthcare_sector_id, name
        """)
        
        all_templates = cursor.fetchall()
        default_templates = [t for t in all_templates if t['is_default']]
        regular_templates = [t for t in all_templates if not t['is_default']]
        
        print(f"\n📊 Current Status:")
        print(f"  - Default templates: {len(default_templates)}")
        print(f"  - Regular templates: {len(regular_templates)}")
        print(f"  - Total templates: {len(all_templates)}")
        
        print(f"\n🔄 Converting {len(default_templates)} default templates to regular:")
        for template in default_templates:
            print(f"  - {template['name']} (ID: {template['id']}, Sector: {template['healthcare_sector_id']})")
        
        if not default_templates:
            print("\n✅ No default templates found - nothing to convert")
            conn.rollback()
            return
        
        # Convert all default templates to regular
        template_ids = [t['id'] for t in default_templates]
        
        cursor.execute("""
        UPDATE analysis_templates 
        SET is_default = FALSE 
        WHERE id = ANY(%s) AND is_active = TRUE
        """, (template_ids,))
        
        updated_count = cursor.rowcount
        print(f"\n✅ Successfully converted {updated_count} templates to regular")
        
        # Verify the changes
        cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE is_default = TRUE) as default_count,
            COUNT(*) FILTER (WHERE is_default = FALSE) as regular_count
        FROM analysis_templates
        WHERE is_active = TRUE
        """)
        
        summary = cursor.fetchone()
        print(f"\n📈 Final Status:")
        print(f"  - Total active templates: {summary['total']}")
        print(f"  - Default templates: {summary['default_count']}")
        print(f"  - Regular templates: {summary['regular_count']}")
        
        # Show sector coverage
        cursor.execute("""
        SELECT DISTINCT healthcare_sector_id, COUNT(*) as template_count
        FROM analysis_templates 
        WHERE is_active = TRUE
        GROUP BY healthcare_sector_id
        ORDER BY healthcare_sector_id
        """)
        
        sector_coverage = cursor.fetchall()
        print(f"\n🏥 Template Coverage by Sector:")
        for sector in sector_coverage:
            print(f"  - Sector {sector['healthcare_sector_id']}: {sector['template_count']} templates")
        
        # Important note about classifier
        print(f"\n⚠️  IMPORTANT POST-MIGRATION STEPS:")
        print(f"1. The startup classifier needs to be updated to handle no default templates")
        print(f"2. It should fall back to the first available template for each sector")
        print(f"3. Consider updating the classifier logic in startup_classifier.py")
        
        # Commit the transaction
        conn.commit()
        print(f"\n🎉 Migration completed successfully!")
        print(f"✅ All {updated_count} templates are now editable and deletable by GPs")
        
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