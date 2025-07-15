#!/usr/bin/env python3
"""
Fix job 10 that completed but wasn't picked up by backend
"""

import os
import json
import sqlite3

def fix_job_10():
    """Fix the specific job that completed but wasn't picked up"""
    
    # Paths
    results_file = "/mnt/shared/results/job_10_1752585680_results.json"
    db_path = "/opt/review-platform/backend/sql_app.db"
    
    if not os.path.exists(results_file):
        print(f"❌ Results file not found: {results_file}")
        return
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    
    # Read results
    with open(results_file, 'r') as f:
        results = json.load(f)
    
    print(f"✅ Found results file: {results_file}")
    print(f"   Results size: {len(json.dumps(results))} bytes")
    
    # Update database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current status
    cursor.execute("SELECT id, file_name, processing_status FROM pitch_decks WHERE id = 10")
    deck = cursor.fetchone()
    
    if deck:
        deck_id, file_name, status = deck
        print(f"✅ Found deck {deck_id}: {file_name} - Status: {status}")
        
        if status != 'completed':
            # Update database
            cursor.execute(
                "UPDATE pitch_decks SET processing_status = ?, ai_analysis_results = ? WHERE id = ?",
                ('completed', json.dumps(results), 10)
            )
            conn.commit()
            print(f"✅ Updated deck 10 to completed with results")
        else:
            print(f"✅ Deck 10 already marked as completed")
    else:
        print(f"❌ Deck 10 not found in database")
    
    conn.close()
    print(f"✅ Job 10 fix completed!")

if __name__ == "__main__":
    fix_job_10()