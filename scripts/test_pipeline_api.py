#!/usr/bin/env python3
"""
Test Pipeline API for offering_extraction prompt
Verify the API endpoints are working correctly
"""

import sys
import os
sys.path.append('/opt/review-platform/backend')

from app.db.database import get_db
from sqlalchemy import text
import requests
import json

def test_database_direct():
    """Test direct database access"""
    print("🔍 Testing Direct Database Access")
    print("-" * 40)
    
    try:
        db = next(get_db())
        
        # Test the exact query used by the API
        query = text("""
        SELECT stage_name, prompt_text 
        FROM pipeline_prompts 
        WHERE is_active = TRUE 
        ORDER BY stage_name
        """)
        
        result = db.execute(query).fetchall()
        
        print(f"Found {len(result)} active prompts:")
        for row in result:
            stage_name, prompt_text = row
            print(f"  • {stage_name}: {prompt_text[:80]}{'...' if len(prompt_text) > 80 else ''}")
            
            if stage_name == "offering_extraction":
                print(f"    ✅ Found offering_extraction prompt!")
                print(f"    📝 Full prompt: {prompt_text}")
                return True
        
        print("❌ offering_extraction prompt not found")
        return False
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

def test_api_endpoints():
    """Test the API endpoints"""
    print("\n🌐 Testing API Endpoints")
    print("-" * 40)
    
    base_url = "http://localhost:8000"
    
    # Test 1: Get all prompts
    print("1. Testing GET /api/pipeline/prompts")
    try:
        response = requests.get(f"{base_url}/api/pipeline/prompts")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            prompts = data.get("prompts", {})
            print(f"   Found {len(prompts)} prompts")
            
            if "offering_extraction" in prompts:
                print("   ✅ offering_extraction found in API response")
                print(f"   📝 Prompt: {prompts['offering_extraction'][:80]}...")
            else:
                print("   ❌ offering_extraction not in API response")
                print(f"   Available prompts: {list(prompts.keys())}")
                
        elif response.status_code == 401:
            print("   ⚠️  Authentication required - need to login as GP")
            return False
        else:
            print(f"   ❌ API error: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Request error: {e}")
        return False
    
    # Test 2: Get specific prompt
    print("\n2. Testing GET /api/pipeline/prompts/offering_extraction")
    try:
        response = requests.get(f"{base_url}/api/pipeline/prompts/offering_extraction")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("   ✅ Successfully retrieved offering_extraction prompt")
            print(f"   📝 Prompt: {data.get('prompt_text', 'N/A')[:80]}...")
            return True
        elif response.status_code == 401:
            print("   ⚠️  Authentication required")
            return False
        else:
            print(f"   ❌ API error: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Request error: {e}")
        return False

def check_frontend_api_integration():
    """Check how the frontend might be calling the API"""
    print("\n🖥️  Frontend Integration Notes")
    print("-" * 40)
    print("If the API works but the frontend shows empty textarea:")
    print("1. Check browser network tab for API calls")
    print("2. Verify authentication - user must be logged in as GP")
    print("3. Check frontend API service implementation")
    print("4. Look for JavaScript console errors")
    print("5. Verify the frontend is calling the correct endpoint")

def main():
    """Main test function"""
    print("Testing Pipeline API for offering_extraction prompt")
    print("=" * 60)
    
    # Test database access
    db_works = test_database_direct()
    
    # Test API endpoints
    api_works = test_api_endpoints()
    
    # Show integration notes
    check_frontend_api_integration()
    
    print("\n" + "=" * 60)
    print("SUMMARY:")
    print(f"  Database Access: {'✅ WORKING' if db_works else '❌ FAILED'}")
    print(f"  API Endpoints: {'✅ WORKING' if api_works else '❌ FAILED / AUTH REQUIRED'}")
    
    if db_works and not api_works:
        print("\n💡 The database has the prompt, but API needs authentication.")
        print("   The frontend needs to be logged in as a GP user to access prompts.")
    elif db_works and api_works:
        print("\n🎉 Both database and API are working!")
        print("   The issue is likely in the frontend code or authentication.")
    else:
        print("\n❌ There's a problem with the database or API setup.")
    
    return db_works

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)