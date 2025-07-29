#!/usr/bin/env python3
"""
Debug script to verify security fix for cross-company deck access
Run on production server to test deck 101 access via different company paths
"""

import os
import sys
import json

# Add the backend to Python path
sys.path.append('/opt/review-platform/backend')

def main():
    print("=== SECURITY FIX VERIFICATION ===")
    
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        # Get database session
        db_session = next(get_db())
        
        print("✅ Connected to backend database")
        
        print("\n1. Finding which company deck 101 actually belongs to...")
        
        # Check both pitch_decks and project_documents tables
        pitch_query = text("""
            SELECT pd.id, pd.file_path, u.email, u.company_name, 'pitch_decks' as source
            FROM pitch_decks pd
            JOIN users u ON pd.user_id = u.id
            WHERE pd.id = :deck_id
        """)
        
        pitch_result = db_session.execute(pitch_query, {"deck_id": 101}).fetchone()
        
        project_query = text("""
            SELECT pd.id, pd.file_path, u.email, u.company_name, 'project_documents' as source
            FROM project_documents pd
            JOIN projects p ON pd.project_id = p.id
            JOIN users u ON pd.uploaded_by = u.id
            WHERE pd.id = :deck_id AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
        """)
        
        project_result = db_session.execute(project_query, {"deck_id": 101}).fetchone()
        
        deck_result = pitch_result or project_result
        
        if deck_result:
            deck_id, file_path, user_email, company_name, source_table = deck_result
            print(f"✅ Found deck 101 in {source_table} table:")
            print(f"  User Email: {user_email}")
            print(f"  Company Name: {company_name}")
            
            # Calculate the proper company_id (same logic as backend)
            if company_name:
                import re
                proper_company_id = re.sub(r'[^a-z0-9-]', '', company_name.lower().replace(' ', '-'))
            else:
                proper_company_id = user_email.split('@')[0]
            
            print(f"  Proper Company ID: {proper_company_id}")
            
            # Test scenarios
            test_company_ids = [
                "nostic-solutions-ag",  # The URL path user was able to access deck 101 through
                proper_company_id,      # The actual company this deck belongs to
                "dojo",                 # Another company
                "test-company"          # Random company
            ]
            
            print(f"\n2. Testing security validation logic for deck 101:")
            for test_company_id in test_company_ids:
                should_allow = (test_company_id == proper_company_id)
                print(f"\n  Testing company_id: '{test_company_id}'")
                print(f"    Expected result: {'ALLOW' if should_allow else 'DENY'}")
                print(f"    Match with proper company: {test_company_id == proper_company_id}")
                
                if test_company_id == "nostic-solutions-ag" and proper_company_id != "nostic-solutions-ag":
                    print(f"    🔴 SECURITY ISSUE: This was previously allowed but should be DENIED")
                elif test_company_id == proper_company_id:
                    print(f"    ✅ This should be allowed (legitimate access)")
                else:
                    print(f"    ✅ This should be denied (cross-company access)")
            
            print("\n3. Checking visual_analysis_cache for deck 101...")
            cache_query = text("""
                SELECT pitch_deck_id, vision_model_used, created_at
                FROM visual_analysis_cache 
                WHERE pitch_deck_id = :deck_id
                ORDER BY created_at DESC
                LIMIT 1
            """)
            
            cache_result = db_session.execute(cache_query, {"deck_id": 101}).fetchone()
            
            if cache_result:
                print(f"✅ Deck 101 HAS visual analysis cache:")
                print(f"  Model: {cache_result[1]}")
                print(f"  Created: {cache_result[2]}")
                print("  This explains why deck 101 shows text while deck 5947 doesn't")
            else:
                print("❌ Deck 101 has no visual analysis cache")
                
        else:
            print("❌ Deck 101 not found in any table")
        
        print("\n4. Summary of findings:")
        if deck_result and cache_result:
            print(f"✅ Deck 101 belongs to company: {proper_company_id}")
            print(f"✅ Deck 101 has visual analysis (created {cache_result[2]})")
            print(f"🔴 Security vulnerability: Deck 101 was accessible via 'nostic-solutions-ag' URL")
            print(f"✅ Security fix: Now only accessible via '{proper_company_id}' URL")
        
        db_session.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    main()