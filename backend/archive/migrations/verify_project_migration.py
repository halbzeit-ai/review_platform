#!/usr/bin/env python3
"""
Project Migration Verification Script
Checks that the migration from deck-centric to project-centric structure was successful
"""

import os
import sys
import psycopg2
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings

def connect_to_database():
    """Connect to the PostgreSQL database"""
    try:
        # Parse DATABASE_URL for connection details
        if hasattr(settings, 'DATABASE_URL') and settings.DATABASE_URL:
            # For production with full DATABASE_URL
            conn = psycopg2.connect(settings.DATABASE_URL)
        else:
            # Fallback for local development
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

def run_verification():
    """Run verification queries and display results"""
    print("Project Migration Verification")
    print("=" * 50)
    
    conn = connect_to_database()
    if not conn:
        return
    
    try:
        cursor = conn.cursor()
        
        # 1. Migration Summary
        print("\n1. MIGRATION SUMMARY:")
        print("-" * 30)
        
        cursor.execute("""
        SELECT 
            'Original pitch_decks' as table_name,
            COUNT(*) as count
        FROM pitch_decks
        WHERE company_id IS NOT NULL
        
        UNION ALL
        
        SELECT 
            'Created projects' as table_name,
            COUNT(*) as count
        FROM projects
        
        UNION ALL
        
        SELECT 
            'Migrated documents' as table_name,
            COUNT(*) as count
        FROM project_documents
        WHERE document_type = 'pitch_deck'
        
        UNION ALL
        
        SELECT 
            'Migrated reviews' as table_name,
            COUNT(*) as count
        FROM project_interactions
        WHERE interaction_type = 'review'
        
        UNION ALL
        
        SELECT 
            'Migrated questions' as table_name,
            COUNT(*) as count
        FROM project_interactions
        WHERE interaction_type = 'question'
        ORDER BY table_name
        """)
        
        results = cursor.fetchall()
        for table_name, count in results:
            print(f"  {table_name:<25}: {count:>5}")
        
        # 2. Project Breakdown
        print("\n2. PROJECT BREAKDOWN:")
        print("-" * 30)
        
        cursor.execute("""
        SELECT 
            p.company_id,
            p.project_name,
            p.funding_round,
            COUNT(DISTINCT pd.id) as document_count,
            COUNT(DISTINCT pi.id) as interaction_count,
            p.created_at::date
        FROM projects p
        LEFT JOIN project_documents pd ON p.id = pd.project_id
        LEFT JOIN project_interactions pi ON p.id = pi.project_id
        GROUP BY p.id, p.company_id, p.project_name, p.funding_round, p.created_at
        ORDER BY p.company_id
        """)
        
        projects = cursor.fetchall()
        if projects:
            print(f"{'Company ID':<20} {'Project Name':<30} {'Round':<10} {'Docs':<6} {'Interactions':<12} {'Created'}")
            print("-" * 90)
            for company_id, project_name, funding_round, doc_count, interaction_count, created_date in projects:
                print(f"{company_id:<20} {project_name[:29]:<30} {funding_round:<10} {doc_count:<6} {interaction_count:<12} {created_date}")
        else:
            print("  No projects found")
        
        # 3. Sample Project Data
        print("\n3. SAMPLE PROJECT DATA:")
        print("-" * 30)
        
        cursor.execute("""
        SELECT 
            p.company_id,
            p.project_name,
            p.funding_sought,
            p.company_offering,
            p.project_metadata
        FROM projects p
        LIMIT 3
        """)
        
        samples = cursor.fetchall()
        for i, (company_id, project_name, funding_sought, company_offering, metadata) in enumerate(samples, 1):
            print(f"\nProject {i}:")
            print(f"  Company ID: {company_id}")
            print(f"  Project Name: {project_name}")
            print(f"  Funding Sought: {funding_sought or 'Not extracted'}")
            print(f"  Company Offering: {company_offering[:100] + '...' if company_offering and len(company_offering) > 100 else company_offering or 'Not extracted'}")
            if metadata:
                try:
                    meta_dict = json.loads(metadata) if isinstance(metadata, str) else metadata
                    print(f"  Migrated: {meta_dict.get('migrated_from_pitch_deck', False)}")
                    print(f"  Data Source: {meta_dict.get('original_data_source', 'Unknown')}")
                except:
                    print(f"  Metadata: {str(metadata)[:50]}...")
        
        # 4. Document Types
        print("\n4. DOCUMENT TYPES:")
        print("-" * 30)
        
        cursor.execute("""
        SELECT 
            document_type,
            COUNT(*) as count,
            COUNT(CASE WHEN extracted_data IS NOT NULL THEN 1 END) as with_extracted_data,
            COUNT(CASE WHEN analysis_results_path IS NOT NULL THEN 1 END) as with_analysis_results
        FROM project_documents
        GROUP BY document_type
        ORDER BY count DESC
        """)
        
        doc_types = cursor.fetchall()
        if doc_types:
            print(f"{'Type':<15} {'Count':<8} {'With Data':<12} {'With Analysis'}")
            print("-" * 50)
            for doc_type, count, with_data, with_analysis in doc_types:
                print(f"{doc_type:<15} {count:<8} {with_data:<12} {with_analysis}")
        
        # 5. Interaction Types
        print("\n5. INTERACTION TYPES:")
        print("-" * 30)
        
        cursor.execute("""
        SELECT 
            interaction_type,
            COUNT(*) as count,
            COUNT(CASE WHEN document_id IS NOT NULL THEN 1 END) as linked_to_document
        FROM project_interactions
        GROUP BY interaction_type
        ORDER BY count DESC
        """)
        
        interaction_types = cursor.fetchall()
        if interaction_types:
            print(f"{'Type':<15} {'Count':<8} {'Linked to Doc'}")
            print("-" * 35)
            for int_type, count, linked in interaction_types:
                print(f"{int_type:<15} {count:<8} {linked}")
        
        print("\n" + "=" * 50)
        print("✅ Migration verification completed!")
        print("\nNext steps:")
        print("  1. Define your funding process stages")
        print("  2. Test the new project management APIs")
        print("  3. Update frontend to use project-centric views")
        
    except Exception as e:
        print(f"Error during verification: {e}")
    
    finally:
        conn.close()

if __name__ == "__main__":
    run_verification()