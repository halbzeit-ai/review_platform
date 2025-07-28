#!/usr/bin/env python3
"""
Investigate Document Count Explosion
Find out why we have 5,643 documents when expecting ~500
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

def investigate_document_explosion():
    """Deep investigation into document count explosion"""
    print("Document Count Explosion Investigation")
    print("=" * 50)
    
    conn = connect_to_database()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # 1. Basic counts comparison
        print("\n1. BASIC COUNTS COMPARISON:")
        print("-" * 30)
        
        cursor.execute("""
        SELECT 
            'Original pitch_decks table' as source,
            COUNT(*) as total_records,
            COUNT(DISTINCT file_path) as unique_file_paths,
            COUNT(DISTINCT company_id) as unique_companies
        FROM pitch_decks
        
        UNION ALL
        
        SELECT 
            'Migrated project_documents' as source,
            COUNT(*) as total_records,
            COUNT(DISTINCT file_path) as unique_file_paths,
            COUNT(DISTINCT project_id) as unique_projects
        FROM project_documents
        WHERE document_type = 'pitch_deck'
        """)
        
        results = cursor.fetchall()
        print(f"{'Source':<30} {'Total':<8} {'Unique Files':<13} {'Unique Comp/Proj'}")
        print("-" * 65)
        for source, total, unique_files, unique_comp in results:
            print(f"{source:<30} {total:<8} {unique_files:<13} {unique_comp}")
        
        # 2. Check for exact duplicates in project_documents
        print("\n2. EXACT DUPLICATES IN PROJECT_DOCUMENTS:")
        print("-" * 30)
        
        cursor.execute("""
        SELECT 
            file_path,
            COUNT(*) as duplicate_count,
            array_agg(DISTINCT project_id) as project_ids,
            array_agg(DISTINCT id) as document_ids
        FROM project_documents
        WHERE document_type = 'pitch_deck'
        GROUP BY file_path
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC
        LIMIT 10
        """)
        
        duplicates = cursor.fetchall()
        if duplicates:
            print(f"Found {len(duplicates)} file paths with duplicates:")
            print(f"{'File Path':<60} {'Count':<8} {'Project IDs'}")
            print("-" * 85)
            for file_path, dup_count, project_ids, doc_ids in duplicates:
                project_str = str(project_ids)[:20] + "..." if len(str(project_ids)) > 20 else str(project_ids)
                print(f"{file_path[:59]:<60} {dup_count:<8} {project_str}")
        else:
            print("No exact file path duplicates found")
        
        # 3. Check if multiple projects have same documents
        print("\n3. CROSS-PROJECT DOCUMENT SHARING:")
        print("-" * 30)
        
        cursor.execute("""
        WITH file_project_mapping AS (
            SELECT 
                file_path,
                COUNT(DISTINCT project_id) as project_count,
                array_agg(DISTINCT project_id ORDER BY project_id) as project_ids
            FROM project_documents
            WHERE document_type = 'pitch_deck'
            GROUP BY file_path
            HAVING COUNT(DISTINCT project_id) > 1
        )
        SELECT 
            file_path,
            project_count,
            project_ids
        FROM file_project_mapping
        ORDER BY project_count DESC
        LIMIT 10
        """)
        
        shared_files = cursor.fetchall()
        if shared_files:
            print(f"Found {len(shared_files)} files shared across multiple projects:")
            print(f"{'File Path':<60} {'Projects':<10} {'Project IDs'}")
            print("-" * 85)
            for file_path, proj_count, project_ids in shared_files:
                ids_str = str(project_ids)[:20] + "..." if len(str(project_ids)) > 20 else str(project_ids)
                print(f"{file_path[:59]:<60} {proj_count:<10} {ids_str}")
        else:
            print("No files shared across multiple projects")
        
        # 4. Check the migration logic issue
        print("\n4. MIGRATION LOGIC ANALYSIS:")
        print("-" * 30)
        
        cursor.execute("""
        SELECT 
            pd.company_id,
            COUNT(DISTINCT pd.file_path) as unique_files_in_pitch_decks,
            COUNT(DISTINCT proj.id) as projects_created,
            COUNT(DISTINCT doc.id) as documents_created
        FROM pitch_decks pd
        LEFT JOIN projects proj ON proj.company_id = pd.company_id
        LEFT JOIN project_documents doc ON doc.project_id = proj.id AND doc.document_type = 'pitch_deck'
        WHERE pd.company_id IS NOT NULL
        GROUP BY pd.company_id
        ORDER BY documents_created DESC
        LIMIT 10
        """)
        
        migration_analysis = cursor.fetchall()
        print(f"{'Company ID':<20} {'Orig Files':<12} {'Projects':<10} {'Migrated Docs'}")
        print("-" * 60)
        for company_id, orig_files, projects, migrated_docs in migration_analysis:
            print(f"{company_id:<20} {orig_files:<12} {projects:<10} {migrated_docs}")
        
        # 5. Sample of potential problematic records
        print("\n5. SAMPLE ANALYSIS - DOJO COMPANY:")
        print("-" * 30)
        
        cursor.execute("""
        SELECT 
            COUNT(*) as total_pitch_decks,
            COUNT(DISTINCT file_path) as unique_files,
            COUNT(DISTINCT file_name) as unique_filenames,
            MIN(created_at) as earliest_date,
            MAX(created_at) as latest_date
        FROM pitch_decks
        WHERE company_id = 'dojo'
        """)
        
        dojo_original = cursor.fetchone()
        print(f"Original dojo pitch_decks:")
        print(f"  Total records: {dojo_original[0]}")
        print(f"  Unique file paths: {dojo_original[1]}")
        print(f"  Unique file names: {dojo_original[2]}")
        print(f"  Date range: {dojo_original[3]} to {dojo_original[4]}")
        
        cursor.execute("""
        SELECT 
            COUNT(*) as total_documents,
            COUNT(DISTINCT file_path) as unique_files,
            COUNT(DISTINCT file_name) as unique_filenames,
            COUNT(DISTINCT project_id) as unique_projects
        FROM project_documents pd
        JOIN projects p ON pd.project_id = p.id
        WHERE p.company_id = 'dojo' AND pd.document_type = 'pitch_deck'
        """)
        
        dojo_migrated = cursor.fetchone()
        print(f"\nMigrated dojo documents:")
        print(f"  Total records: {dojo_migrated[0]}")
        print(f"  Unique file paths: {dojo_migrated[1]}")
        print(f"  Unique file names: {dojo_migrated[2]}")
        print(f"  Unique projects: {dojo_migrated[3]}")
        
        # 6. Check for the root cause - Cartesian product in migration
        print("\n6. ROOT CAUSE ANALYSIS:")
        print("-" * 30)
        
        # This query simulates what the migration JOIN might have done wrong
        cursor.execute("""
        SELECT 
            pd.company_id,
            COUNT(*) as pitch_deck_records,
            COUNT(DISTINCT p.id) as project_records,
            COUNT(*) * COUNT(DISTINCT p.id) as potential_cartesian_product
        FROM pitch_decks pd
        JOIN projects p ON p.company_id = pd.company_id
        WHERE pd.company_id = 'dojo'
        GROUP BY pd.company_id
        """)
        
        cartesian_check = cursor.fetchone()
        if cartesian_check:
            print(f"Dojo migration analysis:")
            print(f"  Original pitch_deck records: {cartesian_check[1]}")
            print(f"  Created project records: {cartesian_check[2]}")
            print(f"  Potential Cartesian product: {cartesian_check[3]}")
            print(f"  Actual migrated documents: {dojo_migrated[0]}")
            
            if cartesian_check[3] == dojo_migrated[0]:
                print("  🚨 FOUND THE ISSUE: Cartesian product in migration JOIN!")
                print("     Each pitch_deck was joined with EVERY project for the same company_id")
            else:
                print("  ✅ No Cartesian product detected")
        
        print("\n" + "=" * 50)
        if cartesian_check and cartesian_check[3] == dojo_migrated[0]:
            print("🎯 CONCLUSION: Migration created Cartesian product")
            print("   Solution: Clean up duplicate documents that reference same file_path")
        else:
            print("🤔 CONCLUSION: Need to investigate other causes")
        
    except Exception as e:
        print(f"Error during investigation: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    investigate_document_explosion()