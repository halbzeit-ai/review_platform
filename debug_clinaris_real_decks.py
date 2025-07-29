#!/usr/bin/env python3
"""
Debug script to find what deck(s) actually belong to clinaris company
and trace how the navigation led to the wrong deck 5946
Run on production server
"""

import os
import sys
import json

sys.path.append('/opt/review-platform/backend')

def main():
    print("=== FINDING REAL CLINARIS DECKS ===")
    
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db_session = next(get_db())
        print("✅ Connected to backend database")
        
        print("\n1. Finding all decks that legitimately belong to 'clinaris' company...")
        
        # Check both tables for clinaris decks
        print("  Checking pitch_decks table...")
        pitch_decks_query = text("""
            SELECT pd.id, pd.file_path, u.email, u.company_name, pd.created_at
            FROM pitch_decks pd
            JOIN users u ON pd.user_id = u.id
            WHERE LOWER(REPLACE(u.company_name, ' ', '-')) LIKE '%clinaris%' 
               OR u.email LIKE '%clinaris%'
            ORDER BY pd.created_at DESC
        """)
        
        pitch_results = db_session.execute(pitch_decks_query).fetchall()
        
        if pitch_results:
            print(f"  ✅ Found {len(pitch_results)} decks in pitch_decks for clinaris:")
            for deck in pitch_results:
                deck_id, file_path, user_email, company_name, created_at = deck
                print(f"    Deck ID: {deck_id}, User: {user_email}, Company: {company_name}, Created: {created_at}")
        else:
            print("  ❌ No decks found in pitch_decks for clinaris")
        
        print("\n  Checking project_documents table...")
        project_docs_query = text("""
            SELECT pd.id, pd.file_name, pd.project_id, u.email, u.company_name, p.company_id, pd.upload_date
            FROM project_documents pd
            JOIN projects p ON pd.project_id = p.id
            JOIN users u ON pd.uploaded_by = u.id
            WHERE pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
              AND (p.company_id = 'clinaris' 
                   OR LOWER(REPLACE(u.company_name, ' ', '-')) LIKE '%clinaris%'
                   OR u.email LIKE '%clinaris%')
            ORDER BY pd.upload_date DESC
        """)
        
        project_docs_results = db_session.execute(project_docs_query).fetchall()
        
        if project_docs_results:
            print(f"  ✅ Found {len(project_docs_results)} decks in project_documents for clinaris:")
            for deck in project_docs_results:
                deck_id, file_name, project_id, user_email, company_name, project_company_id, upload_date = deck
                
                # Calculate user company ID
                if company_name:
                    import re
                    user_company_id = re.sub(r'[^a-z0-9-]', '', company_name.lower().replace(' ', '-'))
                else:
                    user_company_id = user_email.split('@')[0]
                
                match_reason = []
                if project_company_id == 'clinaris':
                    match_reason.append("project company")
                if 'clinaris' in user_company_id:
                    match_reason.append("user company")
                if 'clinaris' in user_email:
                    match_reason.append("user email")
                
                print(f"    Deck ID: {deck_id}, Project: {project_id}, User: {user_email}")
                print(f"      User Company: {company_name} -> {user_company_id}")
                print(f"      Project Company: {project_company_id}")
                print(f"      Match Reason: {', '.join(match_reason)}")
                print(f"      Upload Date: {upload_date}")
        else:
            print("  ❌ No decks found in project_documents for clinaris")
        
        print("\n2. Investigating how Project 345 ended up in clinaris gallery...")
        
        project_345_query = text("""
            SELECT p.id, p.company_id, p.project_name, p.created_at,
                   COUNT(pd.id) as doc_count
            FROM projects p
            LEFT JOIN project_documents pd ON p.id = pd.project_id AND pd.is_active = TRUE
            WHERE p.id = 345
            GROUP BY p.id, p.company_id, p.project_name, p.created_at
        """)
        
        project_345_result = db_session.execute(project_345_query).fetchone()
        
        if project_345_result:
            project_id, project_company_id, project_name, created_at, doc_count = project_345_result
            print(f"  Project 345 details:")
            print(f"    Company ID: {project_company_id}")
            print(f"    Project Name: {project_name}")
            print(f"    Created: {created_at}")
            print(f"    Document Count: {doc_count}")
            
            if project_company_id == 'clinaris':
                print(f"    ✅ Project 345 legitimately belongs to clinaris")
            else:
                print(f"    🔴 Project 345 belongs to '{project_company_id}', not clinaris!")
                print(f"    This means the gallery is showing wrong projects!")
        
        print("\n3. Checking what the getAllProjects endpoint would return for clinaris...")
        
        # Simulate the getAllProjects query for clinaris company
        all_projects_query = text("""
            SELECT p.id, p.company_id, p.project_name, p.company_offering,
                   COUNT(DISTINCT pd.id) as document_count,
                   COUNT(DISTINCT pi.id) as interaction_count
            FROM projects p
            LEFT JOIN project_documents pd ON p.id = pd.project_id AND pd.is_active = TRUE
            LEFT JOIN project_interactions pi ON p.id = pi.project_id AND pi.status = 'active'
            WHERE p.company_id = 'clinaris' AND p.is_active = TRUE
            GROUP BY p.id, p.company_id, p.project_name, p.company_offering
            ORDER BY p.created_at DESC
        """)
        
        clinaris_projects = db_session.execute(all_projects_query).fetchall()
        
        if clinaris_projects:
            print(f"  ✅ getAllProjects would return {len(clinaris_projects)} projects for clinaris:")
            for project in clinaris_projects:
                p_id, p_company_id, p_name, p_offering, doc_count, interaction_count = project
                print(f"    Project {p_id}: {p_name}")
                print(f"      Company: {p_company_id}")
                print(f"      Documents: {doc_count}")
                print(f"      Interactions: {interaction_count}")
                print(f"      Offering: {p_offering[:100] if p_offering else 'None'}...")
                
                if p_id == 345:
                    print(f"      🔴 This is Project 345 that led to deck 5946!")
        else:
            print("  ❌ No projects found for clinaris company")
        
        print("\n4. Finding what deck(s) Project 345 should actually show...")
        
        project_345_docs_query = text("""
            SELECT pd.id, pd.file_name, pd.document_type, u.email, u.company_name
            FROM project_documents pd
            JOIN users u ON pd.uploaded_by = u.id
            WHERE pd.project_id = 345 AND pd.is_active = TRUE
            ORDER BY pd.upload_date DESC
        """)
        
        project_345_docs = db_session.execute(project_345_docs_query).fetchall()
        
        if project_345_docs:
            print(f"  Project 345 contains {len(project_345_docs)} documents:")
            for doc in project_345_docs:
                doc_id, file_name, doc_type, user_email, user_company = doc
                print(f"    Document {doc_id} ({doc_type}): {file_name}")
                print(f"      Uploader: {user_email} from {user_company}")
                
                if doc_id == 5946:
                    print(f"      🔴 This is the problematic deck 5946!")
        
        print("\n5. Summary and Resolution:")
        if project_docs_results:
            legitimate_clinaris_decks = [deck[0] for deck in project_docs_results if deck[5] == 'clinaris']  # project_company_id == 'clinaris'
            print(f"  Real clinaris deck IDs: {legitimate_clinaris_decks}")
        else:
            print("  No legitimate clinaris decks found in project system")
            
        if pitch_results:
            legacy_clinaris_decks = [deck[0] for deck in pitch_results]
            print(f"  Legacy clinaris deck IDs: {legacy_clinaris_decks}")
        else:
            print("  No legacy clinaris decks found")
        
        print(f"\n  The navigation issue is:")
        print(f"  - You accessed a legitimate clinaris project (345)")  
        print(f"  - But project 345 contains deck 5946 from a different company")
        print(f"  - This suggests either:")
        print(f"    a) Data corruption where wrong decks got associated with projects")
        print(f"    b) Multi-company projects are allowed but security wasn't enforced")
        print(f"    c) Bug in document upload/assignment logic")
        
        db_session.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== DEBUG COMPLETE ===")

if __name__ == "__main__":
    main()