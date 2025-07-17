#!/usr/bin/env python3
"""
Complete SQLite to PostgreSQL Migration
Migrates ALL tables from SQLite to PostgreSQL, creating tables as needed
"""

import sqlite3
import psycopg2
import sys
import os

def get_sqlite_schema(cursor, table_name):
    """Get CREATE TABLE statement for a SQLite table"""
    cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}';")
    result = cursor.fetchone()
    return result[0] if result else None

def convert_sqlite_to_postgres_schema(sqlite_schema):
    """Convert SQLite CREATE TABLE to PostgreSQL"""
    if not sqlite_schema:
        return None
    
    # Basic conversions
    postgres_schema = sqlite_schema.replace('AUTOINCREMENT', 'SERIAL')
    postgres_schema = postgres_schema.replace('INTEGER PRIMARY KEY AUTOINCREMENT', 'SERIAL PRIMARY KEY')
    postgres_schema = postgres_schema.replace('INTEGER PRIMARY KEY', 'SERIAL PRIMARY KEY')
    postgres_schema = postgres_schema.replace('DATETIME', 'TIMESTAMP')
    postgres_schema = postgres_schema.replace('BOOLEAN', 'BOOLEAN')
    postgres_schema = postgres_schema.replace('TEXT', 'TEXT')
    postgres_schema = postgres_schema.replace('REAL', 'REAL')
    postgres_schema = postgres_schema.replace('BLOB', 'BYTEA')
    
    return postgres_schema

def migrate_table_data(sqlite_cursor, pg_cursor, table_name):
    """Migrate data from SQLite table to PostgreSQL table"""
    print(f"Migrating data for table: {table_name}")
    
    # Get all data from SQLite
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()
    
    if not rows:
        print(f"  No data in {table_name}")
        return 0
    
    # Get column names
    column_names = [description[0] for description in sqlite_cursor.description]
    print(f"  Columns: {column_names}")
    
    # Clear existing data in PostgreSQL
    try:
        pg_cursor.execute(f"DELETE FROM {table_name}")
        print(f"  Cleared existing data in {table_name}")
    except Exception as e:
        print(f"  Could not clear {table_name}: {e}")
    
    # Insert data
    placeholders = ', '.join(['%s'] * len(column_names))
    insert_sql = f"INSERT INTO {table_name} ({', '.join(column_names)}) VALUES ({placeholders})"
    
    successful_inserts = 0
    for row in rows:
        try:
            # Convert SQLite data to PostgreSQL compatible format
            converted_row = []
            for i, value in enumerate(row):
                column_name = column_names[i]
                
                # Convert SQLite boolean integers to PostgreSQL booleans
                if column_name in ['is_verified', 'is_active', 'is_required', 'enabled', 'is_default'] and isinstance(value, int):
                    converted_row.append(bool(value))
                else:
                    converted_row.append(value)
            
            pg_cursor.execute(insert_sql, tuple(converted_row))
            successful_inserts += 1
        except Exception as e:
            print(f"  Error inserting row: {e}")
            print(f"  Row data: {dict(zip(column_names, row))}")
            continue
    
    print(f"  Successfully migrated {successful_inserts}/{len(rows)} rows")
    return successful_inserts

def main():
    """Main migration function"""
    print("Complete SQLite to PostgreSQL Migration")
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
    
    # Connect to databases
    if not os.path.exists(sqlite_path):
        print(f"Error: SQLite database not found at {sqlite_path}")
        return False
    
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()
    
    try:
        pg_conn = psycopg2.connect(
            host=pg_host,
            database=pg_database,
            user=pg_user,
            password=pg_password
        )
        pg_cursor = pg_conn.cursor()
        print("Connected to both databases successfully")
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        sqlite_conn.close()
        return False
    
    # Get all tables from SQLite
    sqlite_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
    tables = [row[0] for row in sqlite_cursor.fetchall()]
    print(f"Found {len(tables)} tables to migrate: {tables}")
    print()
    
    # Create missing tables in PostgreSQL
    for table in tables:
        print(f"Processing table: {table}")
        
        # Check if table exists in PostgreSQL
        pg_cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
        """, (table,))
        table_exists = pg_cursor.fetchone()[0]
        
        if not table_exists:
            print(f"  Creating table {table} in PostgreSQL...")
            
            # Get SQLite schema
            sqlite_schema = get_sqlite_schema(sqlite_cursor, table)
            if not sqlite_schema:
                print(f"  Could not get schema for {table}")
                continue
            
            # Convert to PostgreSQL schema
            postgres_schema = convert_sqlite_to_postgres_schema(sqlite_schema)
            if not postgres_schema:
                print(f"  Could not convert schema for {table}")
                continue
            
            try:
                pg_cursor.execute(postgres_schema)
                print(f"  ✅ Created table {table}")
            except Exception as e:
                print(f"  ❌ Error creating table {table}: {e}")
                continue
        else:
            print(f"  Table {table} already exists in PostgreSQL")
    
    # Migrate data for all tables
    print("\nMigrating data...")
    total_rows = 0
    
    for table in tables:
        try:
            rows_migrated = migrate_table_data(sqlite_cursor, pg_cursor, table)
            total_rows += rows_migrated
        except Exception as e:
            print(f"Error migrating table {table}: {e}")
            continue
    
    # Commit changes
    try:
        pg_conn.commit()
        print(f"\n✅ Migration completed successfully! Total rows migrated: {total_rows}")
        
        # Verify migration
        print("\nVerifying migration...")
        for table in tables:
            try:
                pg_cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = pg_cursor.fetchone()[0]
                print(f"  {table}: {count} rows")
            except Exception as e:
                print(f"  {table}: Error - {e}")
        
    except Exception as e:
        print(f"Error committing changes: {e}")
        pg_conn.rollback()
        return False
    
    # Close connections
    sqlite_conn.close()
    pg_conn.close()
    
    print("\n🎉 Complete migration finished!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)