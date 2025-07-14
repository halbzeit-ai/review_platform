#!/usr/bin/env python3
"""
Test script for email language functionality
"""

import sys
from pathlib import Path

# Add the backend app to the path
sys.path.append(str(Path(__file__).parent))

from app.services.email_service import EmailService

def test_email_language():
    """Test email language functionality"""
    print("🚀 Testing email language functionality...")
    
    # Test 1: Test email service initialization
    print("\n1️⃣ Testing email service initialization...")
    try:
        email_service = EmailService()
        print("✅ Email service initialized successfully")
    except Exception as e:
        print(f"❌ Email service initialization failed: {e}")
        return
    
    # Test 2: Test verification email template generation (German)
    print("\n2️⃣ Testing German verification email template...")
    try:
        # Mock verification token
        test_token = "test_token_123"
        test_email = "test@example.com"
        
        # We'll modify the send_email method to just return the content for testing
        original_send_email = email_service.send_email
        captured_content = {}
        
        def mock_send_email(to_email, subject, html_body, text_body=None):
            captured_content['to_email'] = to_email
            captured_content['subject'] = subject
            captured_content['html_body'] = html_body
            captured_content['text_body'] = text_body
            return True
        
        email_service.send_email = mock_send_email
        
        # Test German verification email
        result = email_service.send_verification_email(test_email, test_token, "de")
        if result:
            print("✅ German verification email generated successfully")
            print(f"📧 Subject: {captured_content['subject']}")
            if "Verifizieren Sie Ihr HALBZEIT AI Konto" in captured_content['subject']:
                print("✅ German subject line confirmed")
            else:
                print("❌ German subject line not found")
            
            if "Willkommen bei HALBZEIT AI!" in captured_content['html_body']:
                print("✅ German HTML content confirmed")
            else:
                print("❌ German HTML content not found")
        else:
            print("❌ German verification email generation failed")
            
    except Exception as e:
        print(f"❌ German verification email test failed: {e}")
    
    # Test 3: Test verification email template generation (English)
    print("\n3️⃣ Testing English verification email template...")
    try:
        # Test English verification email
        result = email_service.send_verification_email(test_email, test_token, "en")
        if result:
            print("✅ English verification email generated successfully")
            print(f"📧 Subject: {captured_content['subject']}")
            if "Verify your HALBZEIT AI account" in captured_content['subject']:
                print("✅ English subject line confirmed")
            else:
                print("❌ English subject line not found")
            
            if "Welcome to HALBZEIT AI!" in captured_content['html_body']:
                print("✅ English HTML content confirmed")
            else:
                print("❌ English HTML content not found")
        else:
            print("❌ English verification email generation failed")
            
    except Exception as e:
        print(f"❌ English verification email test failed: {e}")
    
    # Test 4: Test welcome email template generation (German)
    print("\n4️⃣ Testing German welcome email template...")
    try:
        # Test German welcome email
        result = email_service.send_welcome_email(test_email, "Test Company", "de")
        if result:
            print("✅ German welcome email generated successfully")
            print(f"📧 Subject: {captured_content['subject']}")
            if "Willkommen bei HALBZEIT AI" in captured_content['subject']:
                print("✅ German welcome subject line confirmed")
            else:
                print("❌ German welcome subject line not found")
            
            if "🎉 Willkommen bei HALBZEIT AI, Test Company!" in captured_content['html_body']:
                print("✅ German welcome HTML content confirmed")
            else:
                print("❌ German welcome HTML content not found")
        else:
            print("❌ German welcome email generation failed")
            
    except Exception as e:
        print(f"❌ German welcome email test failed: {e}")
    
    # Test 5: Test welcome email template generation (English)
    print("\n5️⃣ Testing English welcome email template...")
    try:
        # Test English welcome email
        result = email_service.send_welcome_email(test_email, "Test Company", "en")
        if result:
            print("✅ English welcome email generated successfully")
            print(f"📧 Subject: {captured_content['subject']}")
            if "Welcome to HALBZEIT AI" in captured_content['subject']:
                print("✅ English welcome subject line confirmed")
            else:
                print("❌ English welcome subject line not found")
            
            if "🎉 Welcome to HALBZEIT AI, Test Company!" in captured_content['html_body']:
                print("✅ English welcome HTML content confirmed")
            else:
                print("❌ English welcome HTML content not found")
        else:
            print("❌ English welcome email generation failed")
            
    except Exception as e:
        print(f"❌ English welcome email test failed: {e}")
    
    # Restore original send_email method
    email_service.send_email = original_send_email
    
    print("\n🎉 Email language test completed!")

if __name__ == "__main__":
    test_email_language()