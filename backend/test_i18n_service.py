#!/usr/bin/env python3
"""
Test script for I18n service functionality
"""

import sys
from pathlib import Path

# Add the backend app to the path
sys.path.append(str(Path(__file__).parent))

from app.services.i18n_service import I18nService

def test_i18n_service():
    """Test I18n service functionality"""
    print("🚀 Testing I18n service functionality...")
    
    # Test 1: Service initialization
    print("\n1️⃣ Testing service initialization...")
    try:
        i18n = I18nService()
        print("✅ I18n service initialized successfully")
        print(f"📋 Supported languages: {i18n.get_supported_languages()}")
    except Exception as e:
        print(f"❌ I18n service initialization failed: {e}")
        return
    
    # Test 2: Basic translation lookup
    print("\n2️⃣ Testing basic translation lookup...")
    try:
        # Test English
        en_subject = i18n.t("emails.verification.subject", "en")
        print(f"🇬🇧 English subject: {en_subject}")
        if "Verify your HALBZEIT AI account" in en_subject:
            print("✅ English translation correct")
        else:
            print("❌ English translation incorrect")
        
        # Test German
        de_subject = i18n.t("emails.verification.subject", "de")
        print(f"🇩🇪 German subject: {de_subject}")
        if "Verifizieren Sie Ihr HALBZEIT AI Konto" in de_subject:
            print("✅ German translation correct")
        else:
            print("❌ German translation incorrect")
            
    except Exception as e:
        print(f"❌ Basic translation lookup failed: {e}")
    
    # Test 3: Variable substitution
    print("\n3️⃣ Testing variable substitution...")
    try:
        # Test with company name variable
        en_title = i18n.t("emails.welcome.title", "en", company_name="Test Company")
        print(f"🇬🇧 English title: {en_title}")
        if "Welcome to HALBZEIT AI, Test Company!" in en_title:
            print("✅ English variable substitution correct")
        else:
            print("❌ English variable substitution incorrect")
        
        de_title = i18n.t("emails.welcome.title", "de", company_name="Test Company")
        print(f"🇩🇪 German title: {de_title}")
        if "Willkommen bei HALBZEIT AI, Test Company!" in de_title:
            print("✅ German variable substitution correct")
        else:
            print("❌ German variable substitution incorrect")
            
    except Exception as e:
        print(f"❌ Variable substitution failed: {e}")
    
    # Test 4: Fallback to default language
    print("\n4️⃣ Testing fallback to default language...")
    try:
        # Test with unsupported language (should fall back to English)
        fr_subject = i18n.t("emails.verification.subject", "fr")
        print(f"🇫🇷 French (fallback) subject: {fr_subject}")
        if "Verify your HALBZEIT AI account" in fr_subject:
            print("✅ Fallback to default language works")
        else:
            print("❌ Fallback to default language failed")
            
    except Exception as e:
        print(f"❌ Fallback test failed: {e}")
    
    # Test 5: Invalid key handling
    print("\n5️⃣ Testing invalid key handling...")
    try:
        invalid_key = i18n.t("emails.nonexistent.key", "en")
        print(f"🔍 Invalid key result: {invalid_key}")
        if invalid_key == "emails.nonexistent.key":
            print("✅ Invalid key handling works (returns key as fallback)")
        else:
            print("❌ Invalid key handling failed")
            
    except Exception as e:
        print(f"❌ Invalid key test failed: {e}")
    
    # Test 6: Language support check
    print("\n6️⃣ Testing language support check...")
    try:
        if i18n.is_language_supported("en"):
            print("✅ English language support check works")
        else:
            print("❌ English language support check failed")
            
        if i18n.is_language_supported("de"):
            print("✅ German language support check works")
        else:
            print("❌ German language support check failed")
            
        if not i18n.is_language_supported("fr"):
            print("✅ French language support check works (correctly returns False)")
        else:
            print("❌ French language support check failed")
            
    except Exception as e:
        print(f"❌ Language support check failed: {e}")
    
    print("\n🎉 I18n service test completed!")

if __name__ == "__main__":
    test_i18n_service()