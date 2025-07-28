#!/usr/bin/env python3
"""
Check what templates are in the database
"""

import requests
import json

def check_templates():
    # Production server from the logs
    base_url = "http://65.108.32.168:8000"  # Production server
    
    # First, get a GP token by logging in
    login_response = requests.post(
        f"{base_url}/api/auth/login",
        json={
            "email": "ramin@halölölöl.ai",
            "password": "1234zeedee12"
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
    
    print(f"Successfully authenticated")
    
    # Get templates list
    templates_response = requests.get(
        f"{base_url}/api/healthcare-templates/templates",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
    )
    
    print(f"Templates response: {templates_response.status_code}")
    if templates_response.status_code == 200:
        templates = templates_response.json()
        print(f"Templates in database:")
        for template in templates:
            print(f"  ID: {template.get('id')}, Name: '{template.get('template_name')}', Active: {template.get('is_active')}")
    else:
        print(f"Failed to get templates: {templates_response.text}")

if __name__ == "__main__":
    check_templates()