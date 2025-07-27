#!/usr/bin/env python3
"""
Debug script to check project_metadata types and fix JSON serialization issue
Run this on the production server to diagnose the problem
"""

import os
import sys
import psycopg2
import json

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings

def connect_to_database():
    """Connect to the PostgreSQL database"""
    try:
        if hasattr(settings, 'DATABASE_URL') and settings.DATABASE_URL:
            conn = psycopg2.connect(settings.DATABASE_URL)
        else:
            conn = psycopg2.connect(
                host=getattr(settings, 'DB_HOST', 'localhost'),
                database=getattr(settings, 'DB_NAME', 'review_platform'), 
                user=getattr(settings, 'DB_USER', 'postgres'),
                password=getattr(settings, 'DB_PASSWORD', ''),
                port=getattr(settings, 'DB_PORT', 5432)
            )
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def debug_project_metadata():
    """Debug project_metadata field issues"""
    print("Project Metadata Debug Analysis")
    print("=" * 50)
    
    conn = connect_to_database()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # 1. Check project_metadata column type and sample values
        print("\n1. PROJECT_METADATA COLUMN ANALYSIS:")
        print("-" * 40)
        
        cursor.execute("""
        SELECT 
            id,
            company_id,
            project_name,
            project_metadata,
            pg_typeof(project_metadata) as metadata_type
        FROM projects 
        ORDER BY id 
        LIMIT 10
        """)
        
        results = cursor.fetchall()
        for row in results:
            project_id, company_id, project_name, metadata, metadata_type = row
            print(f"Project {project_id} ({company_id}):")
            print(f"  Name: {project_name}")
            print(f"  Metadata Type: {metadata_type}")
            print(f"  Metadata Value: {metadata}")
            print(f"  Python Type: {type(metadata)}")
            
            # Try to parse if it's a string
            if isinstance(metadata, str):
                try:
                    parsed = json.loads(metadata)
                    print(f"  JSON Parse: SUCCESS -> {parsed}")
                except json.JSONDecodeError as e:
                    print(f"  JSON Parse: FAILED -> {e}")
            elif metadata is None:
                print(f"  JSON Parse: NULL")
            else:
                print(f"  JSON Parse: Already a dict/object")
            print()
        
        # 2. Check for problematic records
        print("\n2. PROBLEMATIC RECORDS CHECK:")
        print("-" * 35)
        
        # Check for invalid JSON strings
        cursor.execute("""
        SELECT id, company_id, project_metadata
        FROM projects 
        WHERE project_metadata IS NOT NULL 
        AND project_metadata != ''
        AND project_metadata::text !~ '^[\\s]*[\\{\\[]'
        """)
        
        invalid_json = cursor.fetchall()
        if invalid_json:
            print(f"Found {len(invalid_json)} records with invalid JSON:")
            for row in invalid_json:
                print(f"  Project {row[0]} ({row[1]}): {row[2]}")
        else:
            print("✅ No invalid JSON found")
        
        # 3. Test the actual query from the API
        print("\n3. TESTING API QUERY:")
        print("-" * 25)
        
        cursor.execute("""
        SELECT p.id, p.company_id, p.project_name, p.funding_round, p.current_stage_id,
               p.funding_sought, p.healthcare_sector_id, p.company_offering, 
               p.project_metadata, p.is_active, p.created_at, p.updated_at,
               COUNT(DISTINCT pd.id) as document_count,
               COUNT(DISTINCT pi.id) as interaction_count
        FROM projects p
        LEFT JOIN project_documents pd ON p.id = pd.project_id AND pd.is_active = TRUE
        LEFT JOIN project_interactions pi ON p.id = pi.project_id AND pi.status = 'active'
        WHERE p.is_active = TRUE
        AND (p.is_test = FALSE OR p.is_test IS NULL)
        GROUP BY p.id, p.company_id, p.project_name, p.funding_round, p.current_stage_id,
                 p.funding_sought, p.healthcare_sector_id, p.company_offering, 
                 p.project_metadata, p.is_active, p.created_at, p.updated_at
        ORDER BY p.updated_at DESC
        LIMIT 5
        """)
        
        api_results = cursor.fetchall()
        print(f"API Query returned {len(api_results)} results")
        
        for i, row in enumerate(api_results):
            project_id = row[0]
            company_id = row[1] 
            project_metadata = row[8]
            
            print(f"\nResult {i+1} - Project {project_id} ({company_id}):")
            print(f"  Metadata raw: {repr(project_metadata)}")
            print(f"  Metadata type: {type(project_metadata)}")
            
            # Simulate the API parsing logic
            try:
                if isinstance(project_metadata, str):
                    parsed = json.loads(project_metadata)
                    print(f"  ✅ JSON parsing: SUCCESS -> {parsed}")
                elif project_metadata is None:
                    parsed = {}
                    print(f"  ✅ NULL handling: SUCCESS -> {parsed}")
                else:
                    # It's already a dict/object
                    parsed = project_metadata
                    print(f"  ✅ Direct use: SUCCESS -> {parsed}")
            except Exception as e:
                print(f"  ❌ ERROR: {e}")
        
        # 4. Summary and recommendations
        print("\n4. SUMMARY & RECOMMENDATIONS:")
        print("-" * 35)
        
        cursor.execute("SELECT COUNT(*) FROM projects WHERE is_active = TRUE")
        total_projects = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM projects WHERE is_active = TRUE AND (is_test = FALSE OR is_test IS NULL)")
        production_projects = cursor.fetchone()[0]
        
        print(f"Total active projects: {total_projects}")
        print(f"Production projects: {production_projects}")
        
        if invalid_json:
            print(f"⚠️  {len(invalid_json)} projects have invalid JSON metadata")
            print("   Recommendation: Fix or clear these records")
        else:
            print("✅ All project metadata appears to be valid JSON or NULL")
            print("   The issue is likely in the Python JSON parsing logic")
        
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

if __name__ == "__main__":
    debug_project_metadata()