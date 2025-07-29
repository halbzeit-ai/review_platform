#!/usr/bin/env python3
"""
Debug script for deck 5947 issue - run this on PRODUCTION server
This will help diagnose the deck viewer problem
"""

import os
import sys
import json
from pathlib import Path

# Add the backend to Python path
sys.path.append('/home/ramin/halbzeit-ai/review_platform/backend')

try:
    from app.db.database import get_db
    from sqlalchemy import text
    from app.core.config import settings
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the production server with the backend environment")
    sys.exit(1)

def main():
    print("=== PRODUCTION DEBUG FOR DECK 5947 ===")
    print(f"Shared filesystem path: {settings.SHARED_FILESYSTEM_MOUNT_PATH}")
    print(f"Shared filesystem exists: {os.path.exists(settings.SHARED_FILESYSTEM_MOUNT_PATH)}")
    print()
    
    # Database checks
    db = next(get_db())
    
    print("=== DATABASE CHECKS ===")
    
    # Check pitch_decks table
    print("1. Checking pitch_decks table for deck 5947...")
    deck_query = text("""
    SELECT pd.id, pd.file_path, pd.results_file_path, u.email, u.company_name, 'pitch_decks' as source
    FROM pitch_decks pd
    JOIN users u ON pd.user_id = u.id
    WHERE pd.id = :deck_id
    """)
    result = db.execute(deck_query, {"deck_id": 5947}).fetchone()
    if result:
        print(f"   ✓ Found in pitch_decks: {result}")
        deck_data = result
    else:
        print("   ✗ Not found in pitch_decks")
        
        # Check project_documents table
        print("2. Checking project_documents table for deck 5947...")
        project_deck_query = text("""
        SELECT pd.id, pd.file_path, NULL as results_file_path, u.email, u.company_name, 'project_documents' as source
        FROM project_documents pd
        JOIN projects p ON pd.project_id = p.id
        JOIN users u ON pd.uploaded_by = u.id
        WHERE pd.id = :deck_id AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
        """)
        result = db.execute(project_deck_query, {"deck_id": 5947}).fetchone()
        if result:
            print(f"   ✓ Found in project_documents: {result}")
            deck_data = result
        else:
            print("   ✗ Not found in project_documents either")
            
            # Show what deck IDs DO exist
            print("\n3. Available deck IDs in both tables:")
            
            # Show project_documents decks
            pd_query = text("""
            SELECT pd.id, pd.file_name, p.company_id 
            FROM project_documents pd
            JOIN projects p ON pd.project_id = p.id
            WHERE pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
            ORDER BY pd.id DESC LIMIT 10
            """)
            pd_results = db.execute(pd_query).fetchall()
            print("   project_documents decks:")
            for row in pd_results:
                print(f"     ID: {row[0]}, File: {row[1]}, Company: {row[2]}")
            
            # Show pitch_decks
            pitch_query = text("""
            SELECT pd.id, pd.file_path, u.company_name
            FROM pitch_decks pd
            JOIN users u ON pd.user_id = u.id
            ORDER BY pd.id DESC LIMIT 10
            """)
            pitch_results = db.execute(pitch_query).fetchall()
            print("   pitch_decks:")
            for row in pitch_results:
                print(f"     ID: {row[0]}, File: {row[1]}, Company: {row[2]}")
            
            print("\n❌ Cannot continue - deck 5947 doesn't exist!")
            db.close()
            return
    
    print(f"\n=== FILESYSTEM CHECKS FOR DECK {deck_data[0]} ===")
    deck_id, file_path, results_file_path, user_email, company_name, source = deck_data
    
    print(f"Deck ID: {deck_id}")
    print(f"File path: {file_path}")
    print(f"Results file path: {results_file_path}")
    print(f"User email: {user_email}")
    print(f"Company name: {company_name}")
    print(f"Data source: {source}")
    
    # Check the PDF file
    if file_path:
        if file_path.startswith('/'):
            full_pdf_path = file_path
        else:
            full_pdf_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, file_path)
        print(f"\n4. PDF file check:")
        print(f"   Full path: {full_pdf_path}")
        print(f"   Exists: {os.path.exists(full_pdf_path)}")
        if os.path.exists(full_pdf_path):
            stat = os.stat(full_pdf_path)
            print(f"   Size: {stat.st_size} bytes")
    
    # Check results file
    if results_file_path:
        if results_file_path.startswith('/'):
            full_results_path = results_file_path
        else:
            full_results_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, results_file_path)
        print(f"\n5. Results file check:")
        print(f"   Full path: {full_results_path}")
        print(f"   Exists: {os.path.exists(full_results_path)}")
        if os.path.exists(full_results_path):
            try:
                with open(full_results_path, 'r') as f:
                    results_data = json.load(f)
                    visual_results = results_data.get("visual_analysis_results", [])
                    print(f"   Visual results count: {len(visual_results)}")
                    if visual_results:
                        print(f"   First slide: {visual_results[0].get('page_number', 'unknown')}")
            except Exception as e:
                print(f"   Error reading results: {e}")
    else:
        print("\n5. No results_file_path in database")
    
    # Check dojo directory structure
    print(f"\n6. Dojo directory structure check:")
    dojo_analysis_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "projects", "dojo", "analysis")
    print(f"   Dojo path: {dojo_analysis_path}")
    print(f"   Exists: {os.path.exists(dojo_analysis_path)}")
    
    if os.path.exists(dojo_analysis_path):
        # Extract deck name from file path
        if file_path:
            deck_name = os.path.splitext(os.path.basename(file_path))[0]
            filesystem_deck_name = deck_name.replace(' ', '_')
            print(f"   Deck name: '{deck_name}'")
            print(f"   Filesystem deck name: '{filesystem_deck_name}'")
            
            print(f"   Available directories:")
            try:
                dirs = os.listdir(dojo_analysis_path)
                for dir_name in sorted(dirs):
                    dir_path = os.path.join(dojo_analysis_path, dir_name)
                    if os.path.isdir(dir_path):
                        print(f"     {dir_name}/")
                        # Check if this directory matches our deck
                        if deck_name in dir_name or filesystem_deck_name in dir_name:
                            print(f"       ✓ MATCHES our deck name!")
                            # Check contents
                            try:
                                contents = os.listdir(dir_path)
                                slide_files = [f for f in contents if f.startswith('slide_') and f.endswith(('.jpg', '.png'))]
                                print(f"       Contents: {len(contents)} items")
                                print(f"       Slide images: {len(slide_files)}")
                                if 'analysis_results.json' in contents:
                                    print(f"       ✓ analysis_results.json present")
                                    # Try to read it
                                    try:
                                        with open(os.path.join(dir_path, 'analysis_results.json'), 'r') as f:
                                            analysis_data = json.load(f)
                                            visual_results = analysis_data.get("visual_analysis_results", [])
                                            print(f"       Visual results: {len(visual_results)} slides")
                                    except Exception as e:
                                        print(f"       Error reading analysis_results.json: {e}")
                                else:
                                    print(f"       ✗ analysis_results.json missing")
                                    
                                if slide_files:
                                    print(f"       Sample slide files: {slide_files[:3]}")
                            except Exception as e:
                                print(f"       Error listing directory: {e}")
            except Exception as e:
                print(f"   Error listing dojo directories: {e}")
    
    # Check company_id mapping
    print(f"\n7. Company ID mapping:")
    if company_name:
        import re
        mapped_company_id = re.sub(r'[^a-z0-9-]', '', re.sub(r'\\s+', '-', company_name.lower()))
        print(f"   Company name: '{company_name}'")
        print(f"   Mapped company ID: '{mapped_company_id}'")
        print(f"   URL company ID: 'nostic-solutions-ag'")
        print(f"   Match: {mapped_company_id == 'nostic-solutions-ag'}")
    
    db.close()
    print(f"\n=== DEBUG COMPLETE ===")
    print("Please share this output to help diagnose the issue!")

if __name__ == "__main__":
    main()