#!/usr/bin/env python3
"""
Debug script for Dojo Extraction Pipeline
Helps diagnose why company offering extraction produces generic results
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
CPU_SERVER = "http://65.108.32.168"
GPU_SERVER = "http://135.181.63.133:8001"

def test_cached_visual_analysis(deck_ids):
    """Test if cached visual analysis exists for sample decks"""
    print("=== TESTING CACHED VISUAL ANALYSIS ===")
    
    try:
        response = requests.post(
            f"{CPU_SERVER}/api/dojo/internal/get-cached-visual-analysis",
            json={"deck_ids": deck_ids},
            timeout=30
        )
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Total Requested: {data.get('total_requested', 0)}")
            print(f"Total Found: {data.get('total_found', 0)}")
            
            cached_analysis = data.get("cached_analysis", {})
            print(f"\nCached Analysis Available for {len(cached_analysis)} decks:")
            
            for deck_id, analysis in cached_analysis.items():
                print(f"\nDeck {deck_id}:")
                if "visual_analysis_results" in analysis:
                    results = analysis["visual_analysis_results"]
                    print(f"  - Pages: {len(results)}")
                    if results:
                        # Show first page sample
                        first_page = results[0]
                        desc = first_page.get("description", "No description")[:200]
                        print(f"  - First page sample: {desc}...")
                else:
                    print(f"  - No visual_analysis_results found")
                    print(f"  - Keys: {list(analysis.keys())}")
            
            return cached_analysis
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return {}
            
    except Exception as e:
        print(f"Exception: {e}")
        return {}

def test_extraction_with_debug(deck_ids, text_model="phi4:latest"):
    """Test offering extraction with debug info"""
    print("\n=== TESTING OFFERING EXTRACTION ===")
    
    # First get the prompt from database
    try:
        prompt_response = requests.get(f"{CPU_SERVER}/api/pipeline/prompts")
        if prompt_response.status_code == 200:
            prompts = prompt_response.json().get("prompts", {})
            extraction_prompt = prompts.get("offering_extraction", "Default prompt not found")
            print(f"Extraction Prompt: {extraction_prompt}")
        else:
            extraction_prompt = "Your task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company."
            print("Using fallback prompt")
    except:
        extraction_prompt = "Your task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company."
        print("Using fallback prompt due to error")
    
    # Test extraction on GPU server directly
    print(f"\nTesting extraction on GPU server...")
    print(f"Deck IDs: {deck_ids}")
    print(f"Text Model: {text_model}")
    
    try:
        response = requests.post(
            f"{GPU_SERVER}/api/run-offering-extraction",
            json={
                "deck_ids": deck_ids,
                "text_model": text_model,
                "extraction_prompt": extraction_prompt,
                "use_cached_visual": True
            },
            timeout=300  # 5 minute timeout for processing
        )
        
        print(f"Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            
            results = data.get("extraction_results", [])
            print(f"\nExtraction Results ({len(results)} decks):")
            
            for result in results:
                deck_id = result.get("deck_id")
                extraction = result.get("offering_extraction", "No extraction")
                visual_used = result.get("visual_analysis_used", False)
                
                print(f"\nDeck {deck_id}:")
                print(f"  Visual Analysis Used: {visual_used}")
                print(f"  Extraction: {extraction}")
                
                # Check if result looks generic
                generic_phrases = ["helps businesses", "automatically", "It helps", "provides"]
                if any(phrase in extraction for phrase in generic_phrases):
                    print(f"  ⚠️  WARNING: Result appears generic")
                else:
                    print(f"  ✅ Result appears specific")
            
            return results
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        print(f"Exception: {e}")
        return []

def get_sample_deck_info(sample_size=3):
    """Get a small sample of deck info for testing"""
    print("=== GETTING SAMPLE DECK INFO ===")
    
    try:
        # You'll need to provide a valid token here
        # For testing, you might want to hardcode some deck IDs
        print("Please provide deck IDs to test, or check recent experiment for deck IDs")
        
        # Example deck IDs from the screenshot (you can modify these)
        deck_ids = [62, 70, 104]  # Adjust based on your actual deck IDs
        print(f"Using test deck IDs: {deck_ids}")
        
        return deck_ids
        
    except Exception as e:
        print(f"Exception: {e}")
        return []

def main():
    print("🔍 DEBUG: Dojo Extraction Pipeline")
    print("=" * 50)
    print(f"CPU Server: {CPU_SERVER}")
    print(f"GPU Server: {GPU_SERVER}")
    print(f"Time: {datetime.now().isoformat()}")
    print()
    
    # Get sample deck IDs
    deck_ids = get_sample_deck_info()
    
    if not deck_ids:
        print("❌ No deck IDs available for testing")
        sys.exit(1)
    
    # Test 1: Check cached visual analysis
    cached_analysis = test_cached_visual_analysis(deck_ids)
    
    # Test 2: Test extraction
    extraction_results = test_extraction_with_debug(deck_ids)
    
    # Summary
    print("\n" + "=" * 50)
    print("🔍 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    print(f"Decks tested: {len(deck_ids)}")
    print(f"Cached visual analysis available: {len(cached_analysis)}")
    print(f"Extraction results received: {len(extraction_results)}")
    
    if len(cached_analysis) == 0:
        print("❌ ISSUE: No cached visual analysis found")
        print("   - Run visual analysis first")
        print("   - Check visual_analysis_cache table")
    
    if len(extraction_results) == 0:
        print("❌ ISSUE: No extraction results received")
        print("   - Check GPU server connectivity")
        print("   - Check text model availability")
    
    generic_count = 0
    for result in extraction_results:
        extraction = result.get("offering_extraction", "")
        generic_phrases = ["helps businesses", "automatically", "It helps", "provides"]
        if any(phrase in extraction for phrase in generic_phrases):
            generic_count += 1
    
    if generic_count > 0:
        print(f"⚠️  WARNING: {generic_count}/{len(extraction_results)} results appear generic")
        print("   - Check if visual analysis context is being used")
        print("   - Verify text model is processing visual context")
        print("   - Consider adjusting extraction prompt")
    else:
        print("✅ Results appear specific and non-generic")

if __name__ == "__main__":
    main()