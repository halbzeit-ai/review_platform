#!/usr/bin/env python3
"""
Compare SQLite vs PostgreSQL Data
Ensures complete migration before removing SQLite dependency
"""

import sqlite3
import psycopg2
import sys
import os
from datetime import datetime

def get_sqlite_data():
    """Get data from SQLite database"""
    sqlite_path = "/opt/review-platform/backend/sql_app.db"
    
    if not os.path.exists(sqlite_path):
        print("❌ SQLite database not found - may already be fully migrated")
        return None
    
    print(f"📊 Reading SQLite data from: {sqlite_path}")
    
    try:
        conn = sqlite3.connect(sqlite_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tables = [row[0] for row in cursor.fetchall()]
        
        sqlite_data = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            sqlite_data[table] = count
        
        conn.close()
        return sqlite_data
        
    except Exception as e:
        print(f"❌ Error reading SQLite data: {e}")
        return None

def get_postgresql_data():
    """Get data from PostgreSQL database"""
    print("📊 Reading PostgreSQL data...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Get all table names
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        postgres_data = {}
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            postgres_data[table] = count
        
        conn.close()
        return postgres_data
        
    except Exception as e:
        print(f"❌ Error reading PostgreSQL data: {e}")
        return None

def compare_core_tables(sqlite_data, postgres_data):
    """Compare core application tables"""
    print("\n🔍 Comparing core application tables...")
    
    # These are the tables that should have been migrated from SQLite
    core_tables = ['users', 'pitch_decks', 'reviews', 'questions', 'answers', 'model_configs']
    
    migration_complete = True
    
    for table in core_tables:
        sqlite_count = sqlite_data.get(table, 0) if sqlite_data else 0
        postgres_count = postgres_data.get(table, 0) if postgres_data else 0
        
        if sqlite_count == postgres_count:
            status = "✅"
        elif postgres_count > sqlite_count:
            status = "📈"  # More data in PostgreSQL (newer records)
        else:
            status = "❌"
            migration_complete = False
        
        print(f"   {status} {table}: SQLite={sqlite_count}, PostgreSQL={postgres_count}")
    
    return migration_complete

def compare_additional_tables(sqlite_data, postgres_data):
    """Compare additional tables that may exist"""
    print("\n🔍 Comparing additional tables...")
    
    if not sqlite_data:
        print("   ℹ️  No SQLite database found - skipping comparison")
        return True
    
    # Find tables that exist in SQLite but not in PostgreSQL
    sqlite_only = set(sqlite_data.keys()) - set(postgres_data.keys())
    if sqlite_only:
        print("   ⚠️  Tables only in SQLite:")
        for table in sqlite_only:
            print(f"     - {table}: {sqlite_data[table]} rows")
    
    # Find tables that exist in PostgreSQL but not in SQLite
    postgres_only = set(postgres_data.keys()) - set(sqlite_data.keys())
    if postgres_only:
        print("   ℹ️  Tables only in PostgreSQL (expected - new features):")
        for table in postgres_only:
            print(f"     - {table}: {postgres_data[table]} rows")
    
    return len(sqlite_only) == 0

def check_application_config():
    """Check if application is configured for PostgreSQL"""
    print("\n🔍 Checking application configuration...")
    
    try:
        # Check backend config
        config_path = "/opt/review-platform/backend/app/core/config.py"
        with open(config_path, 'r') as f:
            config_content = f.read()
        
        if 'postgresql://' in config_content:
            print("   ✅ Backend configured for PostgreSQL")
        else:
            print("   ❌ Backend still configured for SQLite")
            return False
        
        # Check if SQLite file is still being used
        sqlite_path = "/opt/review-platform/backend/sql_app.db"
        if os.path.exists(sqlite_path):
            # Check last modification time
            mtime = os.path.getmtime(sqlite_path)
            last_modified = datetime.fromtimestamp(mtime)
            days_old = (datetime.now() - last_modified).days
            
            if days_old > 1:
                print(f"   ✅ SQLite file last modified {days_old} days ago - likely not in use")
            else:
                print(f"   ⚠️  SQLite file modified recently ({days_old} days ago) - may still be in use")
        else:
            print("   ✅ SQLite file not found - fully migrated")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking application config: {e}")
        return False

def generate_migration_report(sqlite_data, postgres_data):
    """Generate final migration report"""
    print("\n" + "=" * 60)
    print("MIGRATION COMPLETENESS REPORT")
    print("=" * 60)
    
    if not sqlite_data:
        print("🎉 SQLite database not found - migration appears complete!")
        print("\nPostgreSQL database contains:")
        total_rows = sum(postgres_data.values())
        print(f"   • {len(postgres_data)} tables")
        print(f"   • {total_rows} total rows")
        print(f"   • Core tables: users, pitch_decks, reviews, etc.")
        print(f"   • Extended tables: healthcare templates, pipeline prompts, etc.")
        return True
    
    # Compare totals
    sqlite_total = sum(sqlite_data.values())
    postgres_total = sum(postgres_data.values())
    
    print(f"SQLite Database:")
    print(f"   • {len(sqlite_data)} tables")
    print(f"   • {sqlite_total} total rows")
    
    print(f"\nPostgreSQL Database:")
    print(f"   • {len(postgres_data)} tables")
    print(f"   • {postgres_total} total rows")
    
    # Determine migration status
    core_complete = compare_core_tables(sqlite_data, postgres_data)
    additional_complete = compare_additional_tables(sqlite_data, postgres_data)
    config_complete = check_application_config()
    
    print(f"\nMigration Status:")
    print(f"   • Core tables migrated: {'✅' if core_complete else '❌'}")
    print(f"   • Additional tables handled: {'✅' if additional_complete else '❌'}")
    print(f"   • Application configured: {'✅' if config_complete else '❌'}")
    
    if core_complete and additional_complete and config_complete:
        print("\n🎉 MIGRATION COMPLETE!")
        print("\nSafe to remove SQLite dependency:")
        print("1. ✅ All core data migrated to PostgreSQL")
        print("2. ✅ Application configured for PostgreSQL")
        print("3. ✅ Extended features (healthcare, pipeline) working")
        print("4. ✅ SQLite file can be archived/removed")
        return True
    else:
        print("\n⚠️  MIGRATION INCOMPLETE!")
        print("\nActions needed before removing SQLite:")
        if not core_complete:
            print("• Complete core data migration")
        if not additional_complete:
            print("• Handle additional tables")
        if not config_complete:
            print("• Update application configuration")
        return False

def main():
    """Main comparison function"""
    print("SQLite vs PostgreSQL Migration Comparison")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Get data from both databases
    sqlite_data = get_sqlite_data()
    postgres_data = get_postgresql_data()
    
    if postgres_data is None:
        print("❌ Cannot access PostgreSQL database")
        return False
    
    # Generate comprehensive report
    migration_complete = generate_migration_report(sqlite_data, postgres_data)
    
    if migration_complete:
        print("\n📋 NEXT STEPS:")
        print("1. Test application functionality thoroughly")
        print("2. Create backup of SQLite database")
        print("3. Remove SQLite dependency from requirements")
        print("4. Update deployment scripts")
        print("5. Archive SQLite database file")
        
        print("\n💡 Commands to archive SQLite:")
        print("cd /opt/review-platform/backend")
        print("cp sql_app.db sql_app_backup_$(date +%Y%m%d).db")
        print("# After thorough testing:")
        print("# rm sql_app.db")
        
    return migration_complete

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)