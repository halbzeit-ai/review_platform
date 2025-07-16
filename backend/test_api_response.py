#!/usr/bin/env python3
"""
Test what the API is returning for uploads
"""
import sqlite3
import os
import json

def test_api_response():
    # Use the mount path directly
    MOUNT_PATH = "/mnt/CPU-GPU"
    
    # Database path
    db_path = "/opt/review-platform/backend/sql_app.db"
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Simulate the API query (same as in projects.py)
    company_id = "ramin"
    uploads_query = """
        SELECT pd.id, pd.file_path, pd.created_at, pd.results_file_path, u.email, pd.processing_status
        FROM pitch_decks pd
        JOIN users u ON pd.user_id = u.id
        WHERE u.email LIKE ?
        ORDER BY pd.created_at DESC
        LIMIT 5
    """
    
    cursor.execute(uploads_query, (f"{company_id}@%",))
    uploads_result = cursor.fetchall()
    
    print(f"API Response Simulation for company '{company_id}':")
    print(f"Found {len(uploads_result)} uploads\n")
    
    uploads = []
    for upload in uploads_result:
        deck_id, file_path, created_at, results_file_path, user_email, processing_status = upload
        
        print(f"Deck {deck_id}:")
        print(f"  File path: {file_path}")
        print(f"  Results path: {results_file_path}")
        print(f"  Processing status: {processing_status}")
        print(f"  User email: {user_email}")
        
        # Get file info (simulate API logic)
        full_path = os.path.join(MOUNT_PATH, file_path)
        filename = os.path.basename(file_path)
        file_size = 0
        file_type = "PDF"
        pages = None
        
        if os.path.exists(full_path):
            file_size = os.path.getsize(full_path)
            print(f"  File size: {file_size} bytes")
        else:
            print(f"  ❌ File not found: {full_path}")
        
        # Try to get page count from analysis results
        if results_file_path:
            try:
                if results_file_path.startswith('/'):
                    results_full_path = results_file_path
                else:
                    results_full_path = os.path.join(MOUNT_PATH, results_file_path)
                
                if os.path.exists(results_full_path):
                    with open(results_full_path, 'r') as f:
                        results_data = json.load(f)
                        # Try to get page count from visual analysis results
                        visual_results = results_data.get("visual_analysis_results", [])
                        if visual_results:
                            pages = len(visual_results)
                            print(f"  Pages: {pages}")
                        else:
                            print(f"  No visual analysis results found")
                else:
                    print(f"  ❌ Results file not found: {results_full_path}")
            except Exception as e:
                print(f"  ❌ Error reading results: {e}")
        
        # What the API would return
        api_response = {
            "filename": filename,
            "file_path": file_path,
            "file_size": file_size,
            "upload_date": created_at,
            "file_type": file_type,
            "pages": pages,
            "processing_status": processing_status,  # This is what determines the UI status
            "results_file_path": results_file_path
        }
        
        print(f"  API Response: {json.dumps(api_response, indent=4)}")
        print()
    
    conn.close()

if __name__ == "__main__":
    test_api_response()