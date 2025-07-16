#!/usr/bin/env python3
"""
Script to fix completed deck processing status and results_file_path
"""
import sqlite3
import os
import json
import glob
from datetime import datetime

def fix_completed_decks():
    # Database path
    db_path = "/opt/review-platform/backend/sql_app.db"
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all decks with processing status
    cursor.execute("""
        SELECT id, file_name, processing_status, results_file_path, company_id, created_at
        FROM pitch_decks 
        WHERE processing_status = 'processing' OR results_file_path IS NULL
        ORDER BY created_at DESC
    """)
    
    decks = cursor.fetchall()
    
    print(f"Found {len(decks)} decks to check...")
    
    for deck in decks:
        deck_id, file_name, processing_status, results_file_path, company_id, created_at = deck
        
        print(f"\nChecking deck {deck_id}: {file_name}")
        print(f"  Current status: {processing_status}")
        print(f"  Results path: {results_file_path}")
        
        # Look for result files in the old format: /mnt/CPU-GPU/results/job_{deck_id}_*_results.json
        old_results_pattern = f"/mnt/CPU-GPU/results/job_{deck_id}_*_results.json"
        old_result_files = glob.glob(old_results_pattern)
        
        # Look for result files in the new format: /mnt/shared/projects/{company_id}/analysis/{deck_name}/results.json
        if company_id and file_name:
            deck_name = os.path.splitext(file_name)[0]
            new_results_path = f"/mnt/shared/projects/{company_id}/analysis/{deck_name}/results.json"
        else:
            new_results_path = None
        
        result_file_path = None
        
        # Check old format first
        if old_result_files:
            # Use the most recent file
            result_file_path = max(old_result_files, key=os.path.getctime)
            print(f"  Found old format result file: {result_file_path}")
        
        # Check new format
        elif new_results_path and os.path.exists(new_results_path):
            result_file_path = new_results_path
            print(f"  Found new format result file: {result_file_path}")
        
        if result_file_path:
            # Verify the file contains valid analysis results
            try:
                with open(result_file_path, 'r') as f:
                    results_data = json.load(f)
                
                # Check if it has the expected structure
                if 'visual_analysis_results' in results_data or 'company_offering' in results_data:
                    print(f"  ✅ Valid analysis results found")
                    
                    # Convert to relative path for database storage
                    if result_file_path.startswith('/mnt/shared/'):
                        relative_path = result_file_path.replace('/mnt/shared/', '')
                    elif result_file_path.startswith('/mnt/CPU-GPU/'):
                        relative_path = result_file_path.replace('/mnt/CPU-GPU/', '')
                    else:
                        relative_path = result_file_path
                    
                    # Update database
                    cursor.execute("""
                        UPDATE pitch_decks 
                        SET processing_status = 'completed', results_file_path = ?
                        WHERE id = ?
                    """, (relative_path, deck_id))
                    
                    print(f"  ✅ Updated deck {deck_id} to completed status")
                    print(f"  ✅ Set results_file_path to: {relative_path}")
                    
                else:
                    print(f"  ❌ Invalid analysis results structure")
                    
            except Exception as e:
                print(f"  ❌ Error reading results file: {e}")
        else:
            print(f"  ❌ No results file found")
    
    # Commit changes
    conn.commit()
    conn.close()
    
    print(f"\n🎉 Database update completed!")
    print(f"Run this to verify:")
    print(f"sqlite3 {db_path} \"SELECT id, file_name, processing_status, results_file_path FROM pitch_decks ORDER BY created_at DESC LIMIT 5;\"")

if __name__ == "__main__":
    fix_completed_decks()