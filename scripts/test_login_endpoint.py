#!/usr/bin/env python3
"""
Test Login Endpoint with Correct Format
Test the actual login endpoint with proper JSON format
"""

import requests
import json
import sys
from datetime import datetime

def test_login_api():
    """Test the login API endpoint with correct format"""
    print("🔍 Testing login API endpoint...")
    
    # Test different possible formats
    test_cases = [
        {
            "name": "JSON format (what frontend sends)",
            "url": "http://localhost:8000/api/auth/login",
            "data": {"email": "ramin@halbzeit.ai", "password": "test123"},
            "method": "json"
        },
        {
            "name": "Form data format",
            "url": "http://localhost:8000/api/auth/login", 
            "data": {"email": "ramin@halbzeit.ai", "password": "test123"},
            "method": "form"
        },
        {
            "name": "OAuth2 format",
            "url": "http://localhost:8000/api/auth/login",
            "data": {"username": "ramin@halbzeit.ai", "password": "test123"},
            "method": "form"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n   Testing: {test_case['name']}")
        
        try:
            if test_case['method'] == 'json':
                response = requests.post(
                    test_case['url'],
                    json=test_case['data'],
                    headers={"Content-Type": "application/json"}
                )
            else:
                response = requests.post(
                    test_case['url'],
                    data=test_case['data'],
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Login successful!")
                try:
                    result = response.json()
                    print(f"   Token received: {result.get('access_token', 'N/A')[:20]}...")
                except:
                    print("   Response not JSON")
            elif response.status_code == 400:
                print("   ❌ 400 Bad Request - Invalid credentials")
                print(f"   Error: {response.text}")
            elif response.status_code == 403:
                print("   ❌ 403 Forbidden - Email not verified")
                print(f"   Error: {response.text}")
            elif response.status_code == 422:
                print("   ❌ 422 Validation Error - Wrong format")
                print(f"   Error: {response.text[:200]}...")
            else:
                print(f"   ❌ Unexpected status: {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                
        except requests.exceptions.ConnectionError:
            print("   ❌ Connection failed - Is the server running?")
        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_server_status():
    """Test if the server is running and accessible"""
    print("🔍 Testing server status...")
    
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        print(f"   Server status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return True
    except requests.exceptions.ConnectionError:
        print("   ❌ Server not accessible on localhost:8000")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def test_auth_endpoints():
    """Test auth endpoints availability"""
    print("\n🔍 Testing auth endpoints...")
    
    endpoints = [
        "http://localhost:8000/api/auth/login",
        "http://localhost:8000/api/auth/register",
        "http://localhost:8000/api/auth/users"
    ]
    
    for endpoint in endpoints:
        try:
            # Use OPTIONS to check if endpoint exists
            response = requests.options(endpoint, timeout=5)
            print(f"   {endpoint.split('/')[-1]}: {response.status_code} (available)")
        except Exception as e:
            print(f"   {endpoint.split('/')[-1]}: Error - {e}")

def check_cors_headers():
    """Check CORS headers that might be blocking frontend requests"""
    print("\n🔍 Checking CORS headers...")
    
    try:
        response = requests.options(
            "http://localhost:8000/api/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        
        print(f"   CORS preflight status: {response.status_code}")
        
        cors_headers = {
            "Access-Control-Allow-Origin": response.headers.get("Access-Control-Allow-Origin"),
            "Access-Control-Allow-Methods": response.headers.get("Access-Control-Allow-Methods"),
            "Access-Control-Allow-Headers": response.headers.get("Access-Control-Allow-Headers"),
        }
        
        for header, value in cors_headers.items():
            if value:
                print(f"   {header}: {value}")
            else:
                print(f"   {header}: Not set")
        
    except Exception as e:
        print(f"   ❌ CORS check failed: {e}")

def main():
    """Main testing function"""
    print("Login Endpoint Testing")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test server availability
    if not test_server_status():
        print("❌ Server not accessible - check if it's running on port 8000")
        return False
    
    # Test auth endpoints
    test_auth_endpoints()
    
    # Test CORS
    check_cors_headers()
    
    # Test login with different formats
    test_login_api()
    
    print("\n" + "=" * 50)
    print("LOGIN TESTING SUMMARY")
    print("=" * 50)
    print("💡 If you see 400 Bad Request errors, the issue is likely:")
    print("   1. Incorrect password for the test user")
    print("   2. User account locked or needs verification")
    print("   3. Database connection issues")
    print()
    print("💡 If you see 422 Validation errors, the issue is:")
    print("   1. Frontend sending data in wrong format")
    print("   2. API endpoint expecting different structure")
    print()
    print("💡 To fix login issues:")
    print("   1. Check what password is stored for ramin@halbzeit.ai")
    print("   2. Try with a known good password")
    print("   3. Check frontend network tab for actual request format")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)