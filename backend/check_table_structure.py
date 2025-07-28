#!/usr/bin/env python3
"""
Check table structure on production server
Run this on the production CPU server
"""

import requests
import json

def check_table_structure():
    # Production server
    base_url = "http://localhost:8000"  # Local on production server
    
    print("=== TABLE STRUCTURE CHECK ===")
    
    # Login as GP
    login_response = requests.post(
        f"{base_url}/api/auth/login",
        json={
            "email": "ramin@halölölöl.ai",
            "password": "1234zeedee12"
        }
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        return
    
    token_data = login_response.json()
    token = token_data.get("access_token")
    
    # Test a direct template lookup to see what's actually returned
    print("\n1. Testing direct template lookup with ID 1...")
    
    test_response = requests.post(
        f"{base_url}/api/dojo/extraction-test/run-template-processing",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "experiment_id": 21,
            "template_id": 1,  # Test with ID 1
            "generate_thumbnails": False  # Disable thumbnails for faster test
        }
    )
    
    print(f"Response status: {test_response.status_code}")
    
    if test_response.status_code == 404:
        print("❌ Template not found - confirms table/column issue")
        print(f"Response: {test_response.text}")
    elif test_response.status_code == 200:
        result_data = test_response.json()
        template_used = result_data.get("template_used", "Unknown")
        print(f"✅ Template lookup worked! Template used: '{template_used}'")
    else:
        print(f"❌ Other error: {test_response.text}")
    
    print("\n2. Testing with template_id = None (default lookup)...")
    
    test_response2 = requests.post(
        f"{base_url}/api/dojo/extraction-test/run-template-processing",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "experiment_id": 21,
            "template_id": None,  # Test default lookup
            "generate_thumbnails": False
        }
    )
    
    print(f"Response status: {test_response2.status_code}")
    
    if test_response2.status_code == 200:
        result_data = test_response2.json()
        template_used = result_data.get("template_used", "Unknown")
        print(f"✅ Default template lookup worked! Template used: '{template_used}'")
    else:
        print(f"❌ Error: {test_response2.text}")

if __name__ == "__main__":
    check_table_structure()