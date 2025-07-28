#!/usr/bin/env python3
"""
Investigate Document Duplication
Check why we have 5,643 documents from 183 pitch decks
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

def investigate():
    """Investigate document duplication"""
    print("Document Duplication Investigation")
    print("=" * 40)
    
    conn = connect_to_database()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # 1. Check for duplicate documents by file_path
        print("\n1. DUPLICATE DOCUMENTS BY FILE PATH:")
        print("-" * 40)
        
        cursor.execute("""
        SELECT 
            file_path,
            COUNT(*) as duplicate_count,
            array_agg(DISTINCT project_id) as project_ids
        FROM project_documents
        WHERE document_type = 'pitch_deck'
        GROUP BY file_path
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
        LIMIT 10
        """)
        
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"{'File Path':<50} {'Duplicates':<12} {'Project IDs'}")
            print("-" * 80)
            for file_path, dup_count, project_ids in duplicates:
                print(f"{file_path[:49]:<50} {dup_count:<12} {str(project_ids)[:20]}")
        else:
            print("No duplicate documents found by file path")
        
        # 2. Check original pitch_decks vs project_documents
        print("\n2. PITCH DECKS VS PROJECT DOCUMENTS:")
        print("-" * 40)
        
        cursor.execute("""
        SELECT 
            'Original pitch_decks' as source,
            COUNT(*) as count,
            COUNT(DISTINCT company_id) as unique_companies,
            COUNT(DISTINCT file_path) as unique_files
        FROM pitch_decks
        WHERE company_id IS NOT NULL
        
        UNION ALL
        
        SELECT 
            'Project documents' as source,
            COUNT(*) as count,
            COUNT(DISTINCT p.company_id) as unique_companies,
            COUNT(DISTINCT pd.file_path) as unique_files
        FROM project_documents pd
        JOIN projects p ON pd.project_id = p.id
        WHERE pd.document_type = 'pitch_deck'
        """)
        
        comparison = cursor.fetchall()
        print(f"{'Source':<20} {'Count':<8} {'Companies':<12} {'Unique Files'}")
        print("-" * 55)
        for source, count, companies, files in comparison:
            print(f"{source:<20} {count:<8} {companies:<12} {files}")
        
        # 3. Check if there are multiple projects with same company_id
        print("\n3. PROJECTS BY COMPANY:")
        print("-" * 40)
        
        cursor.execute("""
        SELECT 
            company_id,
            COUNT(*) as project_count,
            array_agg(id) as project_ids
        FROM projects
        GROUP BY company_id
        ORDER BY COUNT(*) DESC
        LIMIT 10
        """)
        
        companies = cursor.fetchall()
        print(f"{'Company ID':<20} {'Project Count':<15} {'Project IDs'}")
        print("-" * 60)
        for company_id, project_count, project_ids in companies:
            ids_str = str(project_ids)[:30] + "..." if len(str(project_ids)) > 30 else str(project_ids)
            print(f"{company_id:<20} {project_count:<15} {ids_str}")
        
        # 4. Sample of document records
        print("\n4. SAMPLE DOCUMENT RECORDS:")
        print("-" * 40)
        
        cursor.execute("""
        SELECT 
            pd.id,
            pd.project_id,
            p.company_id,
            pd.file_name,
            pd.file_path
        FROM project_documents pd
        JOIN projects p ON pd.project_id = p.id
        WHERE pd.document_type = 'pitch_deck'
        ORDER BY pd.id
        LIMIT 5
        """)
        
        samples = cursor.fetchall()
        print(f"{'Doc ID':<8} {'Project ID':<12} {'Company':<15} {'File Name'}")
        print("-" * 70)
        for doc_id, project_id, company_id, file_name, file_path in samples:
            print(f"{doc_id:<8} {project_id:<12} {company_id:<15} {file_name[:30]}")
        
        print("\n" + "=" * 40)
        print("Investigation completed!")
        
    except Exception as e:
        print(f"Error during investigation: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    investigate()