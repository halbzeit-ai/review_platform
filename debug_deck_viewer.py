#!/usr/bin/env python3
"""
Debug script to trace deck viewer API calls and responses
"""

import requests
import json
import sys
from datetime import datetime

def test_slide_image_api():
    """Test the slide image API directly"""
    base_url = "https://halbzeit.ai/api"
    
    # Test URLs that the frontend is trying
    test_urls = [
        f"{base_url}/projects/ismaning/slide-image/LigronBio_Pitch-Deck_12-12-2024/slide_1.jpg",
        f"{base_url}/projects/ismaning/slide-image/LigronBio_Pitch-Deck_12-12-2024/slide_15.jpg",
        f"{base_url}/projects/ismaning/slide-image/LigronBio_Pitch-Deck_12-12-2024/slide_21.jpg"
    ]
    
    print("🔍 Testing Slide Image API Calls")
    print("=" * 50)
    
    for url in test_urls:
        print(f"\n📍 Testing: {url}")
        try:
            response = requests.get(url, timeout=10)
            print(f"   Status: {response.status_code}")
            print(f"   Headers: {dict(response.headers)}")
            
            if response.status_code == 404:
                print(f"   ❌ 404 Error: {response.text[:200]}")
            elif response.status_code == 403:
                print(f"   🔐 403 Forbidden: {response.text[:200]}")
            elif response.status_code == 200:
                print(f"   ✅ Success: Content-Length = {len(response.content)} bytes")
            else:
                print(f"   ⚠️  Unexpected status: {response.text[:200]}")
                
        except Exception as e:
            print(f"   💥 Exception: {e}")
    
    print("\n" + "=" * 50)

def test_visual_analysis_api():
    """Test the visual analysis API to see what paths are returned"""
    url = "https://halbzeit.ai/api/projects/ismaning/decks/148/analysis"
    
    print("🔍 Testing Visual Analysis API")
    print("=" * 50)
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Total slides: {data.get('total_slides', 'unknown')}")
            
            slides = data.get('slides', [])
            for i, slide in enumerate(slides[:3]):  # Show first 3
                print(f"Slide {i+1}:")
                print(f"  slide_image_path: {slide.get('slide_image_path', 'MISSING')}")
                print(f"  page_number: {slide.get('page_number', 'MISSING')}")
        else:
            print(f"❌ Error: {response.text[:200]}")
            
    except Exception as e:
        print(f"💥 Exception: {e}")

def monitor_backend_logs():
    """Show recent backend log entries"""
    print("🔍 Recent Backend Logs")
    print("=" * 50)
    
    import subprocess
    try:
        # Get last 20 lines of backend logs
        result = subprocess.run([
            'tail', '-20', '/mnt/CPU-GPU/logs/backend.log'
        ], capture_output=True, text=True)
        
        print(result.stdout)
        
    except Exception as e:
        print(f"💥 Exception reading logs: {e}")

if __name__ == "__main__":
    print(f"🚀 Deck Viewer Debug Script - {datetime.now()}")
    print()
    
    test_visual_analysis_api()
    print()
    test_slide_image_api() 
    print()
    monitor_backend_logs()