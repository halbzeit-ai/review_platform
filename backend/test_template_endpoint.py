#!/usr/bin/env python3
"""
Test script for template processing endpoint
"""

import requests
import json

def test_template_endpoint():
    # Production server from the logs
    base_url = "http://65.108.32.168:8000"  # Production server
    
    # First, get a GP token by logging in
    login_response = requests.post(
        f"{base_url}/api/auth/login",
        json={
            "email": "ramin@halölölöl.ai",  # Your actual GP credentials
            "password": "1234zeedee12"  # Your actual password
        }
    )
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.status_code}")
        print(login_response.text)
        return
    
    token_data = login_response.json()
    token = token_data.get("access_token")
    
    if not token:
        print("No access token received")
        return
    
    print(f"Successfully authenticated, token: {token[:20]}...")
    
    # Now test the template processing endpoint
    test_response = requests.post(
        f"{base_url}/api/dojo/extraction-test/run-template-processing",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "experiment_id": 21,  # Use experiment 21 that was mentioned
            "template_id": 3,  # Test with a specific template ID (Digital Therapeutics)
            "generate_thumbnails": True
        }
    )
    
    print(f"Template endpoint response: {test_response.status_code}")
    print(f"Response headers: {dict(test_response.headers)}")
    print(f"Response body: {test_response.text}")
    
    if test_response.status_code == 200:
        print("✅ Endpoint is working!")
        # Parse and show some results
        try:
            result_data = test_response.json()
            processing_results = result_data.get("processing_results", [])
            print(f"✅ Successfully processed {len(processing_results)} decks")
            if processing_results:
                first_result = processing_results[0]
                print(f"First deck analysis preview: {first_result.get('template_analysis', '')[:200]}...")
        except:
            pass
    else:
        print("❌ Endpoint failed")

if __name__ == "__main__":
    test_template_endpoint()