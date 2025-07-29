#!/usr/bin/env python3
"""
Debug script to test the actual API endpoint - run this on PRODUCTION server
This simulates the exact API call that the frontend is making
"""

import os
import sys
import json
import asyncio
from unittest.mock import MagicMock

# Add the backend to Python path
sys.path.append('/home/ramin/halbzeit-ai/review_platform/backend')

try:
    from app.api.projects import get_deck_analysis
    from app.db.database import get_db
    from app.db.models import User
    from sqlalchemy.orm import Session
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running this from the production server with the backend environment")
    sys.exit(1)

async def test_api_endpoint():
    print("=== TESTING API ENDPOINT DIRECTLY ===")
    print("Simulating: GET /api/projects/nostic-solutions-ag/deck-analysis/5947")
    print()
    
    # Create a mock GP user
    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.email = "test@gp.com"
    mock_user.role = "gp"
    mock_user.company_name = "Test GP"
    
    # Get database session
    db = next(get_db())
    
    try:
        # Call the actual endpoint function
        result = await get_deck_analysis(
            company_id="nostic-solutions-ag",
            deck_id=5947,
            db=db,
            current_user=mock_user
        )
        
        print("✅ API call succeeded!")
        print(f"Result type: {type(result)}")
        print(f"Deck ID: {result.deck_id}")
        print(f"Deck name: {result.deck_name}")
        print(f"Company ID: {result.company_id}")
        print(f"Total slides: {result.total_slides}")
        print(f"Processing metadata: {result.processing_metadata}")
        
        if result.slides:
            print(f"\nSlide details:")
            for i, slide in enumerate(result.slides[:3]):  # Show first 3 slides
                print(f"  Slide {slide.page_number}:")
                print(f"    Image path: {slide.slide_image_path}")
                print(f"    Description length: {len(slide.description)} chars")
                print(f"    Description preview: {slide.description[:100]}...")
        
    except Exception as e:
        print("❌ API call failed!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        
        # Print the full traceback
        import traceback
        print(f"\nFull traceback:")
        traceback.print_exc()
    
    finally:
        db.close()

def test_sync_parts():
    """Test the database queries separately"""
    print("\n=== TESTING DATABASE QUERIES ===")
    
    db = next(get_db())
    
    try:
        from sqlalchemy import text
        
        # Test the exact queries from the endpoint
        print("1. Testing pitch_decks query...")
        deck_query = text("""
        SELECT pd.id, pd.file_path, pd.results_file_path, u.email, u.company_name, 'pitch_decks' as source
        FROM pitch_decks pd
        JOIN users u ON pd.user_id = u.id
        WHERE pd.id = :deck_id
        """)
        
        deck_result = db.execute(deck_query, {"deck_id": 5947}).fetchone()
        if deck_result:
            print(f"   ✓ Found in pitch_decks: {deck_result}")
        else:
            print("   ✗ Not found in pitch_decks")
            
            print("2. Testing project_documents query...")
            project_deck_query = text("""
            SELECT pd.id, pd.file_path, NULL as results_file_path, u.email, u.company_name, 'project_documents' as source
            FROM project_documents pd
            JOIN projects p ON pd.project_id = p.id
            JOIN users u ON pd.uploaded_by = u.id
            WHERE pd.id = :deck_id AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
            """)
            
            deck_result = db.execute(project_deck_query, {"deck_id": 5947}).fetchone()
            if deck_result:
                print(f"   ✓ Found in project_documents: {deck_result}")
            else:
                print("   ✗ Not found in project_documents either")
                
                # Show what IDs exist with nostic in the name
                print("3. Searching for 'nostic' in company names...")
                search_query = text("""
                SELECT pd.id, pd.file_name, p.company_id, u.company_name
                FROM project_documents pd
                JOIN projects p ON pd.project_id = p.id
                JOIN users u ON pd.uploaded_by = u.id
                WHERE pd.document_type = 'pitch_deck' 
                AND pd.is_active = TRUE
                AND (LOWER(u.company_name) LIKE '%nostic%' OR LOWER(p.company_id) LIKE '%nostic%')
                """)
                
                nostic_results = db.execute(search_query).fetchall()
                if nostic_results:
                    print("   Found Nostic-related decks:")
                    for row in nostic_results:
                        print(f"     ID: {row[0]}, File: {row[1]}, Company ID: {row[2]}, Company Name: {row[3]}")
                else:
                    print("   No Nostic-related decks found")
                    
                    # Show ALL decks to see what we have
                    print("4. Showing all available decks...")
                    all_query = text("""
                    SELECT pd.id, pd.file_name, p.company_id, u.company_name
                    FROM project_documents pd
                    JOIN projects p ON pd.project_id = p.id
                    JOIN users u ON pd.uploaded_by = u.id
                    WHERE pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
                    ORDER BY pd.id DESC
                    LIMIT 20
                    """)
                    
                    all_results = db.execute(all_query).fetchall()
                    if all_results:
                        print("   All available decks (last 20):")
                        for row in all_results:
                            print(f"     ID: {row[0]}, File: {row[1]}, Company ID: {row[2]}, Company Name: {row[3]}")
    
    finally:
        db.close()

if __name__ == "__main__":
    print("Starting production debug...")
    test_sync_parts()
    print("\nTesting async endpoint...")
    asyncio.run(test_api_endpoint())
    print("\nDebug complete!")