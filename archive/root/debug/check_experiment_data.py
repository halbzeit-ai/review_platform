#!/usr/bin/env python3
"""
Check the most recent extraction experiment data to diagnose generic results issue
"""

import requests
import json
import sys

# Configuration  
CPU_SERVER = "http://65.108.32.168"

def get_recent_experiment():
    """Get the most recent extraction experiment"""
    print("=== CHECKING RECENT EXPERIMENT DATA ===")
    
    try:
        # You'll need to get a valid auth token
        # For now, let's check if we can access the experiment data
        
        # This is the experiment ID from your screenshot
        experiment_id = "test_1753043800394"  # From the screenshot
        
        print(f"Checking experiment: {experiment_id}")
        
        # Try to get experiment details (you may need to modify this with proper auth)
        print("\n⚠️  To get experiment data, please run this on the CPU server:")
        print(f"curl -H 'Authorization: Bearer YOUR_TOKEN' {CPU_SERVER}/api/dojo/extraction-test/experiments")
        print("\nOr check the database directly:")
        print("SELECT * FROM extraction_experiments ORDER BY created_at DESC LIMIT 1;")
        
        # Check if we can at least test the visual analysis cache
        print("\n=== CHECKING VISUAL ANALYSIS CACHE ===")
        print("To check cached visual analysis, run on CPU server:")
        print("SELECT pitch_deck_id, vision_model_used, LENGTH(analysis_result_json) as json_length")
        print("FROM visual_analysis_cache ORDER BY created_at DESC LIMIT 10;")
        
        return None
        
    except Exception as e:
        print(f"Exception: {e}")
        return None

def analyze_generic_patterns():
    """Analyze the generic patterns we see in results"""
    print("\n=== ANALYZING GENERIC PATTERNS ===")
    
    # From your screenshot, all results follow this pattern:
    results_from_screenshot = [
        "It helps businesses automatically extract and organize critical information from documents.",
        "It helps businesses automatically generate and optimize marketing content for various platforms.", 
        "It helps businesses automatically extract and analyze data from documents.",
        "It helps businesses understand customer behavior and optimize experiences by analyzing visual content.",
        "It helps businesses automatically identify and categorize items within images to improve product discovery and understanding.",
        "It helps businesses understand customer behavior through automated analysis of video content.",
        "It helps businesses automatically understand and respond to customer feedback from various online sources.",
        "It helps businesses automate and optimize their inventory management through data-driven insights.",
        "It helps businesses automatically identify and categorize objects within images and videos.",
        "It helps businesses automatically generate engaging video content from existing data and templates."
    ]
    
    print("Generic patterns detected:")
    print("1. All start with 'It helps businesses automatically...'")
    print("2. All use generic business terms like 'extract', 'analyze', 'optimize'")
    print("3. None mention specific healthcare/medical context")
    print("4. Results don't reflect actual pitch deck content")
    
    # Possible causes:
    print("\n🔍 POSSIBLE CAUSES:")
    print("1. Visual analysis context not being retrieved from cache")
    print("2. Text model not using visual context in generation")  
    print("3. Prompt not emphasizing use of provided context")
    print("4. Model hallucinating generic business descriptions")
    
    print("\n🔧 DEBUGGING STEPS:")
    print("1. Run debug_extraction.py to test visual analysis cache")
    print("2. Check GPU server logs during extraction")
    print("3. Verify visual analysis cache contains actual pitch deck content")
    print("4. Test extraction with a more specific prompt")
    
    # Create a test prompt
    print("\n📝 SUGGESTED TEST PROMPT:")
    test_prompt = """Based ONLY on the visual analysis descriptions provided below, explain in one sentence what specific product or service this healthcare startup provides. Be specific about the medical/health application. If no visual context is provided, respond with "No visual context available".

Visual Analysis Context:
{visual_context}

Company offering:"""
    
    print(test_prompt)

def main():
    print("🔍 EXTRACTION RESULTS ANALYSIS")
    print("=" * 50)
    
    get_recent_experiment()
    analyze_generic_patterns()
    
    print("\n" + "=" * 50)
    print("🎯 NEXT STEPS:")
    print("=" * 50)
    print("1. Run debug_extraction.py on the CPU server with proper auth token")
    print("2. Check visual_analysis_cache table in database")
    print("3. Monitor GPU server logs during extraction")
    print("4. Test with modified prompt that emphasizes context usage")

if __name__ == "__main__":
    main()