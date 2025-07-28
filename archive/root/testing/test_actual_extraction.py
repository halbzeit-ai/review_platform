#!/usr/bin/env python3
"""
Test extraction with the ACTUAL deck IDs from the experiment
"""

import requests
import json
import sys

# Configuration
CPU_SERVER = "http://65.108.32.168"
GPU_SERVER = "http://135.181.63.133:8001"

def get_experiment_deck_ids():
    """Get the actual deck IDs from the recent experiment"""
    # From your screenshot, the experiment shows 10 decks
    # These are likely the deck IDs from your sample
    # You can get the exact IDs by checking the recent experiment
    
    print("Please provide the 10 deck IDs from your recent extraction test.")
    print("You can get them from the experiment details or run:")
    print("SELECT pitch_deck_ids FROM extraction_experiments ORDER BY created_at DESC LIMIT 1;")
    
    # For now, let's test with the ones we know exist
    return [62, 70, 104, 108, 129]  # We know these 5 have cache

def test_visual_context_formatting(deck_ids):
    """Test how visual context gets formatted for the text model"""
    print("=== TESTING VISUAL CONTEXT FORMATTING ===")
    
    try:
        response = requests.post(
            f"{CPU_SERVER}/api/dojo/internal/get-cached-visual-analysis",
            json={"deck_ids": deck_ids},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            cached_analysis = data.get("cached_analysis", {})
            
            for deck_id, visual_data in cached_analysis.items():
                print(f"\nDeck {deck_id} - Visual Context Formatting:")
                
                if visual_data.get("visual_analysis_results"):
                    results = visual_data["visual_analysis_results"]
                    
                    # This is exactly how the GPU formats it
                    visual_descriptions = []
                    for result in results:
                        page_desc = f"Page {result.get('page_number', 'N/A')}: {result.get('description', 'No description')}"
                        visual_descriptions.append(page_desc)
                    
                    visual_context = "\n".join(visual_descriptions)
                    
                    print(f"  Pages: {len(visual_descriptions)}")
                    print(f"  Context length: {len(visual_context)} chars")
                    print(f"  First 200 chars: {visual_context[:200]}...")
                    
                    # Check if this looks like real content
                    healthcare_keywords = ['health', 'medical', 'patient', 'clinical', 'therapy', 'treatment', 'disease', 'diagnosis', 'care', 'physician', 'doctor', 'hospital']
                    found_keywords = [kw for kw in healthcare_keywords if kw.lower() in visual_context.lower()]
                    
                    print(f"  Healthcare keywords found: {found_keywords[:5]}")
                    
                    if not found_keywords:
                        print("  ⚠️  WARNING: No healthcare keywords found in visual context!")
                        print("     This might explain generic business results.")
                else:
                    print(f"  ❌ No visual_analysis_results found")
            
            return True
        else:
            print(f"❌ Error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_single_extraction(deck_id, text_model="phi4:latest"):
    """Test extraction for a single deck with full debugging"""
    print(f"\n=== TESTING SINGLE DECK EXTRACTION (ID: {deck_id}) ===")
    
    # Get the prompt
    extraction_prompt = "your task is to explain in one single short sentence the service or product the startup provides. do not mention the name of the product or the company. please do not write any introductory sentences and do not repeat the instruction, just provide what you are asked for."
    
    print(f"Using text model: {text_model}")
    print(f"Extraction prompt: {extraction_prompt}")
    
    try:
        response = requests.post(
            f"{GPU_SERVER}/api/run-offering-extraction",
            json={
                "deck_ids": [deck_id],
                "text_model": text_model,
                "extraction_prompt": extraction_prompt,
                "use_cached_visual": True
            },
            timeout=120
        )
        
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            results = data.get("extraction_results", [])
            
            if results:
                result = results[0]
                print(f"Visual analysis used: {result.get('visual_analysis_used')}")
                print(f"Extraction result: {result.get('offering_extraction')}")
                
                # Check if generic
                extraction = result.get('offering_extraction', '')
                if 'helps businesses automatically' in extraction.lower():
                    print("❌ GENERIC RESULT DETECTED!")
                    print("The text model is ignoring the visual context.")
                else:
                    print("✅ Result appears specific")
            else:
                print("❌ No results returned")
        else:
            print(f"❌ Error: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def main():
    print("🔍 ACTUAL EXTRACTION PIPELINE TEST")
    print("=" * 60)
    
    deck_ids = get_experiment_deck_ids()
    
    # Test visual context formatting
    test_visual_context_formatting(deck_ids)
    
    # Test single extraction with debugging
    if deck_ids:
        test_single_extraction(deck_ids[0])  # Test first deck
    
    print("\n" + "=" * 60)
    print("🎯 CONCLUSIONS:")
    print("1. If visual context has healthcare keywords → Text model issue")
    print("2. If no healthcare keywords → Visual analysis issue")
    print("3. If generic result despite good context → Prompt engineering issue")

if __name__ == "__main__":
    main()