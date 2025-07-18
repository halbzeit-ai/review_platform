#!/usr/bin/env python3
"""
Complete Pitch Deck Migration
Migrates missing pitch_decks from SQLite to PostgreSQL
"""

import sqlite3
import psycopg2
import sys
import os
from datetime import datetime

def get_missing_pitch_decks():
    """Find pitch decks that exist in SQLite but not in PostgreSQL"""
    print("🔍 Finding missing pitch decks...")
    
    try:
        # Get SQLite pitch decks
        sqlite_conn = sqlite3.connect("/opt/review-platform/backend/sql_app.db")
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        
        sqlite_cursor.execute("SELECT * FROM pitch_decks ORDER BY id")
        sqlite_decks = sqlite_cursor.fetchall()
        
        # Get PostgreSQL pitch decks
        pg_conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        pg_cursor = pg_conn.cursor()
        
        pg_cursor.execute("SELECT id, file_name, company_id, user_id FROM pitch_decks ORDER BY id")
        pg_decks = pg_cursor.fetchall()
        
        # Find missing decks
        pg_deck_ids = {row[0] for row in pg_decks}
        missing_decks = []
        
        print(f"   SQLite has {len(sqlite_decks)} pitch decks")
        print(f"   PostgreSQL has {len(pg_decks)} pitch decks")
        print(f"   PostgreSQL deck IDs: {sorted(pg_deck_ids)}")
        
        for deck in sqlite_decks:
            if deck['id'] not in pg_deck_ids:
                missing_decks.append(deck)
                print(f"   Missing: ID {deck['id']} - {deck['file_name']} ({deck['company_id']})")
        
        sqlite_conn.close()
        pg_conn.close()
        
        return missing_decks
        
    except Exception as e:
        print(f"   ❌ Error finding missing pitch decks: {e}")
        return []

def migrate_missing_decks(missing_decks):
    """Migrate missing pitch decks to PostgreSQL"""
    print(f"\n📦 Migrating {len(missing_decks)} missing pitch decks...")
    
    if not missing_decks:
        print("   ✅ No missing decks to migrate")
        return True
    
    try:
        pg_conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        pg_cursor = pg_conn.cursor()
        
        for deck in missing_decks:
            print(f"   Migrating: ID {deck['id']} - {deck['file_name']}")
            
            # Convert SQLite data to PostgreSQL format
            pg_cursor.execute("""
                INSERT INTO pitch_decks 
                (id, user_id, company_id, file_name, file_path, results_file_path, 
                 s3_url, processing_status, ai_analysis_results, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (
                deck['id'],
                deck['user_id'],
                deck['company_id'],
                deck['file_name'],
                deck['file_path'],
                deck['results_file_path'],
                deck['s3_url'],
                deck['processing_status'],
                deck['ai_analysis_results'],
                deck['created_at']
            ))
        
        pg_conn.commit()
        
        # Update sequence to avoid ID conflicts
        pg_cursor.execute("SELECT MAX(id) FROM pitch_decks")
        max_id = pg_cursor.fetchone()[0]
        if max_id:
            pg_cursor.execute(f"ALTER SEQUENCE pitch_decks_id_seq RESTART WITH {max_id + 1}")
            pg_conn.commit()
        
        pg_conn.close()
        
        print(f"   ✅ Successfully migrated {len(missing_decks)} pitch decks")
        return True
        
    except Exception as e:
        print(f"   ❌ Error migrating pitch decks: {e}")
        return False

def verify_migration_complete():
    """Verify that migration is now complete"""
    print("\n🔍 Verifying migration completion...")
    
    try:
        # Count SQLite pitch decks
        sqlite_conn = sqlite3.connect("/opt/review-platform/backend/sql_app.db")
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT COUNT(*) FROM pitch_decks")
        sqlite_count = sqlite_cursor.fetchone()[0]
        sqlite_conn.close()
        
        # Count PostgreSQL pitch decks
        pg_conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        pg_cursor = pg_conn.cursor()
        pg_cursor.execute("SELECT COUNT(*) FROM pitch_decks")
        pg_count = pg_cursor.fetchone()[0]
        pg_conn.close()
        
        print(f"   SQLite pitch_decks: {sqlite_count}")
        print(f"   PostgreSQL pitch_decks: {pg_count}")
        
        if sqlite_count == pg_count:
            print("   ✅ Migration complete - counts match!")
            return True
        else:
            print(f"   ❌ Migration incomplete - {sqlite_count - pg_count} decks still missing")
            return False
            
    except Exception as e:
        print(f"   ❌ Error verifying migration: {e}")
        return False

def check_application_database_usage():
    """Check if application is still using SQLite"""
    print("\n🔍 Checking current database usage...")
    
    try:
        # Check if application service is running
        import subprocess
        result = subprocess.run(["systemctl", "is-active", "review-platform"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            print("   ✅ Application service is running")
            
            # Check recent logs for database connections
            log_result = subprocess.run(["journalctl", "-u", "review-platform", 
                                       "--since", "1 hour ago", "--no-pager"], 
                                      capture_output=True, text=True)
            
            if "postgresql" in log_result.stdout.lower():
                print("   ✅ Application logs show PostgreSQL usage")
            if "sqlite" in log_result.stdout.lower():
                print("   ⚠️  Application logs show SQLite usage")
            
        else:
            print("   ⚠️  Application service not running")
        
        # Check SQLite file modification time
        sqlite_path = "/opt/review-platform/backend/sql_app.db"
        if os.path.exists(sqlite_path):
            mtime = os.path.getmtime(sqlite_path)
            last_modified = datetime.fromtimestamp(mtime)
            minutes_ago = (datetime.now() - last_modified).total_seconds() / 60
            
            if minutes_ago < 5:
                print(f"   ⚠️  SQLite file modified {minutes_ago:.1f} minutes ago - may still be in use")
                return False
            else:
                print(f"   ✅ SQLite file last modified {minutes_ago:.1f} minutes ago")
                return True
        else:
            print("   ✅ SQLite file not found")
            return True
            
    except Exception as e:
        print(f"   ❌ Error checking application usage: {e}")
        return False

def main():
    """Main migration completion function"""
    print("Complete Pitch Deck Migration")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Find missing pitch decks
    missing_decks = get_missing_pitch_decks()
    
    if not missing_decks:
        print("✅ No missing pitch decks found!")
    else:
        # Migrate missing decks
        migration_success = migrate_missing_decks(missing_decks)
        if not migration_success:
            print("❌ Migration failed!")
            return False
    
    # Verify migration is complete
    verification_success = verify_migration_complete()
    if not verification_success:
        print("❌ Migration verification failed!")
        return False
    
    # Check application usage
    app_check = check_application_database_usage()
    
    print("\n" + "=" * 50)
    print("MIGRATION COMPLETION SUMMARY")
    print("=" * 50)
    
    if verification_success and app_check:
        print("🎉 PITCH DECK MIGRATION COMPLETE!")
        print("\n✅ All pitch decks migrated to PostgreSQL")
        print("✅ Application appears to be using PostgreSQL")
        print("\nNext steps:")
        print("1. Restart application service to ensure clean state")
        print("2. Test uploading a new pitch deck")
        print("3. Monitor logs for any SQLite usage")
        print("4. Run final comparison script")
        return True
    else:
        print("⚠️  MIGRATION ISSUES REMAINING")
        print("\nActions needed:")
        if not verification_success:
            print("• Complete pitch deck data migration")
        if not app_check:
            print("• Ensure application stops using SQLite")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)