#!/usr/bin/env python3
"""
Fix remaining decks with completed status but missing results_file_path
"""
import sqlite3
import os
import glob

def fix_remaining_decks():
    # Use the mount path directly
    MOUNT_PATH = "/mnt/CPU-GPU"
    
    # Database path
    db_path = "/opt/review-platform/backend/sql_app.db"
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all decks with completed status but no results_file_path
    cursor.execute("""
        SELECT id, file_name, processing_status
        FROM pitch_decks 
        WHERE processing_status = 'completed' 
        AND (results_file_path IS NULL OR results_file_path = '')
        ORDER BY created_at DESC
    """)
    
    decks = cursor.fetchall()
    
    print(f"Fixing {len(decks)} completed decks with missing results_file_path...\n")
    
    fixed_count = 0
    
    for deck in decks:
        deck_id, file_name, processing_status = deck
        
        print(f"Deck {deck_id}: {file_name}")
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
                SET results_file_path = ?
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
    print(f"Now restart the service: sudo systemctl restart review-platform")

if __name__ == "__main__":
    fix_remaining_decks()