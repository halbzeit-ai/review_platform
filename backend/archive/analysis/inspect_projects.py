#!/usr/bin/env python3
"""
Database Project Inspector
Identifies and categorizes projects in the database to help clean up migration artifacts
"""

import json
import sys
import os
from sqlalchemy import create_engine, text
from datetime import datetime

# Add the app directory to the path so we can import database config
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings

def connect_to_database():
    """Connect to the database using the same config as the app"""
    try:
        engine = create_engine(settings.database_url)
        return engine.connect()
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def inspect_projects(conn):
    """Inspect all projects and categorize them"""
    print("=" * 80)
    print("PROJECT DATABASE INSPECTION")
    print("=" * 80)
    
    # Get overall statistics
    stats_query = text("""
        SELECT 
            COUNT(*) as total_projects,
            COUNT(CASE WHEN is_test = TRUE THEN 1 END) as test_projects,
            COUNT(CASE WHEN is_test = FALSE THEN 1 END) as production_projects,
            COUNT(DISTINCT company_id) as unique_companies,
            COUNT(CASE WHEN is_test = TRUE THEN company_id END) as test_companies
        FROM projects
    """)
    
    stats = conn.execute(stats_query).fetchone()
    
    print(f"OVERALL STATISTICS:")
    print(f"  Total Projects: {stats[0]}")
    print(f"  Test Projects: {stats[1]}")
    print(f"  Production Projects: {stats[2]}")
    print(f"  Unique Companies: {stats[3]}")
    print(f"  Test Companies: {stats[4]}")
    print()
    
    # Analyze test projects by creation method
    print("TEST PROJECT ANALYSIS:")
    print("-" * 40)
    
    test_projects_query = text("""
        SELECT 
            id, company_id, project_name, funding_round, funding_sought,
            company_offering, created_at, project_metadata, tags
        FROM projects 
        WHERE is_test = TRUE
        ORDER BY created_at DESC
    """)
    
    test_projects = conn.execute(test_projects_query).fetchall()
    
    dojo_created = []
    migration_created = []
    unknown_created = []
    
    for project in test_projects:
        try:
            metadata = json.loads(project[7]) if project[7] else {}
            tags = json.loads(project[8]) if project[8] else []
            
            # Categorize based on metadata and tags
            if metadata.get('created_from_experiment'):
                dojo_created.append(project)
            elif any('migration' in str(tag).lower() for tag in tags) or 'migration' in str(metadata).lower():
                migration_created.append(project)
            else:
                unknown_created.append(project)
                
        except json.JSONDecodeError:
            unknown_created.append(project)
    
    print(f"Dojo-created projects: {len(dojo_created)}")
    print(f"Migration-created projects: {len(migration_created)}")
    print(f"Unknown/Other projects: {len(unknown_created)}")
    print()
    
    # Show migration projects in detail
    if migration_created:
        print("MIGRATION-CREATED PROJECTS:")
        print("-" * 40)
        for project in migration_created:
            print(f"ID: {project[0]}")
            print(f"  Company: {project[1]}")
            print(f"  Project: {project[2]}")
            print(f"  Created: {project[6]}")
            print(f"  Tags: {project[8]}")
            print(f"  Metadata: {project[7][:200]}...")
            print()
    
    # Show unknown projects in detail
    if unknown_created:
        print("UNKNOWN/OTHER PROJECTS:")
        print("-" * 40)
        for project in unknown_created:
            metadata = json.loads(project[7]) if project[7] else {}
            print(f"ID: {project[0]}")
            print(f"  Company: {project[1]}")
            print(f"  Project: {project[2]}")
            print(f"  Created: {project[6]}")
            print(f"  Tags: {project[8]}")
            print(f"  Has experiment metadata: {'created_from_experiment' in metadata}")
            print(f"  Metadata keys: {list(metadata.keys()) if metadata else 'None'}")
            print()
    
    # Check for projects with associated documents
    print("DOCUMENT ASSOCIATIONS:")
    print("-" * 40)
    
    doc_query = text("""
        SELECT p.id, p.company_id, p.project_name, COUNT(pd.id) as doc_count,
               array_agg(pd.document_type) as doc_types
        FROM projects p
        LEFT JOIN project_documents pd ON p.id = pd.project_id
        WHERE p.is_test = TRUE
        GROUP BY p.id, p.company_id, p.project_name
        HAVING COUNT(pd.id) > 0
        ORDER BY p.created_at DESC
    """)
    
    projects_with_docs = conn.execute(doc_query).fetchall()
    
    for project in projects_with_docs:
        print(f"Project {project[0]} ({project[1]}): {project[3]} documents")
        print(f"  Document types: {project[4]}")
        print()

def create_cleanup_script(conn):
    """Generate a cleanup script for non-dojo projects"""
    print("GENERATING CLEANUP RECOMMENDATIONS:")
    print("-" * 40)
    
    # Find projects that are not dojo-created
    non_dojo_query = text("""
        SELECT id, company_id, project_name, project_metadata, tags
        FROM projects 
        WHERE is_test = TRUE 
        AND (
            project_metadata IS NULL 
            OR project_metadata = '{}' 
            OR project_metadata::json->>'created_from_experiment' IS NULL
            OR project_metadata::json->>'created_from_experiment' != 'true'
        )
    """)
    
    non_dojo_projects = conn.execute(non_dojo_query).fetchall()
    
    if non_dojo_projects:
        print(f"Found {len(non_dojo_projects)} non-dojo test projects:")
        print()
        
        project_ids = [str(p[0]) for p in non_dojo_projects]
        
        print("SQL to clean up these projects:")
        print("-- Delete project documents first")
        print(f"DELETE FROM project_documents WHERE project_id IN ({', '.join(project_ids)});")
        print()
        print("-- Delete the projects")
        print(f"DELETE FROM projects WHERE id IN ({', '.join(project_ids)});")
        print()
        
        print("Individual project details:")
        for project in non_dojo_projects:
            print(f"  ID {project[0]}: {project[1]} - {project[2]}")
            metadata = json.loads(project[3]) if project[3] else {}
            print(f"    Metadata: {metadata}")
            print(f"    Tags: {project[4]}")
            print()
    else:
        print("No non-dojo test projects found - all test projects appear to be properly created from experiments.")

def main():
    """Main inspection function"""
    print(f"Starting database inspection at {datetime.now()}")
    print()
    
    conn = connect_to_database()
    if not conn:
        print("Failed to connect to database. Exiting.")
        return
    
    try:
        inspect_projects(conn)
        create_cleanup_script(conn)
        
    except Exception as e:
        print(f"Error during inspection: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()