#!/usr/bin/env python3
"""
Test API endpoints to debug authentication and results issues
Run this on production server to test the API
"""

import requests
import json
import sqlite3
import os

def test_api_endpoints():
    """Test API endpoints to debug authentication issues"""
    
    base_url = "http://localhost:8000/api"
    
    print("=== TESTING API ENDPOINTS ===\n")
    
    # 1. Test health endpoint
    print("1. Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"   Status: {response.status_code}")
        if response.status_code != 404:
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 2. Test auth endpoints
    print("\n2. Testing authentication...")
    
    # First, let's check if we can get a token
    login_data = {
        "username": "ramin@assadollahi.de",  # Use your email
        "password": "your_password_here"     # Replace with actual password
    }
    
    print("   You need to manually test login with your credentials.")
    print("   Try: curl -X POST http://localhost:8000/api/auth/login -d '{\"username\":\"your_email\",\"password\":\"your_password\"}' -H 'Content-Type: application/json'")
    
    # 3. Check database for user and deck info
    print("\n3. Checking database...")
    
    db_path = "/opt/review-platform/backend/sql_app.db"
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get users
        cursor.execute("SELECT id, email, role FROM users ORDER BY id DESC LIMIT 3")
        users = cursor.fetchall()
        print(f"   Recent users:")
        for user_id, email, role in users:
            print(f"     User {user_id}: {email} ({role})")
        
        # Get pitch decks
        cursor.execute("SELECT id, user_id, file_name, processing_status FROM pitch_decks ORDER BY id DESC LIMIT 3")
        decks = cursor.fetchall()
        print(f"\n   Recent pitch decks:")
        for deck_id, user_id, file_name, status in decks:
            print(f"     Deck {deck_id}: {file_name} (User {user_id}) - {status}")
            
        conn.close()
    
    # 4. Test processing status endpoint without auth
    print("\n4. Testing processing status endpoint (no auth)...")
    
    try:
        response = requests.get(f"{base_url}/documents/processing-status/9", timeout=5)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # 5. Check if results files exist
    print("\n5. Checking result files...")
    
    results_dir = "/mnt/shared/results"
    if os.path.exists(results_dir):
        files = [f for f in os.listdir(results_dir) if f.endswith('_results.json')]
        print(f"   Found {len(files)} result files:")
        for f in files[:5]:  # Show first 5
            file_path = os.path.join(results_dir, f)
            size = os.path.getsize(file_path)
            print(f"     {f} ({size} bytes)")
    
    print("\n=== API TEST COMPLETE ===")
    print("\nTo fix the authentication issue:")
    print("1. Check if JWT token is being properly sent from frontend")
    print("2. Check token validation in backend")
    print("3. Check CORS settings")

if __name__ == "__main__":
    test_api_endpoints()