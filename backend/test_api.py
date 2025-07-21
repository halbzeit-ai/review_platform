#!/usr/bin/env python3
"""
Test API Response for Experiment 11
Check what the API endpoint is actually returning
"""

import sys
import json
import asyncio
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent))

async def test_experiment_api():
    """Test the experiment details API endpoint"""
    try:
        from app.db.database import get_db
        from app.api.dojo import get_extraction_experiment
        
        # Create a mock GP user
        class MockUser:
            def __init__(self):
                self.role = "gp"
                self.id = 1
                
        mock_user = MockUser()
        db = next(get_db())
        
        print("🚀 Testing experiment details API for experiment 11...")
        
        # Call the API endpoint directly
        result = await get_extraction_experiment(11, db, mock_user)
        
        print("📊 API Response:")
        print(f"Experiment Name: {result.get('experiment_name')}")
        print(f"Classification Enabled: {result.get('classification_enabled')}")
        print(f"Classification Completed: {result.get('classification_completed_at')}")
        print()
        
        # Check classification statistics
        if "classification_statistics" in result:
            stats = result["classification_statistics"]
            print(f"📈 Classification Statistics: {stats}")
        else:
            print("❌ No classification statistics in response")
            
        # Check classification results JSON
        if "classification_results_json" in result:
            results_json = result["classification_results_json"]
            if results_json:
                print(f"📋 Classification Results JSON present: {len(results_json)} chars")
                try:
                    parsed = json.loads(results_json)
                    print(f"Parsed keys: {list(parsed.keys()) if isinstance(parsed, dict) else type(parsed)}")
                except:
                    print("Failed to parse classification_results_json")
            else:
                print("❌ classification_results_json is None")
        else:
            print("❌ No classification_results_json in response")
            
        # Check individual results
        if "results" in result:
            results = result["results"]
            print(f"📋 Individual Results: {len(results)} entries")
            for i, res in enumerate(results[:3]):  # Show first 3
                print(f"  Result {i}: deck_id={res.get('deck_id')}, primary_sector={res.get('primary_sector', 'None')}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_experiment_api())