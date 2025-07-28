#!/usr/bin/env python3
"""
Check current template status to understand what needs to be migrated
"""

import sys
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent))

def check_template_status():
    """Check current template default status"""
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        print("🔍 Current Template Status")
        print("=" * 60)
        
        # Check all templates with their default status
        query = text("""
        SELECT id, name, is_default, is_active, healthcare_sector_id
        FROM analysis_templates
        WHERE is_active = TRUE
        ORDER BY is_default DESC, name
        """)
        
        result = db.execute(query).fetchall()
        
        print(f"\n📊 Found {len(result)} active templates:")
        print("\nDEFAULT TEMPLATES (is_default = TRUE):")
        default_count = 0
        for row in result:
            id, name, is_default, is_active, sector_id = row
            if is_default:
                print(f"  ✅ ID {id}: {name} (sector: {sector_id})")
                default_count += 1
        
        print(f"\nREGULAR TEMPLATES (is_default = FALSE):")
        regular_count = 0
        for row in result:
            id, name, is_default, is_active, sector_id = row
            if not is_default:
                print(f"  📝 ID {id}: {name} (sector: {sector_id})")
                regular_count += 1
        
        print(f"\n📈 Summary:")
        print(f"  - Default templates: {default_count}")
        print(f"  - Regular templates: {regular_count}")
        print(f"  - Total active templates: {len(result)}")
        
        # Check which template is "Standard Seven-Chapter Review"
        standard_template = None
        for row in result:
            id, name, is_default, is_active, sector_id = row
            if "standard seven-chapter review" in name.lower():
                standard_template = row
                break
        
        if standard_template:
            print(f"\n🎯 Found 'Standard Seven-Chapter Review':")
            print(f"  - ID: {standard_template[0]}")
            print(f"  - Name: {standard_template[1]}")
            print(f"  - is_default: {standard_template[2]}")
            print(f"  - Sector ID: {standard_template[4]}")
        else:
            print(f"\n⚠️  Could not find 'Standard Seven-Chapter Review' template")
            print("Available templates:")
            for row in result:
                print(f"  - {row[1]}")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_template_status()