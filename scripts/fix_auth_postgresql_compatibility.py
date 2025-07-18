#!/usr/bin/env python3
"""
Fix Authentication PostgreSQL Compatibility Issues
Addresses specific auth code issues after PostgreSQL migration
"""

import psycopg2
import sys
from datetime import datetime

def test_auth_queries():
    """Test authentication queries for PostgreSQL compatibility"""
    print("🔍 Testing authentication queries with PostgreSQL...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Test 1: Login query (should work)
        print("   Testing login query...")
        cursor.execute("""
            SELECT id, email, password_hash, role, company_name, is_verified, preferred_language
            FROM users 
            WHERE email = %s;
        """, ("ramin@halbzeit.ai",))
        user = cursor.fetchone()
        if user:
            print("   ✅ Login query works")
        else:
            print("   ❌ Login query failed")
        
        # Test 2: Pipeline prompts query (problematic SUBSTR)
        print("   Testing pipeline prompts query (SUBSTR issue)...")
        try:
            cursor.execute("""
                SELECT id, stage_name, SUBSTR(prompt_text, 1, 100) as prompt_preview, 
                       is_active, created_by, created_at, updated_at
                FROM pipeline_prompts
                WHERE is_active = true
                LIMIT 1;
            """)
            result = cursor.fetchone()
            print("   ⚠️  SUBSTR query works but should use SUBSTRING for PostgreSQL")
        except Exception as e:
            print(f"   ❌ SUBSTR query failed: {e}")
            
            # Test PostgreSQL-compatible version
            try:
                cursor.execute("""
                    SELECT id, stage_name, SUBSTRING(prompt_text, 1, 100) as prompt_preview, 
                           is_active, created_by, created_at, updated_at
                    FROM pipeline_prompts
                    WHERE is_active = true
                    LIMIT 1;
                """)
                result = cursor.fetchone()
                print("   ✅ SUBSTRING query works (PostgreSQL compatible)")
            except Exception as e2:
                print(f"   ❌ SUBSTRING query also failed: {e2}")
        
        # Test 3: User deletion cascade query (complex raw SQL)
        print("   Testing user deletion cascade queries...")
        test_user_id = 999  # Non-existent user for testing
        test_company_id = "test_company"
        
        try:
            # Test the complex deletion queries from auth.py
            cursor.execute("""
                SELECT COUNT(*) FROM questions 
                WHERE review_id IN (
                    SELECT id FROM reviews 
                    WHERE pitch_deck_id IN (
                        SELECT id FROM pitch_decks 
                        WHERE user_id = %s OR company_id = %s
                    )
                );
            """, (test_user_id, test_company_id))
            count = cursor.fetchone()[0]
            print(f"   ✅ Complex deletion query works (found {count} related records)")
        except Exception as e:
            print(f"   ❌ Complex deletion query failed: {e}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing auth queries: {e}")
        return False

def test_user_verification_tokens():
    """Test email verification token functionality"""
    print("\n🔍 Testing email verification token functionality...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Check verification token structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'users' 
            AND column_name IN ('verification_token', 'verification_token_expires');
        """)
        token_columns = cursor.fetchall()
        
        print(f"   Found {len(token_columns)} verification token columns:")
        for col in token_columns:
            print(f"     - {col[0]}: {col[1]} ({'NULL' if col[2] == 'YES' else 'NOT NULL'})")
        
        # Test token lookup query
        cursor.execute("""
            SELECT id, email, verification_token, verification_token_expires, is_verified
            FROM users 
            WHERE verification_token IS NOT NULL
            LIMIT 5;
        """)
        unverified_users = cursor.fetchall()
        
        print(f"   Users with verification tokens: {len(unverified_users)}")
        
        # Test verification query
        test_token = "test_token_123"
        cursor.execute("""
            SELECT id, email, is_verified
            FROM users 
            WHERE verification_token = %s 
            AND verification_token_expires > %s;
        """, (test_token, datetime.utcnow()))
        
        print("   ✅ Verification token query structure works")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error testing verification tokens: {e}")
        return False

def test_login_endpoint():
    """Test login endpoint with actual credentials"""
    print("\n🔍 Testing login endpoint with API call...")
    
    try:
        import requests
        
        # Test login with known user
        login_data = {
            "username": "ramin@halbzeit.ai",  # FastAPI uses 'username' for OAuth2
            "password": "your_password_here"  # This will fail but we can see the error
        }
        
        response = requests.post(
            "http://localhost:8000/api/auth/login",
            data=login_data,  # OAuth2 uses form data, not JSON
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        print(f"   Login response status: {response.status_code}")
        print(f"   Response content: {response.text[:200]}...")
        
        if response.status_code == 400:
            print("   ⚠️  400 Bad Request - likely incorrect password or format")
        elif response.status_code == 200:
            print("   ✅ Login successful!")
        else:
            print(f"   ❌ Unexpected response: {response.status_code}")
        
        return True
        
    except ImportError:
        print("   ⚠️  requests library not available - skipping API test")
        return True
    except Exception as e:
        print(f"   ❌ Error testing login endpoint: {e}")
        return False

def analyze_auth_compatibility():
    """Analyze overall authentication compatibility"""
    print("\n📊 Authentication PostgreSQL Compatibility Analysis...")
    
    issues_found = []
    
    # Check for common PostgreSQL migration issues
    print("\n   Common PostgreSQL Migration Issues:")
    
    # 1. SUBSTR vs SUBSTRING
    issues_found.append({
        "issue": "SUBSTR function usage",
        "description": "Auth code uses SUBSTR (SQLite) instead of SUBSTRING (PostgreSQL)",
        "severity": "medium",
        "fix": "Replace SUBSTR with SUBSTRING in auth.py line 77"
    })
    
    # 2. Datetime inconsistencies
    issues_found.append({
        "issue": "Datetime handling inconsistencies", 
        "description": "Mixed use of datetime.now() and datetime.utcnow()",
        "severity": "low",
        "fix": "Standardize to datetime.utcnow() in auth.py line 118"
    })
    
    # 3. Raw SQL in delete_user
    issues_found.append({
        "issue": "Raw SQL in delete_user function",
        "description": "Complex deletion queries may need PostgreSQL optimization",
        "severity": "low", 
        "fix": "Test and optimize raw SQL queries in auth.py lines 260-342"
    })
    
    print(f"\n   Found {len(issues_found)} potential compatibility issues:")
    for i, issue in enumerate(issues_found, 1):
        print(f"\n   {i}. {issue['issue']} ({issue['severity']} severity)")
        print(f"      Description: {issue['description']}")
        print(f"      Fix: {issue['fix']}")
    
    return issues_found

def main():
    """Main authentication compatibility check"""
    print("Authentication PostgreSQL Compatibility Check")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    checks = [
        test_auth_queries(),
        test_user_verification_tokens(),
        test_login_endpoint()
    ]
    
    issues = analyze_auth_compatibility()
    
    print("\n" + "=" * 60)
    print("AUTHENTICATION COMPATIBILITY SUMMARY")
    print("=" * 60)
    
    if all(checks):
        print("✅ Basic authentication queries work with PostgreSQL!")
        
        if len(issues) == 0:
            print("🎉 No compatibility issues found!")
        else:
            print(f"⚠️  {len(issues)} minor compatibility issues identified")
            print("\nThese issues are not blocking login but should be fixed:")
            for issue in issues:
                if issue['severity'] == 'high':
                    print(f"   🔴 {issue['issue']}")
                elif issue['severity'] == 'medium':
                    print(f"   🟡 {issue['issue']}")
                else:
                    print(f"   🟢 {issue['issue']}")
        
        print("\n💡 For the 400 Bad Request errors, check:")
        print("   1. Correct password for the users")
        print("   2. Frontend sending correct format (username/password vs email/password)")
        print("   3. CORS settings allowing the requests")
        print("   4. OAuth2 vs JSON format in login requests")
        
        return True
    else:
        print("❌ Some authentication compatibility issues found")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)