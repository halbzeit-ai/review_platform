#!/usr/bin/env python3
"""
Clean up all dojo-related data before fresh import
Run on production server
"""

import os
import sys
import shutil

sys.path.append('/opt/review-platform/backend')

def main():
    print("=== DOJO DATA CLEANUP ===")
    
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db_session = next(get_db())
        print("✅ Connected to backend database")
        
        # 1. Find all dojo-related projects and documents
        print("\n1. Finding dojo-related data...")
        
        dojo_projects_query = text("""
            SELECT p.id, p.company_id, p.project_name, COUNT(pd.id) as doc_count
            FROM projects p
            LEFT JOIN project_documents pd ON p.id = pd.project_id AND pd.is_active = TRUE
            WHERE LOWER(p.company_id) LIKE '%dojo%' 
               OR LOWER(p.project_name) LIKE '%dojo%'
               OR p.is_test = TRUE
            GROUP BY p.id, p.company_id, p.project_name
            ORDER BY p.id
        """)
        
        dojo_projects = db_session.execute(dojo_projects_query).fetchall()
        
        if dojo_projects:
            print(f"Found {len(dojo_projects)} dojo projects:")
            for project in dojo_projects:
                print(f"  Project {project[0]}: {project[2]} (company: {project[1]}, docs: {project[3]})")
        else:
            print("No dojo projects found")
        
        # 2. Find all documents in dojo projects
        dojo_docs_query = text("""
            SELECT pd.id, pd.file_name, pd.project_id, p.company_id
            FROM project_documents pd
            JOIN projects p ON pd.project_id = p.id
            WHERE LOWER(p.company_id) LIKE '%dojo%' 
               OR LOWER(p.project_name) LIKE '%dojo%'
               OR p.is_test = TRUE
            ORDER BY pd.id
        """)
        
        dojo_docs = db_session.execute(dojo_docs_query).fetchall()
        
        if dojo_docs:
            print(f"\nFound {len(dojo_docs)} dojo documents:")
            for doc in dojo_docs:
                print(f"  Doc {doc[0]}: {doc[1]} (project {doc[2]}, company {doc[3]})")
        
        # 3. Find visual analysis cache entries for these documents
        if dojo_docs:
            doc_ids = [doc[0] for doc in dojo_docs]
            doc_ids_str = ','.join(map(str, doc_ids))
            
            cache_query = text(f"""
                SELECT pitch_deck_id, vision_model_used, created_at
                FROM visual_analysis_cache 
                WHERE pitch_deck_id IN ({doc_ids_str})
                ORDER BY pitch_deck_id
            """)
            
            cache_entries = db_session.execute(cache_query).fetchall()
            
            if cache_entries:
                print(f"\nFound {len(cache_entries)} visual analysis cache entries:")
                for entry in cache_entries:
                    print(f"  Deck {entry[0]}: {entry[1]} ({entry[2]})")
            else:
                print("\nNo visual analysis cache entries found for dojo docs")
        
        # 4. Check filesystem data
        print("\n2. Checking filesystem data...")
        
        dojo_projects_path = os.path.join('/mnt/CPU-GPU/projects/dojo')
        if os.path.exists(dojo_projects_path):
            print(f"Dojo projects directory exists: {dojo_projects_path}")
            if os.path.exists(os.path.join(dojo_projects_path, 'analysis')):
                analysis_dirs = os.listdir(os.path.join(dojo_projects_path, 'analysis'))
                print(f"  Found {len(analysis_dirs)} analysis directories")
            else:
                print("  No analysis directory found")
        else:
            print("No dojo projects directory found")
        
        # 5. Cleanup confirmation
        print(f"\n3. Cleanup Summary:")
        print(f"  Will delete {len(dojo_projects)} projects")
        print(f"  Will delete {len(dojo_docs) if dojo_docs else 0} documents")
        print(f"  Will delete {len(cache_entries) if dojo_docs and cache_entries else 0} cache entries")
        print(f"  Will clean filesystem directories")
        
        confirm = input("\nProceed with cleanup? (yes/no): ")
        
        if confirm.lower() == 'yes':
            print("\n4. Performing cleanup...")
            
            # Delete visual analysis cache entries
            if dojo_docs:
                doc_ids = [doc[0] for doc in dojo_docs]
                for doc_id in doc_ids:
                    delete_cache_query = text("DELETE FROM visual_analysis_cache WHERE pitch_deck_id = :doc_id")
                    db_session.execute(delete_cache_query, {"doc_id": doc_id})
                print(f"✅ Deleted visual analysis cache entries")
            
            # Delete project documents
            if dojo_docs:
                for doc in dojo_docs:
                    delete_doc_query = text("DELETE FROM project_documents WHERE id = :doc_id")
                    db_session.execute(delete_doc_query, {"doc_id": doc[0]})
                print(f"✅ Deleted {len(dojo_docs)} documents")
            
            # Delete projects
            if dojo_projects:
                for project in dojo_projects:
                    delete_project_query = text("DELETE FROM projects WHERE id = :project_id")
                    db_session.execute(delete_project_query, {"project_id": project[0]})
                print(f"✅ Deleted {len(dojo_projects)} projects")
            
            # Clean filesystem
            if os.path.exists(dojo_projects_path):
                shutil.rmtree(dojo_projects_path)
                print(f"✅ Deleted filesystem directory: {dojo_projects_path}")
            
            db_session.commit()
            print("✅ Cleanup completed successfully!")
            
        else:
            print("Cleanup cancelled")
        
        db_session.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if 'db_session' in locals():
            db_session.rollback()
    
    print("\n=== CLEANUP COMPLETE ===")

if __name__ == "__main__":
    main()