#!/usr/bin/env python3
"""
SQLite to PostgreSQL Migration Script
Migrates data from SQLite database to PostgreSQL for multi-server access
"""

import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
import sys
import os

def migrate_database(sqlite_path, pg_host, pg_database, pg_user, pg_password):
    """Migrate data from SQLite to PostgreSQL"""
    
    print(f"Starting migration from {sqlite_path} to PostgreSQL...")
    
    # Connect to SQLite
    if not os.path.exists(sqlite_path):
        print(f"Error: SQLite database not found at {sqlite_path}")
        return False
    
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    
    # Connect to PostgreSQL
    try:
        pg_conn = psycopg2.connect(
            host=pg_host,
            database=pg_database,
            user=pg_user,
            password=pg_password
        )
        pg_cursor = pg_conn.cursor()
        print("Connected to PostgreSQL successfully")
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        sqlite_conn.close()
        return False
    
    # Get all table names from SQLite
    sqlite_cursor = sqlite_conn.cursor()
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in sqlite_cursor.fetchall()]
    
    print(f"Found tables: {tables}")
    
    # Copy data table by table
    total_rows = 0
    for table in tables:
        print(f"\nCopying table: {table}")
        
        # Get all rows from SQLite
        sqlite_cursor.execute(f"SELECT * FROM {table}")
        rows = sqlite_cursor.fetchall()
        
        if not rows:
            print(f"  No data in {table}")
            continue
        
        # Get column names
        columns = [description[0] for description in sqlite_cursor.description]
        print(f"  Columns: {columns}")
        
        # Clear existing data in PostgreSQL table (if any)
        try:
            pg_cursor.execute(f"DELETE FROM {table}")
            print(f"  Cleared existing data in {table}")
        except Exception as e:
            print(f"  Warning: Could not clear {table}: {e}")
        
        # Create INSERT statement
        placeholders = ', '.join(['%s'] * len(columns))
        insert_sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        # Insert data with data type conversion
        successful_inserts = 0
        for row in rows:
            try:
                # Convert SQLite data to PostgreSQL compatible format
                converted_row = []
                for i, value in enumerate(row):
                    column_name = columns[i]
                    
                    # Convert SQLite boolean integers to PostgreSQL booleans
                    if column_name in ['is_verified', 'is_active', 'is_required', 'enabled', 'is_default'] and isinstance(value, int):
                        converted_row.append(bool(value))
                    else:
                        converted_row.append(value)
                
                pg_cursor.execute(insert_sql, tuple(converted_row))
                successful_inserts += 1
            except Exception as e:
                print(f"  Error inserting row: {e}")
                print(f"  Row data: {dict(row)}")
                continue
        
        print(f"  Successfully copied {successful_inserts}/{len(rows)} rows")
        total_rows += successful_inserts
    
    # Commit changes
    try:
        pg_conn.commit()
        print(f"\nMigration completed successfully! Total rows migrated: {total_rows}")
        
        # Verify migration
        print("\nVerifying migration...")
        for table in tables:
            try:
                pg_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = pg_cursor.fetchone()[0]
                print(f"  {table}: {count} rows")
            except Exception as e:
                print(f"  {table}: Table not found in PostgreSQL - {e}")
        
    except Exception as e:
        print(f"Error committing changes: {e}")
        pg_conn.rollback()
        return False
    
    # Close connections
    sqlite_conn.close()
    pg_conn.close()
    
    return True

def main():
    """Main migration function"""
    print("SQLite to PostgreSQL Migration Tool")
    print("=" * 50)
    
    # Configuration
    sqlite_path = "/opt/review-platform/backend/sql_app.db"
    pg_host = "localhost"
    pg_database = "review-platform"
    pg_user = "review_user"
    pg_password = "review_password"
    
    print(f"SQLite source: {sqlite_path}")
    print(f"PostgreSQL target: {pg_user}@{pg_host}/{pg_database}")
    print()
    
    # Run migration
    success = migrate_database(sqlite_path, pg_host, pg_database, pg_user, pg_password)
    
    if success:
        print("\n✅ Migration completed successfully!")
        print("You can now update your application configuration to use PostgreSQL.")
        sys.exit(0)
    else:
        print("\n❌ Migration failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()