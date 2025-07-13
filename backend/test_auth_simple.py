#!/usr/bin/env python3
"""
Simple test for auth module language features
"""

import sys
from pathlib import Path

# Add the backend app to the path
sys.path.append(str(Path(__file__).parent))

def test_auth_module():
    """Test that the auth module can be imported and has our new classes"""
    print("🚀 Testing auth module...")
    
    try:
        # Test imports
        from app.api.auth import LanguagePreferenceData, RegisterData
        print("✅ Language preference models imported successfully")
        
        # Test LanguagePreferenceData model
        lang_data = LanguagePreferenceData(preferred_language="de")
        print(f"✅ LanguagePreferenceData works: {lang_data.preferred_language}")
        
        # Test RegisterData model with language
        reg_data = RegisterData(
            email="test@example.com",
            password="test123",
            company_name="Test Co",
            role="startup",
            preferred_language="en"
        )
        print(f"✅ RegisterData with language works: {reg_data.preferred_language}")
        
        # Test default language
        reg_data_default = RegisterData(
            email="test2@example.com",
            password="test123",
            company_name="Test Co",
            role="startup"
        )
        print(f"✅ RegisterData default language: {reg_data_default.preferred_language}")
        
        print("\n🎉 Auth module language features working!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing auth module: {e}")
        return False

if __name__ == "__main__":
    test_auth_module()