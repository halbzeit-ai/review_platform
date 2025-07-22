#!/usr/bin/env python3
"""
Debug script to check healthcare templates database tables and data
"""

import os
import sys
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

def check_table_exists(cursor, table_name):
    """Check if a table exists"""
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = %s
        );
    """, (table_name,))
    return cursor.fetchone()[0]

def check_table_data(cursor, table_name):
    """Check data in a table"""
    try:
        cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
        count = cursor.fetchone()[0]
        
        cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
        sample_data = cursor.fetchall()
        
        return count, sample_data
    except Exception as e:
        return None, f"Error: {e}"

def main():
    print("🔍 Healthcare Templates Database Debug Script")
    print("=" * 50)
    
    # Connect to database
    conn = get_db_connection()
    if not conn:
        sys.exit(1)
    
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # Tables to check
    tables_to_check = [
        'healthcare_sectors',
        'analysis_templates',
        'template_chapters',
        'chapter_questions',
        'gp_template_customizations',
        'template_performance',
        'classification_performance',
        'startup_classifications'
    ]
    
    print("\n📋 Checking table existence:")
    for table in tables_to_check:
        exists = check_table_exists(cursor, table)
        status = "✅ EXISTS" if exists else "❌ MISSING"
        print(f"  {table}: {status}")
    
    print("\n📊 Checking table data:")
    for table in tables_to_check:
        if check_table_exists(cursor, table):
            count, sample = check_table_data(cursor, table)
            if count is not None:
                print(f"\n  {table}:")
                print(f"    📈 Row count: {count}")
                if count > 0 and sample:
                    print(f"    📄 Sample data:")
                    for i, row in enumerate(sample):
                        print(f"      Row {i+1}: {dict(row)}")
                elif count == 0:
                    print(f"    ⚠️  Table is empty")
            else:
                print(f"    ❌ Error reading {table}: {sample}")
    
    print("\n🔍 Testing the specific healthcare sectors query:")
    try:
        cursor.execute("""
        SELECT id, name, display_name, description, keywords, subcategories, 
               confidence_threshold, regulatory_requirements, is_active
        FROM healthcare_sectors
        WHERE is_active = TRUE
        ORDER BY display_name
        """)
        results = cursor.fetchall()
        print(f"✅ Query successful! Found {len(results)} active healthcare sectors")
        for sector in results:
            print(f"  - {sector['display_name']} (ID: {sector['id']})")
    except Exception as e:
        print(f"❌ Healthcare sectors query failed: {e}")
    
    print("\n🔍 Testing performance metrics query:")
    try:
        cursor.execute("""
        SELECT t.name, COUNT(tp.id) as usage_count, 
               AVG(tp.average_confidence) as avg_confidence,
               AVG(tp.gp_rating) as avg_rating
        FROM analysis_templates t
        LEFT JOIN template_performance tp ON t.id = tp.template_id
        WHERE t.is_active = TRUE
        GROUP BY t.id, t.name
        ORDER BY usage_count DESC
        """)
        results = cursor.fetchall()
        print(f"✅ Performance metrics query successful! Found {len(results)} templates")
        for template in results[:3]:  # Show first 3
            print(f"  - {template['name']}: {template['usage_count']} uses")
    except Exception as e:
        print(f"❌ Performance metrics query failed: {e}")
    
    cursor.close()
    conn.close()
    
    print("\n✅ Debug script completed!")

if __name__ == "__main__":
    main()