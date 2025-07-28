#!/usr/bin/env python3
"""
Inspect cached visual analysis data in detail
"""

import requests
import json

# Configuration
CPU_SERVER = "http://65.108.32.168"

def inspect_visual_cache():
    """Inspect the cached visual analysis data in detail"""
    print("=== INSPECTING CACHED VISUAL ANALYSIS ===")
    
    # Test with known deck IDs
    test_deck_ids = [62, 70, 104, 108, 129]
    
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
                return
            
            print(f"\n✅ Found cached analysis for {len(cached_analysis)} decks:")
            
            for deck_id, analysis in cached_analysis.items():
                print(f"\n{'='*60}")
                print(f"DECK {deck_id}")
                print(f"{'='*60}")
                
                # Show raw structure
                print(f"Data type: {type(analysis)}")
                if isinstance(analysis, dict):
                    print(f"Keys: {list(analysis.keys())}")
                    
                    # Check for visual_analysis_results
                    if "visual_analysis_results" in analysis:
                        results = analysis["visual_analysis_results"]
                        print(f"Visual analysis results type: {type(results)}")
                        
                        if isinstance(results, list):
                            print(f"Number of pages: {len(results)}")
                            
                            # Show each page
                            for i, result in enumerate(results):
                                if isinstance(result, dict):
                                    page_num = result.get('page_number', 'N/A')
                                    description = result.get('description', 'No description')
                                    
                                    print(f"\n  Page {page_num}:")
                                    print(f"    Description length: {len(description)} chars")
                                    print(f"    First 500 chars: {description[:500]}...")
                                    
                                    # Check for healthcare keywords
                                    healthcare_keywords = ['health', 'medical', 'patient', 'clinical', 'therapy', 'treatment', 'disease', 'diagnosis', 'care', 'physician', 'doctor', 'hospital']
                                    found_keywords = [kw for kw in healthcare_keywords if kw.lower() in description.lower()]
                                    if found_keywords:
                                        print(f"    Healthcare keywords: {found_keywords[:3]}")
                                    else:
                                        print(f"    ⚠️  No healthcare keywords found")
                                else:
                                    print(f"  Page {i}: Not a dict - {type(result)}")
                        else:
                            print(f"  ❌ visual_analysis_results is not a list: {type(results)}")
                    else:
                        print(f"  ❌ No 'visual_analysis_results' key found")
                        print(f"  Available keys: {list(analysis.keys())}")
                else:
                    print(f"❌ Analysis is not a dict: {type(analysis)}")
                    
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    print("🔍 VISUAL CACHE DETAILED INSPECTION")
    print("=" * 70)
    
    inspect_visual_cache()
    
    print("\n" + "=" * 70)
    print("🎯 WHAT TO LOOK FOR:")
    print("✅ Each deck should have visual_analysis_results with multiple pages")
    print("✅ Each page should have substantial description text (>100 chars)")
    print("✅ Healthcare keywords should be present in descriptions")
    print("❌ If any of the above is missing, visual analysis cache has issues")

if __name__ == "__main__":
    main()