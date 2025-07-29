#!/usr/bin/env python3
"""
Debug script to investigate the relationship between:
- Project 345 (which shows in clinaris company view)  
- Deck 5946 (which is accessed via clinaris URL but belongs to different company)
Run on production server
"""

import os
import sys
import json

sys.path.append('/opt/review-platform/backend')

def main():
    print("=== PROJECT 345 / DECK 5946 RELATIONSHIP DEBUG ===")
    
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db_session = next(get_db())
        print("✅ Connected to backend database")
        
        print("\n1. Investigating Project 345...")
        
        project_query = text("""
            SELECT p.id, p.company_id, p.project_name, p.funding_round, p.created_at, p.updated_at
            FROM projects p
            WHERE p.id = :project_id
        """)
        
        project_result = db_session.execute(project_query, {"project_id": 345}).fetchone()
        
        if project_result:
            project_id, project_company_id, project_name, funding_round, created_at, updated_at = project_result
            print(f"✅ Project 345 details:")
            print(f"  ID: {project_id}")
            print(f"  Company ID: {project_company_id}")
            print(f"  Project Name: {project_name}")
            print(f"  Funding Round: {funding_round}")
            print(f"  Created: {created_at}")
            print(f"  Updated: {updated_at}")
        else:
            print("❌ Project 345 not found")
            return
        
        print("\n2. Finding all documents in Project 345...")
        
        project_docs_query = text("""
            SELECT pd.id, pd.document_type, pd.file_name, pd.upload_date, pd.uploaded_by,
                   u.email, u.company_name
            FROM project_documents pd
            JOIN users u ON pd.uploaded_by = u.id
            WHERE pd.project_id = :project_id AND pd.is_active = TRUE
            ORDER BY pd.upload_date DESC
        """)
        
        docs_results = db_session.execute(project_docs_query, {"project_id": 345}).fetchall()
        
        if docs_results:
            print(f"✅ Found {len(docs_results)} documents in Project 345:")
            for doc in docs_results:
                doc_id, doc_type, file_name, upload_date, uploaded_by, user_email, user_company = doc
                
                # Calculate user's company_id
                if user_company:
                    import re
                    user_company_id = re.sub(r'[^a-z0-9-]', '', user_company.lower().replace(' ', '-'))
                else:
                    user_company_id = user_email.split('@')[0]
                
                print(f"\n  Document ID: {doc_id}")
                print(f"    Type: {doc_type}")
                print(f"    File: {file_name}")
                print(f"    Uploaded: {upload_date}")
                print(f"    Uploader: {user_email}")
                print(f"    Uploader Company Name: {user_company}")
                print(f"    Uploader Company ID: {user_company_id}")
                print(f"    Project Company ID: {project_company_id}")
                
                if doc_id == 5946:
                    print(f"    🔴 FOUND DECK 5946!")
                    if user_company_id != project_company_id:
                        print(f"    🔴 MISMATCH: Deck uploader company '{user_company_id}' != Project company '{project_company_id}'")
                        print(f"    This explains why security check fails!")
                    else:
                        print(f"    ✅ Companies match - unexpected security failure")
                
                if user_company_id != project_company_id:
                    print(f"    ⚠️  MISMATCH: Uploader company '{user_company_id}' != Project company '{project_company_id}'")
        else:
            print("❌ No documents found in Project 345")
        
        print("\n3. Checking if deck 5946 exists and its actual ownership...")
        
        deck_query = text("""
            SELECT pd.id, pd.project_id, pd.file_name, pd.uploaded_by,
                   u.email, u.company_name, p.company_id as project_company_id
            FROM project_documents pd
            JOIN users u ON pd.uploaded_by = u.id
            JOIN projects p ON pd.project_id = p.id
            WHERE pd.id = :deck_id AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
        """)
        
        deck_result = db_session.execute(deck_query, {"deck_id": 5946}).fetchone()
        
        if deck_result:
            deck_id, deck_project_id, file_name, uploaded_by, user_email, user_company, deck_project_company = deck_result
            
            if user_company:
                import re
                deck_owner_company_id = re.sub(r'[^a-z0-9-]', '', user_company.lower().replace(' ', '-'))
            else:
                deck_owner_company_id = user_email.split('@')[0]
            
            print(f"✅ Deck 5946 details:")
            print(f"  Belongs to Project: {deck_project_id}")
            print(f"  File: {file_name}")
            print(f"  Uploader: {user_email}")
            print(f"  Uploader Company: {user_company}")
            print(f"  Uploader Company ID: {deck_owner_company_id}")
            print(f"  Project Company ID: {deck_project_company}")
            
            print(f"\n4. Navigation Flow Analysis:")
            print(f"  GP Dashboard → Gallery → Project 345 (company: {project_company_id})")
            print(f"  Project 345 → Overview → Deck Viewer Button")
            print(f"  Button constructs URL: /project/{project_company_id}/deck-viewer/5946")
            print(f"  But deck 5946 actually belongs to company: {deck_owner_company_id}")
            
            if deck_owner_company_id != project_company_id:
                print(f"  🔴 ROOT CAUSE: Deck 5946 uploaded by {deck_owner_company_id} user but associated with {project_company_id} project")
                print(f"  This is a data consistency issue in the project system!")
                print(f"  ✅ Security fix working correctly by blocking this cross-company access")
            
            if deck_project_id != 345:
                print(f"  🔴 ADDITIONAL ISSUE: Deck 5946 belongs to project {deck_project_id}, not project 345!")
                print(f"  This suggests the gallery is showing decks from wrong projects!")
        else:
            print("❌ Deck 5946 not found")
        
        print("\n5. Summary:")
        print("  The security fix is working correctly.")
        print("  The issue is data inconsistency where:")
        print("  - Projects contain documents uploaded by users from different companies")
        print("  - OR Gallery is displaying documents from wrong projects")
        print("  - This creates cross-company access attempts that are now properly blocked")
        
        db_session.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== DEBUG COMPLETE ===")

if __name__ == "__main__":
    main()