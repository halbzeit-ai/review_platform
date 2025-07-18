#!/usr/bin/env python3
"""
Debug Authentication Flow
Debug the exact authentication flow to find where it's failing
"""

import psycopg2
from passlib.context import CryptContext
import sys
from datetime import datetime

def debug_authentication_step_by_step():
    """Debug each step of the authentication process"""
    print("🔍 Debugging authentication flow step by step...")
    
    email = "ramin@halbzeit.ai"
    password = "test123"
    
    try:
        # Initialize password context (same as backend)
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        # Connect to database
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Step 1: Find user (same query as backend)
        print(f"\n   Step 1: Finding user with email '{email}'...")
        cursor.execute("SELECT id, email, password_hash, role, company_name, is_verified, preferred_language FROM users WHERE email = %s;", (email,))
        user = cursor.fetchone()
        
        if not user:
            print(f"   ❌ User not found in database")
            return False
        
        user_id, db_email, password_hash, role, company_name, is_verified, preferred_language = user
        print(f"   ✅ User found: ID={user_id}, Email={db_email}")
        print(f"   Role: {role}, Company: {company_name}")
        print(f"   Verified: {is_verified}, Language: {preferred_language}")
        print(f"   Password hash: {password_hash[:30]}...")
        
        # Step 2: Check if email is verified (backend check)
        print(f"\n   Step 2: Checking email verification...")
        if not is_verified:
            print(f"   ❌ Email not verified - this would cause 403 error")
            return False
        else:
            print(f"   ✅ Email is verified")
        
        # Step 3: Verify password (exact same as backend)
        print(f"\n   Step 3: Verifying password...")
        print(f"   Password to verify: '{password}'")
        print(f"   Hash from database: {password_hash}")
        
        # Test password verification
        password_valid = pwd_context.verify(password, password_hash)
        print(f"   Password verification result: {password_valid}")
        
        if not password_valid:
            print(f"   ❌ Password verification failed")
            
            # Let's test with a fresh hash
            print(f"\n   Testing with fresh hash...")
            fresh_hash = pwd_context.hash(password)
            print(f"   Fresh hash: {fresh_hash}")
            fresh_verification = pwd_context.verify(password, fresh_hash)
            print(f"   Fresh verification: {fresh_verification}")
            
            # Let's also test the stored hash format
            print(f"\n   Analyzing stored hash...")
            if password_hash.startswith('$2b$'):
                print(f"   ✅ Hash format is correct (bcrypt $2b$)")
            elif password_hash.startswith('$2a$'):
                print(f"   ✅ Hash format is correct (bcrypt $2a$)")
            else:
                print(f"   ❌ Hash format may be incorrect")
            
            return False
        else:
            print(f"   ✅ Password verification successful")
        
        # Step 4: Check what the backend would return
        print(f"\n   Step 4: Authentication would succeed...")
        print(f"   Backend would create token for user {user_id}")
        print(f"   Backend would return: role={role}, company_name={company_name}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error during authentication debug: {e}")
        return False

def check_backend_logs():
    """Check backend logs for authentication errors"""
    print("\n🔍 Checking recent backend logs...")
    
    try:
        import subprocess
        
        # Get recent logs
        result = subprocess.run(
            ["journalctl", "-u", "review-platform", "--since", "2 minutes ago", "-n", "20"],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            logs = result.stdout
            print("   Recent backend logs:")
            print("   " + "-" * 40)
            
            # Look for authentication-related logs
            for line in logs.split('\n'):
                if any(keyword in line.lower() for keyword in ['auth', 'login', 'password', 'error', 'exception']):
                    print(f"   {line}")
            
            print("   " + "-" * 40)
        else:
            print("   ❌ Could not retrieve logs")
            
    except Exception as e:
        print(f"   ❌ Error checking logs: {e}")

def test_direct_password_verification():
    """Test password verification directly"""
    print("\n🔍 Testing password verification directly...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Get the stored hash
        cursor.execute("SELECT password_hash FROM users WHERE email = %s;", ("ramin@halbzeit.ai",))
        stored_hash = cursor.fetchone()[0]
        
        print(f"   Stored hash: {stored_hash}")
        
        # Test various password combinations
        test_passwords = ["test123", "Test123", "TEST123", "123test", ""]
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        
        for test_pwd in test_passwords:
            if test_pwd:
                result = pwd_context.verify(test_pwd, stored_hash)
                print(f"   Password '{test_pwd}': {'✅ MATCH' if result else '❌ no match'}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"   ❌ Error testing passwords: {e}")

def main():
    """Main debugging function"""
    print("Authentication Flow Debug")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Debug authentication step by step
    auth_success = debug_authentication_step_by_step()
    
    # Test password verification
    test_direct_password_verification()
    
    # Check backend logs
    check_backend_logs()
    
    print("\n" + "=" * 50)
    print("AUTHENTICATION DEBUG SUMMARY")
    print("=" * 50)
    
    if auth_success:
        print("✅ Authentication logic should work!")
        print("The issue might be in the FastAPI backend code or request processing.")
    else:
        print("❌ Authentication logic has issues")
        print("The problem is in the password verification or user verification.")
    
    print("\nNext steps:")
    print("1. Check if the password hash in database matches what we expect")
    print("2. Look at backend logs for specific error messages")
    print("3. Check if FastAPI is processing the request correctly")
    
    return auth_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)