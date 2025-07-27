#!/usr/bin/env python3
"""
Verify Document Cleanup Results
Check that deduplication worked correctly
"""

import os
import sys
import psycopg2

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

def verify_cleanup():
    """Verify the cleanup was successful"""
    print("Document Cleanup Verification")
    print("=" * 40)
    
    conn = connect_to_database()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # 1. Final document counts
        print("\n1. FINAL DOCUMENT COUNTS:")
        print("-" * 25)
        
        cursor.execute("""
        SELECT 
            'Total project documents' as metric,
            COUNT(*) as count
        FROM project_documents
        WHERE document_type = 'pitch_deck'
        
        UNION ALL
        
        SELECT 
            'Unique file paths' as metric,
            COUNT(DISTINCT file_path) as count
        FROM project_documents  
        WHERE document_type = 'pitch_deck'
        
        UNION ALL
        
        SELECT 
            'Original pitch_decks' as metric,
            COUNT(*) as count
        FROM pitch_decks
        WHERE company_id IS NOT NULL
        """)
        
        results = cursor.fetchall()
        for metric, count in results:
            print(f"  {metric:<25}: {count:>5}")
        
        # 2. Check for remaining duplicates
        print("\n2. DUPLICATE CHECK:")
        print("-" * 20)
        
        cursor.execute("""
        SELECT 
            file_path,
            COUNT(*) as duplicate_count
        FROM project_documents
        WHERE document_type = 'pitch_deck'
        GROUP BY file_path
        HAVING COUNT(*) > 1
        LIMIT 5
        """)
        
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"⚠️  Found {len(duplicates)} remaining duplicates:")
            for file_path, count in duplicates:
                print(f"    {file_path}: {count} copies")
        else:
            print("✅ No duplicates found - cleanup successful!")
        
        # 3. Test/Production data breakdown
        print("\n3. TEST/PRODUCTION DATA:")
        print("-" * 25)
        
        cursor.execute("""
        SELECT 
            CASE 
                WHEN p.is_test THEN 'Test/Dojo data'
                ELSE 'Production data'
            END as data_type,
            COUNT(DISTINCT p.id) as projects,
            COUNT(DISTINCT pd.id) as documents
        FROM projects p
        LEFT JOIN project_documents pd ON p.id = pd.project_id 
            AND pd.document_type = 'pitch_deck'
        GROUP BY p.is_test
        ORDER BY p.is_test
        """)
        
        data_breakdown = cursor.fetchall()
        print(f"{'Data Type':<20} {'Projects':<10} {'Documents'}")
        print("-" * 40)
        for data_type, projects, documents in data_breakdown:
            print(f"{data_type:<20} {projects:<10} {documents or 0}")
        
        # 4. Company summary
        print("\n4. COMPANY SUMMARY:")
        print("-" * 20)
        
        cursor.execute("""
        SELECT 
            p.company_id,
            COUNT(DISTINCT p.id) as projects,
            COUNT(DISTINCT pd.id) as documents,
            CASE WHEN p.is_test THEN 'Test' ELSE 'Prod' END as type
        FROM projects p
        LEFT JOIN project_documents pd ON p.id = pd.project_id 
            AND pd.document_type = 'pitch_deck'
        GROUP BY p.company_id, p.is_test
        ORDER BY COUNT(DISTINCT pd.id) DESC
        """)
        
        companies = cursor.fetchall()
        print(f"{'Company':<15} {'Projects':<10} {'Documents':<10} {'Type'}")
        print("-" * 50)
        for company_id, projects, documents, data_type in companies:
            print(f"{company_id:<15} {projects:<10} {documents or 0:<10} {data_type}")
        
        print("\n" + "=" * 40)
        print("✅ Cleanup verification completed!")
        
    except Exception as e:
        print(f"Error during verification: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    verify_cleanup()