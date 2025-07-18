#!/usr/bin/env python3
"""
PostgreSQL Setup Verification Script
Verifies that PostgreSQL is properly configured and accessible for the review platform
"""

import psycopg2
import sys
import os
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def check_postgresql_service():
    """Check if PostgreSQL service is running"""
    print("1. Checking PostgreSQL service status...")
    
    try:
        result = os.system("systemctl is-active postgresql --quiet")
        if result == 0:
            print("   ✅ PostgreSQL service is running")
            return True
        else:
            print("   ❌ PostgreSQL service is not running")
            print("   Run: sudo systemctl start postgresql")
            return False
    except Exception as e:
        print(f"   ❌ Error checking PostgreSQL service: {e}")
        return False

def check_database_connection():
    """Test database connection with configured credentials"""
    print("\n2. Testing database connection...")
    
    # Configuration from config.py
    db_config = {
        'host': 'localhost',
        'database': 'review-platform',
        'user': 'review_user',
        'password': 'review_password',
        'port': 5432
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"   ✅ Database connection successful")
        print(f"   PostgreSQL version: {version}")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"   ❌ Database connection failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Unexpected error: {e}")
        return False

def check_database_exists():
    """Check if the review-platform database exists"""
    print("\n3. Checking if database exists...")
    
    try:
        # Connect to postgres database first
        conn = psycopg2.connect(
            host='localhost',
            database='postgres',
            user='review_user',
            password='review_password'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute("""
            SELECT EXISTS(
                SELECT datname FROM pg_catalog.pg_database 
                WHERE datname = 'review-platform'
            );
        """)
        exists = cursor.fetchone()[0]
        
        if exists:
            print("   ✅ Database 'review-platform' exists")
        else:
            print("   ❌ Database 'review-platform' does not exist")
            print("   Creating database...")
            cursor.execute("CREATE DATABASE \"review-platform\";")
            print("   ✅ Database created successfully")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking/creating database: {e}")
        return False

def check_user_permissions():
    """Check if database user has proper permissions"""
    print("\n4. Checking user permissions...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Test table creation permission
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_permissions (
                id SERIAL PRIMARY KEY,
                test_data TEXT
            );
        """)
        
        # Test insert permission
        cursor.execute("INSERT INTO test_permissions (test_data) VALUES ('test');")
        
        # Test select permission
        cursor.execute("SELECT * FROM test_permissions;")
        result = cursor.fetchall()
        
        # Clean up
        cursor.execute("DROP TABLE test_permissions;")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("   ✅ User has CREATE, INSERT, SELECT, and DROP permissions")
        return True
        
    except Exception as e:
        print(f"   ❌ Permission check failed: {e}")
        return False

def check_existing_tables():
    """Check what tables already exist in the database"""
    print("\n5. Checking existing tables...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        
        if tables:
            print(f"   Found {len(tables)} existing tables:")
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
                count = cursor.fetchone()[0]
                print(f"     - {table[0]}: {count} rows")
        else:
            print("   ❌ No tables found - database is empty")
            print("   Migration will be required")
        
        cursor.close()
        conn.close()
        return len(tables) > 0
        
    except Exception as e:
        print(f"   ❌ Error checking tables: {e}")
        return False

def main():
    """Main verification function"""
    print("PostgreSQL Setup Verification")
    print("=" * 50)
    
    checks = [
        check_postgresql_service(),
        check_database_connection(),
        check_database_exists(),
        check_user_permissions(),
        check_existing_tables()
    ]
    
    print("\n" + "=" * 50)
    print("VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"✅ All {total} checks passed! PostgreSQL is ready.")
        print("\nNext steps:")
        print("1. If tables exist, verify data integrity")
        print("2. If no tables exist, run migration scripts")
        return True
    else:
        print(f"❌ {total - passed} checks failed out of {total}")
        print("\nPlease fix the issues above before proceeding with migration.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)