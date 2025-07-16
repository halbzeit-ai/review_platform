#!/usr/bin/env python3
"""
Fix results file paths to point to correct locations
"""
import sqlite3
import os
import glob

def fix_results_paths():
    # Use the mount path directly
    MOUNT_PATH = "/mnt/CPU-GPU"
    
    # Database path
    db_path = "/opt/review-platform/backend/sql_app.db"
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all decks with incorrect results paths
    cursor.execute("""
        SELECT id, file_name, results_file_path, processing_status
        FROM pitch_decks 
        WHERE results_file_path LIKE '/mnt/shared/%'
        OR results_file_path IS NULL
        ORDER BY created_at DESC
    """)
    
    decks = cursor.fetchall()
    
    print(f"Fixing {len(decks)} decks with incorrect results paths...\n")
    
    fixed_count = 0
    
    for deck in decks:
        deck_id, file_name, results_file_path, processing_status = deck
        
        print(f"Deck {deck_id}: {file_name}")
        print(f"  Current results path: {results_file_path}")
        print(f"  Status: {processing_status}")
        
        # Look for results file in old format
        old_results_pattern = f"{MOUNT_PATH}/results/job_{deck_id}_*_results.json"
        old_result_files = glob.glob(old_results_pattern)
        
        if old_result_files:
            # Use the most recent file
            result_file = max(old_result_files, key=os.path.getctime)
            
            # Convert to relative path
            relative_path = result_file.replace(f"{MOUNT_PATH}/", "")
            
            print(f"  ✅ Found results file: {result_file}")
            print(f"  ✅ Setting relative path: {relative_path}")
            
            # Update database
            cursor.execute("""
                UPDATE pitch_decks 
                SET results_file_path = ?, processing_status = 'completed'
                WHERE id = ?
            """, (relative_path, deck_id))
            
            fixed_count += 1
            
        else:
            print(f"  ❌ No results file found for deck {deck_id}")
        
        print()
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"🎉 Fixed {fixed_count} decks!")
    print(f"Restarting the service should now show correct file sizes and statuses.")

if __name__ == "__main__":
    fix_results_paths()