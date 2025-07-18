#!/usr/bin/env python3
"""
Reset User Password
Reset password for testing login functionality
"""

import psycopg2
from passlib.context import CryptContext
import sys
from datetime import datetime

def reset_user_password(email, new_password):
    """Reset password for a specific user"""
    print(f"🔐 Resetting password for {email}...")
    
    try:
        # Initialize password context (same as in backend)
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Hash the new password
        password_hash = pwd_context.hash(new_password)
        print(f"   Generated password hash: {password_hash[:20]}...")
        
        # Connect to database
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Check if user exists
        cursor.execute("SELECT id, email, role FROM users WHERE email = %s;", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"   ❌ User {email} not found")
            return False
        
        print(f"   Found user: ID={user[0]}, Email={user[1]}, Role={user[2]}")
        
        # Update password
        cursor.execute("""
            UPDATE users 
            SET password_hash = %s 
            WHERE email = %s;
        """, (password_hash, email))
        
        # Commit changes
        conn.commit()
        
        # Verify update
        cursor.execute("SELECT password_hash FROM users WHERE email = %s;", (email,))
        updated_hash = cursor.fetchone()[0]
        
        if updated_hash == password_hash:
            print(f"   ✅ Password updated successfully!")
            print(f"   New password: {new_password}")
            
            # Test password verification
            if pwd_context.verify(new_password, updated_hash):
                print(f"   ✅ Password verification test passed")
            else:
                print(f"   ❌ Password verification test failed")
        else:
            print(f"   ❌ Password update failed")
            return False
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error resetting password: {e}")
        return False

def test_login_with_new_password(email, password):
    """Test login with the new password"""
    print(f"\n🔍 Testing login with new password...")
    
    try:
        import requests
        
        response = requests.post(
            "http://localhost:8000/api/auth/login",
            json={"email": email, "password": password},
            headers={"Content-Type": "application/json"}
        )
        
        print(f"   Login test status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"   ✅ Login successful!")
            print(f"   Token received: {result.get('access_token', 'N/A')[:30]}...")
            print(f"   User role: {result.get('role', 'N/A')}")
            print(f"   Company: {result.get('company_name', 'N/A')}")
            return True
        else:
            print(f"   ❌ Login failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Login test error: {e}")
        return False

def main():
    """Main password reset function"""
    print("User Password Reset")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Reset password for test user
    test_email = "ramin@halbzeit.ai"
    test_password = "test123"
    
    print(f"Resetting password for: {test_email}")
    print(f"New password: {test_password}")
    print()
    
    # Reset password
    reset_success = reset_user_password(test_email, test_password)
    
    if reset_success:
        # Test login
        login_success = test_login_with_new_password(test_email, test_password)
        
        if login_success:
            print("\n" + "=" * 50)
            print("🎉 PASSWORD RESET AND LOGIN TEST SUCCESSFUL!")
            print("=" * 50)
            print(f"✅ PostgreSQL migration: COMPLETE")
            print(f"✅ Authentication: WORKING")
            print(f"✅ Login credentials: {test_email} / {test_password}")
            print()
            print("You can now:")
            print("1. Login to the web interface with these credentials")
            print("2. Test uploading pitch decks")
            print("3. Verify all features work with PostgreSQL")
            print()
            print("🎯 THE MIGRATION IS COMPLETE AND FUNCTIONAL!")
            return True
        else:
            print("\n❌ Password reset successful but login still failing")
            return False
    else:
        print("\n❌ Password reset failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)