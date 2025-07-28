#!/usr/bin/env python3
"""
Cleanup script for migration artifact projects
Removes projects that were created during database migrations but are not proper dojo experiments
"""

import json
import os
import sys
from datetime import datetime

def get_database_connection():
    """Get database connection using app's database session factory"""
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
        from app.db.database import SessionLocal
        from sqlalchemy import create_engine
        
        # Use the SessionLocal to get the engine
        session = SessionLocal()
        engine = session.get_bind()
        session.close()
        
        return engine.connect(), 'app_database'
    except Exception as e:
        print(f"Database connection error: {e}")
        return None, None

def identify_migration_projects(conn):
    """Identify projects that are migration artifacts"""
    from sqlalchemy import text
    
    # Find test projects without the dojo experiment flag
    query = text("""
        SELECT 
            id, company_id, project_name, created_at, project_metadata, tags
        FROM projects 
        WHERE is_test = TRUE
        AND (
            project_metadata IS NULL 
            OR project_metadata = '{}'
            OR project_metadata::json->>'created_from_experiment' IS NULL
            OR project_metadata::json->>'created_from_experiment' != 'true'
        )
        ORDER BY created_at DESC
    """)
    
    projects = conn.execute(query).fetchall()
    
    migration_projects = []
    
    for project in projects:
        project_id, company_id, project_name, created_at, metadata_raw, tags_raw = project
        
        # Parse metadata
        try:
            if isinstance(metadata_raw, dict):
                metadata = metadata_raw
            elif metadata_raw:
                metadata = json.loads(metadata_raw)
            else:
                metadata = {}
        except:
            metadata = {}
        
        # Check if this looks like a migration artifact
        is_migration = (
            metadata.get('migrated_from_pitch_deck') or
            metadata.get('data_source_type') or
            'migration' in str(metadata).lower()
        )
        
        if is_migration or not metadata.get('created_from_experiment'):
            migration_projects.append({
                'id': project_id,
                'company_id': company_id,
                'project_name': project_name,
                'created_at': created_at,
                'metadata': metadata
            })
    
    return migration_projects

def cleanup_migration_projects(conn, project_ids, dry_run=True):
    """Clean up migration projects"""
    from sqlalchemy import text
    
    if not project_ids:
        print("No projects to clean up.")
        return
    
    id_list = ', '.join(map(str, project_ids))
    
    if dry_run:
        print("DRY RUN - No changes will be made")
        print("=" * 50)
        
        # Show what would be deleted
        doc_query = text(f"""
            SELECT COUNT(*) FROM project_documents 
            WHERE project_id IN ({id_list})
        """)
        doc_count = conn.execute(doc_query).fetchone()[0]
        
        print(f"Would delete:")
        print(f"  - {len(project_ids)} projects")
        print(f"  - {doc_count} associated documents")
        print()
        print("SQL commands that would be executed:")
        print(f"DELETE FROM project_documents WHERE project_id IN ({id_list});")
        print(f"DELETE FROM projects WHERE id IN ({id_list});")
        
    else:
        print("EXECUTING CLEANUP")
        print("=" * 50)
        
        try:
            # Delete documents first (foreign key constraint)
            doc_delete = text(f"""
                DELETE FROM project_documents 
                WHERE project_id IN ({id_list})
            """)
            doc_result = conn.execute(doc_delete)
            print(f"✅ Deleted {doc_result.rowcount} project documents")
            
            # Delete projects
            project_delete = text(f"""
                DELETE FROM projects 
                WHERE id IN ({id_list})
            """)
            project_result = conn.execute(project_delete)
            print(f"✅ Deleted {project_result.rowcount} projects")
            
            # Commit the transaction
            conn.commit()
            print("✅ Cleanup completed successfully!")
            
        except Exception as e:
            print(f"❌ Cleanup failed: {e}")
            conn.rollback()
            raise

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Clean up migration artifact projects')
    parser.add_argument('--execute', action='store_true', 
                       help='Actually execute the cleanup (default is dry-run)')
    parser.add_argument('--confirm', action='store_true',
                       help='Skip confirmation prompt when executing')
    
    args = parser.parse_args()
    
    print("Migration Project Cleanup Tool")
    print("=" * 50)
    
    conn, db_type = get_database_connection()
    if not conn:
        print("❌ Could not connect to database.")
        return
    
    print(f"✅ Connected to database ({db_type})")
    print()
    
    try:
        # Identify migration projects
        migration_projects = identify_migration_projects(conn)
        
        if not migration_projects:
            print("✅ No migration artifact projects found!")
            return
        
        print(f"Found {len(migration_projects)} migration artifact projects:")
        print("-" * 60)
        
        project_ids = []
        for project in migration_projects:
            print(f"ID {project['id']}: {project['company_id']} - {project['project_name']}")
            print(f"  Created: {project['created_at']}")
            print(f"  Migration indicators: {list(project['metadata'].keys())}")
            project_ids.append(project['id'])
            print()
        
        # Execute cleanup
        if args.execute:
            if not args.confirm:
                response = input(f"\n⚠️  Are you sure you want to delete {len(project_ids)} projects? (yes/no): ")
                if response.lower() != 'yes':
                    print("Cancelled.")
                    return
            
            cleanup_migration_projects(conn, project_ids, dry_run=False)
        else:
            print("🔍 DRY RUN MODE (use --execute to actually delete)")
            cleanup_migration_projects(conn, project_ids, dry_run=True)
            print("\nTo execute the cleanup, run:")
            print("python cleanup_migration_projects.py --execute")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()