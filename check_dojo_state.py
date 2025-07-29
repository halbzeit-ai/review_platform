#!/usr/bin/env python3
"""
Check current state of dojo data
Run on production server
"""

import os
import sys

sys.path.append('/opt/review-platform/backend')

def main():
    print("=== DOJO STATE CHECK ===")
    
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db_session = next(get_db())
        print("✅ Connected to backend database")
        
        # Check pitch_decks with dojo data
        dojo_files_count = db_session.execute(text(
            "SELECT COUNT(*) FROM pitch_decks WHERE data_source = 'dojo'"
        )).fetchone()[0]
        
        print(f"Dojo files in pitch_decks table: {dojo_files_count}")
        
        # Check visual_analysis_cache entries
        cache_count = db_session.execute(text(
            "SELECT COUNT(*) FROM visual_analysis_cache"
        )).fetchone()[0]
        
        print(f"Visual analysis cache entries: {cache_count}")
        
        # Check cache entries specifically for dojo decks
        dojo_cache_count = db_session.execute(text("""
            SELECT COUNT(*) FROM visual_analysis_cache vac
            INNER JOIN pitch_decks pd ON vac.pitch_deck_id = pd.id
            WHERE pd.data_source = 'dojo'
        """)).fetchone()[0]
        
        print(f"Cache entries for dojo decks: {dojo_cache_count}")
        
        # Check project_documents table for dojo-related projects
        project_docs_count = db_session.execute(text("""
            SELECT COUNT(*) FROM project_documents pd
            JOIN projects p ON pd.project_id = p.id
            WHERE LOWER(p.company_id) LIKE '%dojo%' 
               OR LOWER(p.project_name) LIKE '%dojo%'
               OR p.is_test = TRUE
        """)).fetchone()[0]
        
        print(f"Project documents in dojo projects: {project_docs_count}")
        
        # Show some sample data if any exists
        if dojo_files_count > 0:
            print(f"\nSample dojo files:")
            sample_files = db_session.execute(text(
                "SELECT id, file_name, created_at FROM pitch_decks WHERE data_source = 'dojo' LIMIT 5"
            )).fetchall()
            
            for file in sample_files:
                print(f"  ID {file[0]}: {file[1]} (created: {file[2]})")
        
        if project_docs_count > 0:
            print(f"\nSample project documents:")
            sample_docs = db_session.execute(text("""
                SELECT pd.id, pd.file_name, p.company_id, p.project_name
                FROM project_documents pd
                JOIN projects p ON pd.project_id = p.id
                WHERE LOWER(p.company_id) LIKE '%dojo%' 
                   OR LOWER(p.project_name) LIKE '%dojo%'
                   OR p.is_test = TRUE
                LIMIT 5
            """)).fetchall()
            
            for doc in sample_docs:
                print(f"  Doc ID {doc[0]}: {doc[1]} (company: {doc[2]}, project: {doc[3]})")
        
        db_session.close()
        
        print(f"\n=== SUMMARY ===")
        print(f"The interface shows '182 cached decks' but actual state is:")
        print(f"  - Dojo files: {dojo_files_count}")
        print(f"  - Cache entries: {cache_count}")
        print(f"  - Project docs: {project_docs_count}")
        
        if dojo_files_count == 0 and project_docs_count == 0:
            print("  ✅ All dojo data successfully cleaned up")
            print("  🔄 Interface needs refresh to update cached counts")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== STATE CHECK COMPLETE ===")

if __name__ == "__main__":
    main()