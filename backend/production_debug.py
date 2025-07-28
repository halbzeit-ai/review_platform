#!/usr/bin/env python3
"""
Production server debugging script
Run this on the production CPU server to check templates and test the endpoint
"""

import requests
import json

def debug_production():
    # Production server
    base_url = "http://localhost:8000"  # Local on production server
    
    print("=== PRODUCTION SERVER DEBUG ===")
    
    # Step 1: Login as GP
    print("\n1. Logging in as GP...")
    login_response = requests.post(
        f"{base_url}/api/auth/login",
        json={
            "email": "ramin@halölölöl.ai",
            "password": "1234zeedee12"
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(login_response.text)
        return
    
    token_data = login_response.json()
    token = token_data.get("access_token")
    print("✅ Login successful")
    
    # Step 2: Get available templates
    print("\n2. Fetching available templates...")
    templates_response = requests.get(
        f"{base_url}/api/healthcare-templates/templates",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    
    if templates_response.status_code != 200:
        print(f"❌ Templates fetch failed: {templates_response.status_code}")
        print(templates_response.text)
        return
    
    templates = templates_response.json()
    print(f"✅ Found {len(templates)} templates:")
    for template in templates:
        print(f"   ID: {template.get('id')}, Name: '{template.get('name')}', Active: {template.get('is_active')}")
    
    # Step 3: Test template processing with different template IDs
    test_template_ids = [None, 1, 2, 3, 4, 5]  # Test various IDs
    
    for template_id in test_template_ids:
        print(f"\n3. Testing template processing with template_id: {template_id}")
        
        test_response = requests.post(
            f"{base_url}/api/dojo/extraction-test/run-template-processing",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "experiment_id": 21,  # Use experiment 21
                "template_id": template_id,
                "generate_thumbnails": True
            }
        )
        
        print(f"   Response status: {test_response.status_code}")
        
        if test_response.status_code == 200:
            result_data = test_response.json()
            template_used = result_data.get("template_used", "Unknown")
            processing_results = result_data.get("processing_results", [])
            print(f"   ✅ Success! Template used: '{template_used}'")
            print(f"   ✅ Processed {len(processing_results)} decks")
            
            # Show first result preview
            if processing_results:
                first_deck_id = processing_results[0].get("deck_id")
                analysis_preview = processing_results[0].get("template_analysis", "")[:100]
                print(f"   📋 Deck {first_deck_id} analysis preview: {analysis_preview}...")
        else:
            print(f"   ❌ Failed: {test_response.text}")
        
        # Don't spam the server, test only first few
        if template_id == 3:
            break
    
    print("\n=== DEBUG COMPLETE ===")

if __name__ == "__main__":
    debug_production()