#!/usr/bin/env python3
"""
Debug script to investigate deck 5946 company ownership issue
Run on production server
"""

import os
import sys
import json

sys.path.append('/opt/review-platform/backend')

def main():
    print("=== DECK 5946 COMPANY OWNERSHIP DEBUG ===")
    
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db_session = next(get_db())
        print("✅ Connected to backend database")
        
        print("\n1. Finding which company deck 5946 actually belongs to...")
        
        # Check both pitch_decks and project_documents tables
        pitch_query = text("""
            SELECT pd.id, pd.file_path, u.email, u.company_name, 'pitch_decks' as source
            FROM pitch_decks pd
            JOIN users u ON pd.user_id = u.id
            WHERE pd.id = :deck_id
        """)
        
        pitch_result = db_session.execute(pitch_query, {"deck_id": 5946}).fetchone()
        
        project_query = text("""
            SELECT pd.id, pd.file_path, u.email, u.company_name, 'project_documents' as source, p.company_id as project_company_id
            FROM project_documents pd
            JOIN projects p ON pd.project_id = p.id
            JOIN users u ON pd.uploaded_by = u.id
            WHERE pd.id = :deck_id AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
        """)
        
        project_result = db_session.execute(project_query, {"deck_id": 5946}).fetchone()
        
        deck_result = pitch_result or project_result
        
        if deck_result:
            if len(deck_result) == 6:  # project_documents result
                deck_id, file_path, user_email, company_name, source_table, project_company_id = deck_result
                print(f"✅ Found deck 5946 in {source_table} table:")
                print(f"  User Email: {user_email}")
                print(f"  User Company Name: {company_name}")
                print(f"  Project Company ID: {project_company_id}")
            else:  # pitch_decks result
                deck_id, file_path, user_email, company_name, source_table = deck_result
                project_company_id = None
                print(f"✅ Found deck 5946 in {source_table} table:")
                print(f"  User Email: {user_email}")
                print(f"  User Company Name: {company_name}")
            
            # Calculate the expected company_id (same logic as backend)
            if company_name:
                import re
                expected_company_id = re.sub(r'[^a-z0-9-]', '', company_name.lower().replace(' ', '-'))
            else:
                expected_company_id = user_email.split('@')[0]
            
            print(f"  Expected Company ID (from user): {expected_company_id}")
            if project_company_id:
                print(f"  Project Company ID: {project_company_id}")
            
            print(f"\n2. Analysis:")
            print(f"  URL attempted: /project/clinaris/deck-viewer/5946")
            print(f"  Expected URL: /project/{expected_company_id}/deck-viewer/5946")
            
            if expected_company_id != "clinaris":
                print(f"  🔴 MISMATCH: Deck belongs to '{expected_company_id}' but accessed via 'clinaris'")
                print(f"  ✅ Security fix working correctly - blocking cross-company access")
            else:
                print(f"  ❓ UNEXPECTED: Company IDs match, but security check failed")
            
            # Check if there are multiple companies this user might be associated with
            print(f"\n3. Checking if user has multiple company associations...")
            
            user_projects_query = text("""
                SELECT DISTINCT p.company_id, p.project_name
                FROM projects p
                JOIN project_documents pd ON p.id = pd.project_id
                WHERE pd.uploaded_by = (
                    SELECT uploaded_by FROM project_documents 
                    WHERE id = :deck_id AND document_type = 'pitch_deck' AND is_active = TRUE
                )
                ORDER BY p.company_id
            """)
            
            user_projects = db_session.execute(user_projects_query, {"deck_id": 5946}).fetchall()
            
            if user_projects:
                print(f"  User has uploaded to {len(user_projects)} different companies:")
                for company_id, project_name in user_projects:
                    print(f"    - {company_id}: {project_name}")
            
        else:
            print("❌ Deck 5946 not found in any table")
        
        print("\n4. Checking navigation flow - how did user reach /project/clinaris/deck-viewer/5946?")
        print("  This could indicate:")
        print("  - User navigated from clinaris gallery but deck belongs to different company")
        print("  - URL manipulation or bookmark with wrong company path")
        print("  - Data inconsistency in project/company associations")
        
        db_session.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== DEBUG COMPLETE ===")

if __name__ == "__main__":
    main()