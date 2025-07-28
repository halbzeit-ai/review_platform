#!/usr/bin/env python3
"""
Test visual cache retrieval from GPU server side to see what data GPU receives
"""

import requests
import json
import os

# Configuration (from GPU server perspective)
PRODUCTION_SERVER = os.getenv("PRODUCTION_SERVER_URL", "http://65.108.32.168")

def test_gpu_cache_retrieval():
    """Test cache retrieval exactly as the GPU server does it"""
    print("=== TESTING CACHE RETRIEVAL FROM GPU SIDE ===")
    
    # Use the same deck IDs
    deck_ids = [62, 70, 104, 108, 129]
    
    print(f"Testing with deck IDs: {deck_ids}")
    print(f"Production server URL: {PRODUCTION_SERVER}")
    
    try:
        # This is exactly what the GPU server does
        response = requests.post(
            f"{PRODUCTION_SERVER}/api/dojo/internal/get-cached-visual-analysis",
            json={"deck_ids": deck_ids},
            timeout=30
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Response success flag: {data.get('success')}")
            
            if data.get("success"):
                cached_data = data.get("cached_analysis", {})
                print(f"Number of cached decks received: {len(cached_data)}")
                
                # Process exactly like GPU server does
                for deck_id in deck_ids:
                    print(f"\n{'='*50}")
                    print(f"PROCESSING DECK {deck_id} (GPU server logic)")
                    print(f"{'='*50}")
                    
                    if str(deck_id) in cached_data:
                        visual_data = cached_data[str(deck_id)]
                        print(f"✅ Deck {deck_id} found in cached data")
                        
                        if visual_data.get("visual_analysis_results"):
                            print(f"✅ visual_analysis_results key exists")
                            
                            # This is the GPU server's formatting logic
                            visual_descriptions = []
                            for result in visual_data["visual_analysis_results"]:
                                page_desc = f"Page {result.get('page_number', 'N/A')}: {result.get('description', 'No description')}"
                                visual_descriptions.append(page_desc)
                            
                            visual_context = "\n".join(visual_descriptions)
                            visual_used = True
                            
                            print(f"✅ Successfully formatted visual context")
                            print(f"   Pages processed: {len(visual_descriptions)}")
                            print(f"   Total context length: {len(visual_context)} characters")
                            print(f"   Visual used flag: {visual_used}")
                            print(f"   First 500 chars of context:")
                            print(f"   {visual_context[:500]}...")
                            
                            # Check for healthcare keywords
                            healthcare_keywords = ['health', 'medical', 'patient', 'clinical', 'therapy', 'treatment', 'disease', 'diagnosis', 'care', 'physician', 'doctor', 'hospital']
                            found_keywords = [kw for kw in healthcare_keywords if kw.lower() in visual_context.lower()]
                            print(f"   Healthcare keywords found: {found_keywords[:5]}")
                            
                        else:
                            print(f"❌ No visual_analysis_results in visual_data")
                            print(f"   Available keys: {list(visual_data.keys()) if isinstance(visual_data, dict) else 'Not a dict'}")
                    else:
                        print(f"❌ Deck {deck_id} NOT found in cached_analysis")
                        print(f"   Available deck IDs: {list(cached_data.keys())}")
                
                return cached_data
            else:
                print(f"❌ API returned success=False")
                print(f"Error: {data.get('error', 'Unknown error')}")
                return {}
        else:
            print(f"❌ HTTP error: {response.status_code}")
            print(f"Response text: {response.text}")
            return {}
            
    except Exception as e:
        print(f"❌ Exception during cache retrieval: {e}")
        return {}

def test_key_types_matching():
    """Test if deck ID types match between request and response"""
    print(f"\n{'='*60}")
    print("TESTING KEY TYPE MATCHING")
    print(f"{'='*60}")
    
    # Test different key type scenarios
    test_cases = [
        [62, 70, 104],  # int keys
        ["62", "70", "104"],  # string keys
    ]
    
    for i, deck_ids in enumerate(test_cases):
        print(f"\nTest case {i+1}: {type(deck_ids[0])} keys - {deck_ids}")
        
        try:
            response = requests.post(
                f"{PRODUCTION_SERVER}/api/dojo/internal/get-cached-visual-analysis",
                json={"deck_ids": deck_ids},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    cached_data = data.get("cached_analysis", {})
                    print(f"  Response key types: {[type(k) for k in cached_data.keys()]}")
                    print(f"  Found {len(cached_data)} results")
                    
                    # Check if deck_ids match
                    for deck_id in deck_ids:
                        if str(deck_id) in cached_data:
                            print(f"  ✅ {deck_id} ({type(deck_id)}) found")
                        else:
                            print(f"  ❌ {deck_id} ({type(deck_id)}) NOT found")
                else:
                    print(f"  ❌ API error: {data.get('error')}")
            else:
                print(f"  ❌ HTTP error: {response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")

def main():
    print("🔍 GPU SIDE CACHE RETRIEVAL TEST")
    print("=" * 70)
    
    cached_data = test_gpu_cache_retrieval()
    test_key_types_matching()
    
    print("\n" + "=" * 70)
    print("🎯 ANALYSIS:")
    if cached_data:
        print("✅ GPU server CAN retrieve cached visual analysis")
        print("🔍 If extraction still fails, issue is likely in:")
        print("   1. Key type mismatch (int vs string)")
        print("   2. Data structure differences")
        print("   3. Processing logic after retrieval")
    else:
        print("❌ GPU server CANNOT retrieve cached visual analysis")
        print("🔍 Issues to check:")
        print("   1. Network connectivity between servers")
        print("   2. API endpoint availability")
        print("   3. Authentication/authorization")

if __name__ == "__main__":
    main()