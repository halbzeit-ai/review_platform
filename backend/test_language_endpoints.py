#!/usr/bin/env python3
"""
Test script for language preference endpoints
"""

import sys
from pathlib import Path

# Add the backend app to the path
sys.path.append(str(Path(__file__).parent))

from app.main import app
from fastapi.testclient import TestClient

def test_language_endpoints():
    """Test the new language preference endpoints"""
    client = TestClient(app)
    
    print("🚀 Testing language preference endpoints...")
    
    # Test 1: Try to access language preference without auth (should fail)
    print("\n1️⃣ Testing unauthorized access...")
    response = client.get("/auth/language-preference")
    print(f"Status: {response.status_code} (Expected: 401)")
    
    # Test 2: Check if the endpoints are properly defined
    print("\n2️⃣ Testing if endpoints exist...")
    
    # Get OpenAPI spec to check if endpoints are defined
    response = client.get("/docs")
    if response.status_code == 200:
        print("✅ FastAPI docs accessible - endpoints should be available")
    else:
        print("❌ FastAPI docs not accessible")
    
    # Test 3: Check if we can import the auth module without errors
    print("\n3️⃣ Testing auth module import...")
    try:
        from app.api.auth import router
        print("✅ Auth module imports successfully")
        
        # Check if our new routes are in the router
        routes = [route.path for route in router.routes]
        print(f"📋 Available routes: {routes}")
        
        if "/language-preference" in routes:
            print("✅ Language preference endpoints found in router")
        else:
            print("❌ Language preference endpoints not found in router")
            
    except Exception as e:
        print(f"❌ Auth module import failed: {e}")
    
    print("\n🎉 Language endpoint test completed!")

if __name__ == "__main__":
    test_language_endpoints()