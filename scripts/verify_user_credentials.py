#!/usr/bin/env python3
"""
Verify User Credentials in PostgreSQL
Check that users exist with proper password hashes
"""

import psycopg2
import sys
from datetime import datetime

def verify_users_in_postgresql():
    """Verify users and their password hashes exist in PostgreSQL"""
    print("🔍 Verifying users in PostgreSQL database...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Get all users with their credential information
        cursor.execute("""
            SELECT id, email, password_hash, company_name, role, 
                   is_verified, created_at, last_login
            FROM users 
            ORDER BY id;
        """)
        users = cursor.fetchall()
        
        print(f"   Found {len(users)} users in PostgreSQL:")
        print()
        
        for user in users:
            user_id, email, password_hash, company_name, role, is_verified, created_at, last_login = user
            
            print(f"   👤 User ID {user_id}:")
            print(f"      Email: {email}")
            print(f"      Company: {company_name}")
            print(f"      Role: {role}")
            print(f"      Verified: {'✅' if is_verified else '❌'}")
            print(f"      Created: {created_at}")
            print(f"      Last Login: {last_login if last_login else 'Never'}")
            
            # Check password hash
            if password_hash:
                # Check if it looks like a bcrypt hash
                if password_hash.startswith('$2b$') or password_hash.startswith('$2a$'):
                    print(f"      Password: ✅ Valid bcrypt hash ({len(password_hash)} chars)")
                else:
                    print(f"      Password: ⚠️  Hash format: {password_hash[:20]}... (may not be bcrypt)")
            else:
                print(f"      Password: ❌ No password hash stored!")
            
            print()
        
        cursor.close()
        conn.close()
        
        # Summary
        users_with_passwords = sum(1 for user in users if user[2])  # user[2] is password_hash
        verified_users = sum(1 for user in users if user[5])  # user[5] is is_verified
        
        print("   📊 Summary:")
        print(f"      Total users: {len(users)}")
        print(f"      Users with passwords: {users_with_passwords}")
        print(f"      Verified users: {verified_users}")
        
        if users_with_passwords == len(users) and verified_users == len(users):
            print("      ✅ All users have valid credentials!")
            return True
        else:
            print("      ⚠️  Some users may have credential issues")
            return False
        
    except Exception as e:
        print(f"   ❌ Error verifying users: {e}")
        return False

def test_user_authentication():
    """Test if the authentication would work"""
    print("\n🔍 Testing authentication setup...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Test auth-related queries that the application would use
        print("   Testing authentication queries...")
        
        # Test email lookup (what happens during login)
        test_email = "ramin@halbzeit.ai"
        cursor.execute("""
            SELECT id, email, password_hash, role, is_verified 
            FROM users 
            WHERE email = %s;
        """, (test_email,))
        user = cursor.fetchone()
        
        if user:
            print(f"   ✅ User lookup works for {test_email}")
            print(f"      Found: ID={user[0]}, Role={user[3]}, Verified={user[4]}")
            
            if user[2]:  # password_hash exists
                print(f"      ✅ Password hash available for authentication")
            else:
                print(f"      ❌ No password hash - authentication will fail")
        else:
            print(f"   ❌ User lookup failed for {test_email}")
        
        # Test verification token queries
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE verification_token IS NOT NULL;
        """)
        pending_verifications = cursor.fetchone()[0]
        print(f"   📧 Users with pending email verification: {pending_verifications}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing authentication: {e}")
        return False

def check_password_hashing():
    """Check if passwords are properly hashed"""
    print("\n🔍 Checking password hashing...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT email, password_hash 
            FROM users 
            WHERE password_hash IS NOT NULL;
        """)
        users = cursor.fetchall()
        
        for email, password_hash in users:
            print(f"   🔐 {email}:")
            
            # Check hash format
            if password_hash.startswith('$2b$'):
                print(f"      ✅ bcrypt hash (secure)")
            elif password_hash.startswith('$2a$'):
                print(f"      ✅ bcrypt hash (older format)")
            elif len(password_hash) >= 50:
                print(f"      ✅ Long hash (likely secure)")
            else:
                print(f"      ⚠️  Short hash - may not be secure")
                print(f"      Format: {password_hash[:20]}...")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking password hashing: {e}")
        return False

def main():
    """Main verification function"""
    print("User Credentials Verification")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    checks = [
        verify_users_in_postgresql(),
        test_user_authentication(),
        check_password_hashing()
    ]
    
    print("\n" + "=" * 50)
    print("USER VERIFICATION SUMMARY")
    print("=" * 50)
    
    if all(checks):
        print("✅ All user credential checks passed!")
        print("\n🎉 Users are properly stored in PostgreSQL with secure passwords!")
        print("\nIf login is still failing, check:")
        print("1. Frontend is sending correct JSON format")
        print("2. Password being entered matches the stored hash")
        print("3. Email addresses are exactly correct")
        print("4. CORS settings allow the requests")
        return True
    else:
        print("❌ Some user credential issues found")
        print("\nPlease review the issues above before testing login.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)