#!/usr/bin/env python3
"""
Production PostgreSQL Migration Script
Complete migration process for moving from SQLite to PostgreSQL on production
"""

import os
import sys
import subprocess
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import sqlite3
from datetime import datetime

def log_step(step_name, success=True):
    """Log migration step with timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "✅" if success else "❌"
    print(f"{timestamp} {status} {step_name}")

def backup_sqlite_database():
    """Create a backup of the SQLite database before migration"""
    log_step("Creating SQLite database backup")
    
    sqlite_path = "/opt/review-platform/backend/sql_app.db"
    backup_path = f"/opt/review-platform/backend/sql_app_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    try:
        if os.path.exists(sqlite_path):
            subprocess.run(["cp", sqlite_path, backup_path], check=True)
            log_step(f"SQLite backup created: {backup_path}")
            return backup_path
        else:
            log_step("SQLite database not found - no backup needed")
            return None
    except Exception as e:
        log_step(f"SQLite backup failed: {e}", False)
        return None

def setup_postgresql_user():
    """Create PostgreSQL user and database if they don't exist"""
    log_step("Setting up PostgreSQL user and database")
    
    try:
        # Connect as postgres superuser
        conn = psycopg2.connect(
            host='localhost',
            database='postgres',
            user='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Create user if not exists
        cursor.execute("""
            SELECT 1 FROM pg_roles WHERE rolname = 'review_user';
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE USER review_user WITH PASSWORD 'review_password';
            """)
            log_step("Created PostgreSQL user: review_user")
        else:
            log_step("PostgreSQL user already exists")
        
        # Create database if not exists
        cursor.execute("""
            SELECT 1 FROM pg_database WHERE datname = 'review-platform';
        """)
        if not cursor.fetchone():
            cursor.execute("""
                CREATE DATABASE "review-platform" OWNER review_user;
            """)
            log_step("Created PostgreSQL database: review-platform")
        else:
            log_step("PostgreSQL database already exists")
        
        # Grant permissions
        cursor.execute("""
            GRANT ALL PRIVILEGES ON DATABASE "review-platform" TO review_user;
        """)
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        log_step(f"PostgreSQL setup failed: {e}", False)
        return False

def create_sqlalchemy_tables():
    """Create tables using SQLAlchemy models"""
    log_step("Creating SQLAlchemy tables")
    
    try:
        # Run the table creation script
        script_path = "/opt/review-platform/scripts/create_postgres_tables.py"
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            log_step("SQLAlchemy tables created successfully")
            return True
        else:
            log_step(f"SQLAlchemy table creation failed: {result.stderr}", False)
            return False
            
    except Exception as e:
        log_step(f"Error creating SQLAlchemy tables: {e}", False)
        return False

def run_sql_migrations():
    """Run all SQL migration scripts"""
    log_step("Running SQL migration scripts")
    
    migration_dir = "/opt/review-platform/backend/migrations"
    migration_files = [
        "add_company_id_and_results_path.sql",
        "add_results_file_path.sql", 
        "create_healthcare_templates.sql",
        "insert_healthcare_sectors.sql",
        "insert_digital_therapeutics_template.sql",
        "create_pipeline_prompts.sql",
        "add_company_offering_prompt.sql"
    ]
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        for migration_file in migration_files:
            migration_path = os.path.join(migration_dir, migration_file)
            
            if os.path.exists(migration_path):
                log_step(f"Running migration: {migration_file}")
                
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                
                try:
                    cursor.execute(migration_sql)
                    conn.commit()
                    log_step(f"Migration {migration_file} completed")
                except Exception as e:
                    log_step(f"Migration {migration_file} failed: {e}", False)
                    conn.rollback()
                    # Continue with other migrations
            else:
                log_step(f"Migration file not found: {migration_file}", False)
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        log_step(f"SQL migrations failed: {e}", False)
        return False

def migrate_sqlite_data():
    """Migrate data from SQLite to PostgreSQL"""
    log_step("Migrating data from SQLite to PostgreSQL")
    
    try:
        # Run the complete migration script
        script_path = "/opt/review-platform/scripts/complete_postgres_migration.py"
        result = subprocess.run([sys.executable, script_path], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            log_step("Data migration completed successfully")
            print(result.stdout)
            return True
        else:
            log_step(f"Data migration failed: {result.stderr}", False)
            return False
            
    except Exception as e:
        log_step(f"Error during data migration: {e}", False)
        return False

def verify_migration():
    """Verify that migration was successful"""
    log_step("Verifying migration results")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Check core tables
        core_tables = ['users', 'pitch_decks', 'reviews', 'questions', 'answers', 'model_configs']
        healthcare_tables = ['healthcare_sectors', 'analysis_templates', 'template_chapters', 'chapter_questions']
        
        print("\nMigration Verification:")
        print("-" * 30)
        
        total_rows = 0
        for table in core_tables + healthcare_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table};")
                count = cursor.fetchone()[0]
                print(f"{table}: {count} rows")
                total_rows += count
            except Exception as e:
                print(f"{table}: Error - {e}")
        
        cursor.close()
        conn.close()
        
        log_step(f"Migration verification completed - {total_rows} total rows")
        return total_rows > 0
        
    except Exception as e:
        log_step(f"Migration verification failed: {e}", False)
        return False

def update_application_config():
    """Update application to use PostgreSQL"""
    log_step("Updating application configuration")
    
    try:
        # The config is already set to PostgreSQL in config.py
        # Just restart the application service
        result = subprocess.run(["systemctl", "restart", "review-platform"], 
                              capture_output=True, text=True)
        
        if result.returncode == 0:
            log_step("Application service restarted")
            return True
        else:
            log_step(f"Application restart failed: {result.stderr}", False)
            return False
            
    except Exception as e:
        log_step(f"Error updating application: {e}", False)
        return False

def main():
    """Main migration function"""
    print("Production PostgreSQL Migration")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    steps = [
        ("Backup SQLite database", backup_sqlite_database),
        ("Setup PostgreSQL user/database", setup_postgresql_user),
        ("Create SQLAlchemy tables", create_sqlalchemy_tables),
        ("Run SQL migrations", run_sql_migrations),
        ("Migrate SQLite data", migrate_sqlite_data),
        ("Verify migration", verify_migration),
        ("Update application config", update_application_config)
    ]
    
    for step_name, step_func in steps:
        print(f"\n{step_name}...")
        print("-" * 40)
        
        success = step_func()
        if not success:
            print(f"\n❌ Migration failed at step: {step_name}")
            print("Please check the errors above and fix them before retrying.")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 MIGRATION COMPLETED SUCCESSFULLY!")
    print("=" * 50)
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("Next steps:")
    print("1. Test the application with PostgreSQL")
    print("2. Monitor logs for any issues")
    print("3. Remove SQLite database after confirming everything works")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)