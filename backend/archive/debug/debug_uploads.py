#!/usr/bin/env python3
"""
Debug script to check upload file paths and fix them
"""
import sqlite3
import os
import json
import sys
sys.path.append('/opt/review-platform/backend')
from app.core.config import settings

def debug_uploads():
    # Database path
    db_path = "/opt/review-platform/backend/sql_app.db"
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all recent decks
    cursor.execute("""
        SELECT id, file_name, file_path, processing_status, results_file_path, company_id, created_at
        FROM pitch_decks 
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    decks = cursor.fetchall()
    
    print(f"Debugging {len(decks)} recent decks...\n")
    
    for deck in decks:
        deck_id, file_name, file_path, processing_status, results_file_path, company_id, created_at = deck
        
        print(f"Deck {deck_id}: {file_name}")
        print(f"  Status: {processing_status}")
        print(f"  File path: {file_path}")
        print(f"  Results path: {results_file_path}")
        print(f"  Company ID: {company_id}")
        
        # Check various possible file locations
        possible_paths = []
        
        if file_path:
            # Current stored path
            possible_paths.append(os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, file_path))
            
            # Upload location
            possible_paths.append(os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "uploads", file_name))
            
            # Company-based upload location
            if company_id:
                possible_paths.append(os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "uploads", company_id, file_name))
        
        found_path = None
        for path in possible_paths:
            if os.path.exists(path):
                found_path = path
                file_size = os.path.getsize(path)
                print(f"  ✅ Found file at: {path} ({file_size} bytes)")
                break
        
        if not found_path:
            print(f"  ❌ File not found at any location")
            print(f"     Checked: {possible_paths}")
        
        # Check results file
        if results_file_path:
            if results_file_path.startswith('/'):
                results_full_path = results_file_path
            else:
                results_full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, results_file_path)
                
            if os.path.exists(results_full_path):
                print(f"  ✅ Results file exists: {results_full_path}")
            else:
                print(f"  ❌ Results file missing: {results_full_path}")
        
        print()
    
    conn.close()

if __name__ == "__main__":
    debug_uploads()