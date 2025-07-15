#!/usr/bin/env python3
"""
Debug script to diagnose why results aren't showing on website
Run this on production server to check all components
"""

import os
import json
import sqlite3
import sys
import requests
from pathlib import Path

def debug_results_issue():
    """Comprehensive debugging of the results display issue"""
    
    print("=== DEBUGGING RESULTS DISPLAY ISSUE ===\n")
    
    # 1. Check filesystem
    print("1. FILESYSTEM CHECK")
    print("-" * 50)
    
    results_dir = "/mnt/shared/results"
    if not os.path.exists(results_dir):
        print(f"❌ Results directory not found: {results_dir}")
        return
    else:
        print(f"✅ Results directory exists: {results_dir}")
    
    result_files = [f for f in os.listdir(results_dir) if f.endswith('_results.json')]
    print(f"✅ Found {len(result_files)} result files:")
    for f in result_files:
        file_path = os.path.join(results_dir, f)
        size = os.path.getsize(file_path)
        print(f"   - {f} ({size} bytes)")
    
    # 2. Check database
    print(f"\n2. DATABASE CHECK")
    print("-" * 50)
    
    db_path = "/opt/review-platform/backend/sql_app.db"
    if not os.path.exists(db_path):
        print(f"❌ Database not found: {db_path}")
        return
    else:
        print(f"✅ Database exists: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, file_name, processing_status, ai_analysis_results FROM pitch_decks ORDER BY id DESC LIMIT 5")
    decks = cursor.fetchall()
    
    print(f"✅ Found {len(decks)} pitch decks (latest 5):")
    for deck_id, file_name, status, results in decks:
        has_results = "Yes" if results else "No"
        print(f"   - Deck {deck_id}: {file_name}")
        print(f"     Status: {status}")
        print(f"     Has results: {has_results}")
        
        # Check if corresponding result file exists
        matching_files = [f for f in result_files if f.startswith(f'job_{deck_id}_')]
        if matching_files:
            print(f"     Matching result files: {matching_files}")
        else:
            print(f"     No matching result files found")
        print()
    
    # 3. Check API endpoints
    print("3. API ENDPOINT CHECK")
    print("-" * 50)
    
    # Test if backend is responding
    try:
        response = requests.get("http://localhost:8000/api/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is responding")
        else:
            print(f"⚠️  Backend responding with status: {response.status_code}")
    except Exception as e:
        print(f"❌ Backend not responding: {e}")
    
    # Test processing status endpoint for latest deck
    if decks:
        latest_deck_id = decks[0][0]
        try:
            response = requests.get(f"http://localhost:8000/api/documents/processing-status/{latest_deck_id}", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Processing status API works for deck {latest_deck_id}:")
                print(f"   Status: {data.get('processing_status', 'Unknown')}")
            else:
                print(f"⚠️  Processing status API returned: {response.status_code}")
        except Exception as e:
            print(f"❌ Processing status API failed: {e}")
    
    # 4. Check file-based processing service
    print(f"\n4. FILE-BASED PROCESSING SERVICE CHECK")
    print("-" * 50)
    
    # Check if the service can read result files
    try:
        sys.path.append('/opt/review-platform/backend')
        from app.services.file_based_processing import file_based_gpu_service
        print("✅ File-based processing service imported successfully")
        
        # Test with latest deck
        if decks:
            latest_deck_id = decks[0][0]
            status_result = file_based_gpu_service.get_processing_status(latest_deck_id)
            print(f"✅ Service status check for deck {latest_deck_id}:")
            print(f"   Result: {status_result}")
            
    except Exception as e:
        print(f"❌ File-based processing service error: {e}")
    
    # 5. Match result files to database entries
    print(f"\n5. RESULT FILE MATCHING")
    print("-" * 50)
    
    for result_file in result_files:
        print(f"Processing file: {result_file}")
        
        # Extract pitch deck ID from filename
        try:
            if result_file.startswith('job_'):
                parts = result_file.replace('_results.json', '').split('_')
                if len(parts) >= 2:
                    pitch_deck_id = int(parts[1])
                    
                    # Check database entry
                    cursor.execute("SELECT processing_status, ai_analysis_results FROM pitch_decks WHERE id = ?", (pitch_deck_id,))
                    result = cursor.fetchone()
                    
                    if result:
                        db_status, db_results = result
                        print(f"   Deck {pitch_deck_id}: DB status = {db_status}, Has results = {'Yes' if db_results else 'No'}")
                        
                        if db_status != 'completed' or not db_results:
                            print(f"   ⚠️  Needs updating!")
                            
                            # Read result file
                            result_path = os.path.join(results_dir, result_file)
                            with open(result_path, 'r') as f:
                                results_data = json.load(f)
                            
                            # Update database
                            cursor.execute(
                                "UPDATE pitch_decks SET processing_status = ?, ai_analysis_results = ? WHERE id = ?",
                                ('completed', json.dumps(results_data), pitch_deck_id)
                            )
                            conn.commit()
                            print(f"   ✅ Updated deck {pitch_deck_id} to completed")
                        else:
                            print(f"   ✅ Already up to date")
                    else:
                        print(f"   ❌ No database entry found for deck {pitch_deck_id}")
                        
        except Exception as e:
            print(f"   ❌ Error processing {result_file}: {e}")
        print()
    
    # 6. Final verification
    print("6. FINAL VERIFICATION")
    print("-" * 50)
    
    cursor.execute("SELECT id, file_name, processing_status FROM pitch_decks WHERE processing_status = 'completed' ORDER BY id DESC LIMIT 5")
    completed_decks = cursor.fetchall()
    
    print(f"✅ Found {len(completed_decks)} completed decks:")
    for deck_id, file_name, status in completed_decks:
        print(f"   - Deck {deck_id}: {file_name} - {status}")
    
    conn.close()
    
    print(f"\n=== DEBUGGING COMPLETE ===")
    print("If decks are now marked as 'completed', refresh your webpage!")

if __name__ == "__main__":
    debug_results_issue()