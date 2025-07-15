#!/usr/bin/env python3
"""
Fix the results endpoint to use the correct file format
This script will update the documents.py file to use the new job_X_timestamp format
"""

import os
import shutil
import re

def fix_results_endpoint():
    """Fix the results endpoint to look for job_X_timestamp files"""
    
    api_file = "/opt/review-platform/backend/app/api/documents.py"
    backup_file = f"{api_file}.backup"
    
    if not os.path.exists(api_file):
        print(f"❌ API file not found: {api_file}")
        return False
    
    # Create backup
    shutil.copy(api_file, backup_file)
    print(f"✅ Created backup: {backup_file}")
    
    # Read the file
    with open(api_file, 'r') as f:
        content = f.read()
    
    # Find the results endpoint section
    old_results_logic = """    # Get results from volume storage - use flat filename format
    flat_filename = pitch_deck.file_path.replace('/', '_').replace('.pdf', '_results.json')
    results_path = f"results/{flat_filename}"
    results = volume_storage.get_results(results_path)"""
    
    new_results_logic = """    # Get results from file-based processing using job format
    import json
    import glob
    
    # Find the result file using job format: job_{pitch_deck_id}_*_results.json
    results_dir = "/mnt/shared/results"
    pattern = f"{results_dir}/job_{pitch_deck_id}_*_results.json"
    result_files = glob.glob(pattern)
    
    if not result_files:
        raise HTTPException(status_code=404, detail="Results not found")
    
    # Use the most recent result file
    result_file = max(result_files, key=os.path.getctime)
    
    try:
        with open(result_file, 'r') as f:
            results = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading results: {str(e)}")"""
    
    # Replace the old logic with new logic
    if old_results_logic in content:
        content = content.replace(old_results_logic, new_results_logic)
        
        # Write the updated content
        with open(api_file, 'w') as f:
            f.write(content)
        
        print("✅ Updated results endpoint to use job file format")
        return True
    else:
        print("❌ Could not find the old results logic to replace")
        return False

if __name__ == "__main__":
    print("=== FIXING RESULTS ENDPOINT ===")
    success = fix_results_endpoint()
    
    if success:
        print("\n✅ Results endpoint fixed!")
        print("Restart the backend service: sudo systemctl restart review-platform")
    else:
        print("\n❌ Failed to fix results endpoint")
        print("Manual intervention required")