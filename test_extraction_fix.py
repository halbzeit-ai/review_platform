#!/usr/bin/env python3
"""
Test the extraction fix - verify that GPU server can now retrieve cached visual analysis
"""

import requests
import json

# Configuration
CPU_SERVER = "http://65.108.32.168"
GPU_SERVER = "http://135.181.63.133:8001"

def test_fixed_extraction():
    """Test extraction with the URL fix"""
    print("=== TESTING EXTRACTION WITH URL FIX ===")
    
    # Use deck IDs we know have cached visual analysis
    test_deck_ids = [62, 70, 104]
    
    # Test extraction with phi4 model
    extraction_prompt = "your task is to explain in one single short sentence the service or product the startup provides. do not mention the name of the product or the company. please do not write any introductory sentences and do not repeat the instruction, just provide what you are asked for."
    
    print(f"Testing extraction for decks: {test_deck_ids}")
    print(f"Using text model: phi4:latest")
    
    try:
        response = requests.post(
            f"{GPU_SERVER}/api/run-offering-extraction",
            json={
                "deck_ids": test_deck_ids,
                "text_model": "phi4:latest",
                "extraction_prompt": extraction_prompt,
                "use_cached_visual": True
            },
            timeout=120
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("extraction_results", [])
            
            print(f"\n✅ SUCCESS! Got {len(results)} results")
            
            for result in results:
                deck_id = result.get("deck_id")
                visual_used = result.get("visual_analysis_used")
                extraction = result.get("offering_extraction")
                
                print(f"\nDeck {deck_id}:")
                print(f"  Visual analysis used: {visual_used}")
                print(f"  Extraction: {extraction}")
                
                # Check if still generic
                if 'helps businesses automatically' in extraction.lower():
                    print(f"  ⚠️  Still generic result")
                elif extraction == "No visual analysis available for extraction":
                    print(f"  ❌ No visual analysis available")
                else:
                    print(f"  ✅ Specific result!")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    print("🔧 TESTING EXTRACTION URL FIX")
    print("=" * 50)
    
    test_fixed_extraction()
    
    print("\n" + "=" * 50)
    print("🎯 RESULTS:")
    print("If 'Visual analysis used: True' and results are specific:")
    print("  ✅ FIX SUCCESSFUL!")
    print("If still generic or 'Visual analysis used: False':")
    print("  ❌ Additional debugging needed")

if __name__ == "__main__":
    main()