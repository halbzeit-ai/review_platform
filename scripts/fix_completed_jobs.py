#!/usr/bin/env python3
"""
Fix completed jobs that weren't picked up by backend
Run this on production server to manually update completed jobs
"""

import os
import json
import sys
import sqlite3
from pathlib import Path

def fix_completed_jobs():
    """Find completed result files and update database"""
    
    # Paths
    results_dir = "/mnt/shared/results"
    db_path = "/opt/review-platform/backend/sql_app.db"
    
    if not os.path.exists(results_dir):
        print(f"Results directory not found: {results_dir}")
        return
        
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return
    
    # Find all result files
    result_files = [f for f in os.listdir(results_dir) if f.endswith('_results.json')]
    print(f"Found {len(result_files)} result files")
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current pitch deck statuses
    cursor.execute("SELECT id, file_name, processing_status FROM pitch_decks")
    decks = cursor.fetchall()
    
    print("\n=== Current Pitch Deck Status ===")
    for deck_id, file_name, status in decks:
        print(f"Deck {deck_id}: {file_name} - Status: {status}")
    
    # Process each result file
    for result_file in result_files:
        print(f"\n--- Processing {result_file} ---")
        
        # Extract job info
        if not result_file.startswith('job_'):
            print(f"Skipping non-job file: {result_file}")
            continue
            
        try:
            # Parse job_id format: job_PITCH_DECK_ID_TIMESTAMP_results.json
            parts = result_file.replace('_results.json', '').split('_')
            if len(parts) >= 2:
                pitch_deck_id = int(parts[1])
                print(f"Found pitch deck ID: {pitch_deck_id}")
                
                # Check if this deck exists and needs updating
                cursor.execute("SELECT processing_status FROM pitch_decks WHERE id = ?", (pitch_deck_id,))
                result = cursor.fetchone()
                
                if result:
                    current_status = result[0]
                    print(f"Current status: {current_status}")
                    
                    if current_status != 'completed':
                        # Read the results file
                        result_path = os.path.join(results_dir, result_file)
                        with open(result_path, 'r') as f:
                            results = json.load(f)
                        
                        # Update database
                        cursor.execute(
                            "UPDATE pitch_decks SET processing_status = ?, ai_analysis_results = ? WHERE id = ?",
                            ('completed', json.dumps(results), pitch_deck_id)
                        )
                        conn.commit()
                        print(f"✅ Updated deck {pitch_deck_id} to completed")
                    else:
                        print(f"Deck {pitch_deck_id} already completed")
                else:
                    print(f"Deck {pitch_deck_id} not found in database")
                    
        except (ValueError, IndexError) as e:
            print(f"Error parsing job file {result_file}: {e}")
    
    # Show final status
    cursor.execute("SELECT id, file_name, processing_status FROM pitch_decks")
    decks = cursor.fetchall()
    
    print("\n=== Final Pitch Deck Status ===")
    for deck_id, file_name, status in decks:
        print(f"Deck {deck_id}: {file_name} - Status: {status}")
    
    conn.close()
    print(f"\n✅ Job completion fix completed!")

if __name__ == "__main__":
    fix_completed_jobs()