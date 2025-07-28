#!/usr/bin/env python3
"""
Debug script to check healthcare templates database tables via FastAPI database connection
"""

import sys
import os
import asyncio
from sqlalchemy import text
import json

# Add the app directory to Python path so we can import from it
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.database import SessionLocal
from app.core.config import settings

def check_table_exists(db, table_name):
    """Check if a table exists"""
    try:
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = :table_name
            );
        """), {"table_name": table_name})
        return result.fetchone()[0]
    except Exception as e:
        print(f"❌ Error checking if table {table_name} exists: {e}")
        return False

def check_table_data(db, table_name):
    """Check data in a table"""
    try:
        # Get row count
        count_result = db.execute(text(f"SELECT COUNT(*) FROM {table_name};"))
        count = count_result.fetchone()[0]
        
        # Get sample data
        if count > 0:
            sample_result = db.execute(text(f"SELECT * FROM {table_name} LIMIT 3;"))
            sample_data = sample_result.fetchall()
            return count, sample_data
        else:
            return count, []
    except Exception as e:
        return None, f"Error: {e}"

def main():
    print("🔍 Healthcare Templates Database Debug Script (via FastAPI)")
    print("=" * 60)
    
    print(f"📋 Database URL: {settings.DATABASE_URL}")
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Test basic connection
        print("\n🔌 Testing database connection...")
        test_result = db.execute(text("SELECT 1 as test;"))
        test_value = test_result.fetchone()[0]
        if test_value == 1:
            print("✅ Database connection successful!")
        else:
            print("❌ Database connection failed!")
            return
        
        # Tables to check
        tables_to_check = [
            'healthcare_sectors',
            'analysis_templates',
            'template_chapters',
            'chapter_questions',
            'gp_template_customizations',
            'template_performance',
            'classification_performance',
            'startup_classifications',
            'pipeline_prompts'
        ]
        
        print("\n📋 Checking table existence:")
        existing_tables = []
        for table in tables_to_check:
            exists = check_table_exists(db, table)
            status = "✅ EXISTS" if exists else "❌ MISSING"
            print(f"  {table}: {status}")
            if exists:
                existing_tables.append(table)
        
        print("\n📊 Checking table data:")
        for table in existing_tables:
            count, sample = check_table_data(db, table)
            if count is not None:
                print(f"\n  {table}:")
                print(f"    📈 Row count: {count}")
                if count > 0 and sample:
                    print(f"    📄 Sample data (first 3 rows):")
                    for i, row in enumerate(sample):
                        # Convert row to dict for better display
                        row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(zip(row.keys(), row))
                        print(f"      Row {i+1}: {row_dict}")
                elif count == 0:
                    print(f"    ⚠️  Table is empty")
            else:
                print(f"    ❌ Error reading {table}: {sample}")
        
        print("\n🔍 Testing the specific API queries:")
        
        # Test healthcare sectors query (same as API)
        print("\n1️⃣ Healthcare Sectors Query:")
        try:
            query = text("""
            SELECT id, name, display_name, description, keywords, subcategories, 
                   confidence_threshold, regulatory_requirements, is_active
            FROM healthcare_sectors
            WHERE is_active = TRUE
            ORDER BY display_name
            """)
            result = db.execute(query)
            rows = result.fetchall()
            print(f"✅ Query successful! Found {len(rows)} active healthcare sectors")
            for row in rows:
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(zip(row.keys(), row))
                print(f"  - {row_dict.get('display_name', 'N/A')} (ID: {row_dict.get('id', 'N/A')})")
                # Try to parse JSON fields
                try:
                    keywords = json.loads(row_dict.get('keywords', '[]')) if row_dict.get('keywords') else []
                    print(f"    Keywords: {keywords[:3]}...")  # Show first 3 keywords
                except:
                    print(f"    Keywords: [parsing error]")
                    
        except Exception as e:
            print(f"❌ Healthcare sectors query failed: {e}")
        
        # Test performance metrics query (same as API)
        print("\n2️⃣ Performance Metrics Query:")
        try:
            query = text("""
            SELECT t.name, COUNT(tp.id) as usage_count, 
                   AVG(tp.average_confidence) as avg_confidence,
                   AVG(tp.gp_rating) as avg_rating
            FROM analysis_templates t
            LEFT JOIN template_performance tp ON t.id = tp.template_id
            WHERE t.is_active = TRUE
            GROUP BY t.id, t.name
            ORDER BY usage_count DESC
            """)
            result = db.execute(query)
            rows = result.fetchall()
            print(f"✅ Performance metrics query successful! Found {len(rows)} templates")
            for row in rows[:5]:  # Show first 5
                row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(zip(row.keys(), row))
                print(f"  - {row_dict.get('name', 'N/A')}: {row_dict.get('usage_count', 0)} uses, "
                      f"avg confidence: {row_dict.get('avg_confidence', 0):.2f}")
        except Exception as e:
            print(f"❌ Performance metrics query failed: {e}")
        
        # Test template details query
        print("\n3️⃣ Template Details Query (if templates exist):")
        try:
            # First get a template ID
            template_query = text("SELECT id FROM analysis_templates WHERE is_active = TRUE LIMIT 1")
            template_result = db.execute(template_query)
            template_row = template_result.fetchone()
            
            if template_row:
                template_id = template_row[0]
                print(f"Testing with template ID: {template_id}")
                
                # Test the template details query
                query = text("""
                SELECT t.id, t.name, t.description, t.template_version, t.specialized_analysis,
                       s.name as sector_name, s.display_name as sector_display_name
                FROM analysis_templates t
                JOIN healthcare_sectors s ON t.healthcare_sector_id = s.id
                WHERE t.id = :template_id AND t.is_active = TRUE
                """)
                result = db.execute(query, {"template_id": template_id})
                row = result.fetchone()
                
                if row:
                    row_dict = dict(row._mapping) if hasattr(row, '_mapping') else dict(zip(row.keys(), row))
                    print(f"✅ Template details query successful!")
                    print(f"  Template: {row_dict.get('name', 'N/A')}")
                    print(f"  Sector: {row_dict.get('sector_display_name', 'N/A')}")
                else:
                    print(f"❌ No template found with ID {template_id}")
            else:
                print("⚠️  No active templates found to test with")
        except Exception as e:
            print(f"❌ Template details query failed: {e}")
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()
    
    print("\n✅ Debug script completed!")
    
    # Show migration files available
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    if os.path.exists(migrations_dir):
        print(f"\n📁 Available migration files in {migrations_dir}:")
        migration_files = [f for f in os.listdir(migrations_dir) if f.endswith('.sql')]
        for migration in sorted(migration_files):
            print(f"  - {migration}")
    else:
        print(f"\n⚠️  Migrations directory not found at {migrations_dir}")

if __name__ == "__main__":
    main()