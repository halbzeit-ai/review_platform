#!/usr/bin/env python3
"""
Test script to verify visual cache retrieval is working
"""

import requests
import json
import sys

# Configuration
CPU_SERVER = "http://65.108.32.168"
GPU_SERVER = "http://135.181.63.133:8001"

def test_visual_cache_direct():
    """Test the visual cache endpoint directly"""
    print("=== TESTING VISUAL CACHE ENDPOINT ===")
    
    # Use some deck IDs from your recent experiment
    test_deck_ids = [62, 70, 104, 108, 129]  # Adjust based on your actual IDs
    
    try:
        response = requests.post(
            f"{CPU_SERVER}/api/dojo/internal/get-cached-visual-analysis",
            json={"deck_ids": test_deck_ids},
            timeout=30
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Total Requested: {data.get('total_requested')}")
            print(f"Total Found: {data.get('total_found')}")
            
            cached_analysis = data.get("cached_analysis", {})
            
            if not cached_analysis:
                print("❌ NO CACHED ANALYSIS FOUND!")
                print("This explains why extraction produces generic results.")
                print("\nPossible causes:")
                print("1. Visual analysis was never cached")
                print("2. Progressive caching failed")
                print("3. Database query is not finding records")
                return False
            
            print(f"\n✅ Found cached analysis for {len(cached_analysis)} decks:")
            
            for deck_id, analysis in cached_analysis.items():
                print(f"\nDeck {deck_id}:")
                print(f"  Type: {type(analysis)}")
                print(f"  Keys: {list(analysis.keys()) if isinstance(analysis, dict) else 'Not a dict'}")
                
                if isinstance(analysis, dict) and "visual_analysis_results" in analysis:
                    results = analysis["visual_analysis_results"]
                    print(f"  Pages: {len(results) if isinstance(results, list) else 'Not a list'}")
                    
                    if isinstance(results, list) and results:
                        first_result = results[0]
                        print(f"  Sample keys: {list(first_result.keys()) if isinstance(first_result, dict) else 'Not a dict'}")
                        
                        if isinstance(first_result, dict):
                            desc = first_result.get("description", "No description")
                            print(f"  Sample description: {desc[:100]}...")
                else:
                    print("  ❌ Missing 'visual_analysis_results' key!")
            
            return True
            
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def main():
    print("🔍 VISUAL CACHE RETRIEVAL TEST")
    print("=" * 50)
    
    success = test_visual_cache_direct()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Visual cache retrieval is working")
        print("The issue might be in:")
        print("1. Text model not using the visual context properly")
        print("2. Prompt not emphasizing context usage enough")
        print("3. Context being ignored due to model limitations")
    else:
        print("❌ Visual cache retrieval is failing")
        print("This is why extraction produces generic results!")
        print("\nTo fix:")
        print("1. Check if visual analysis was properly cached during batch processing")
        print("2. Verify visual_analysis_cache table has data")
        print("3. Check database connectivity between services")

if __name__ == "__main__":
    main()