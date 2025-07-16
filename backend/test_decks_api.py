#!/usr/bin/env python3
"""
Test what the /decks API is returning
"""
import sqlite3
import os

def test_decks_api():
    # Use the mount path directly
    MOUNT_PATH = "/mnt/CPU-GPU"
    
    # Database path
    db_path = "/opt/review-platform/backend/sql_app.db"
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Simulate the decks API query for startup users
    cursor.execute("""
        SELECT pd.id, pd.file_name, pd.file_path, pd.results_file_path, pd.company_id, 
               pd.processing_status, pd.created_at, pd.user_id
        FROM pitch_decks pd
        WHERE pd.company_id = 'ramin' OR pd.user_id = 1
        ORDER BY pd.created_at DESC
        LIMIT 10
    """)
    
    decks = cursor.fetchall()
    
    print(f"Decks API Response Simulation:")
    print(f"Found {len(decks)} decks\n")
    
    for deck in decks:
        deck_id, file_name, file_path, results_file_path, company_id, processing_status, created_at, user_id = deck
        
        print(f"Deck {deck_id}: {file_name}")
        print(f"  file_path: {file_path}")
        print(f"  results_file_path: {results_file_path}")
        print(f"  company_id: {company_id}")
        print(f"  processing_status: {processing_status}")
        print(f"  created_at: {created_at}")
        
        # Check if results file exists
        if results_file_path:
            if results_file_path.startswith('/'):
                results_full_path = results_file_path
            else:
                results_full_path = os.path.join(MOUNT_PATH, results_file_path)
            
            if os.path.exists(results_full_path):
                print(f"  ✅ Results file exists: {results_full_path}")
            else:
                print(f"  ❌ Results file missing: {results_full_path}")
        else:
            print(f"  ❌ No results_file_path set")
        
        # What determines if Deck Viewer button is enabled
        button_enabled = results_file_path is not None and results_file_path != ""
        print(f"  Deck Viewer button enabled: {button_enabled}")
        
        print()
    
    conn.close()

if __name__ == "__main__":
    test_decks_api()