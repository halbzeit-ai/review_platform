#!/usr/bin/env python3
"""
Project Migration Script
Migrates from deck-centric to project-centric database structure
"""

import os
import sys
import sqlite3
import json
from pathlib import Path

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.core.config import settings

def run_sql_file(cursor, file_path):
    """Execute SQL commands from a file"""
    print(f"Running SQL file: {file_path}")
    
    with open(file_path, 'r') as f:
        sql_content = f.read()
    
    # Split by semicolon and execute each statement
    statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
    
    for i, statement in enumerate(statements):
        if statement:
            try:
                cursor.execute(statement)
                print(f"  ✓ Statement {i+1}/{len(statements)} executed")
            except Exception as e:
                print(f"  ✗ Error in statement {i+1}: {e}")
                print(f"    Statement: {statement[:100]}...")
                raise

def update_file_sizes(cursor):
    """Update file sizes for migrated documents"""
    print("Updating file sizes for migrated documents...")
    
    cursor.execute("""
        SELECT id, file_path FROM project_documents 
        WHERE file_size IS NULL AND is_active = 1
    """)
    
    documents = cursor.fetchall()
    updated_count = 0
    
    for doc_id, file_path in documents:
        try:
            if file_path.startswith('/'):
                full_path = file_path
            else:
                full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, file_path)
            
            if os.path.exists(full_path):
                file_size = os.path.getsize(full_path)
                cursor.execute(
                    "UPDATE project_documents SET file_size = ? WHERE id = ?",
                    (file_size, doc_id)
                )
                updated_count += 1
        except Exception as e:
            print(f"  Warning: Could not update file size for document {doc_id}: {e}")
    
    print(f"  ✓ Updated file sizes for {updated_count} documents")

def verify_migration(cursor):
    """Verify the migration was successful"""
    print("\nVerifying migration results...")
    
    # Check original data counts
    cursor.execute("SELECT COUNT(*) FROM pitch_decks")
    original_pitch_decks = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM reviews")
    original_reviews = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM questions")
    original_questions = cursor.fetchone()[0]
    
    # Check migrated data counts
    cursor.execute("SELECT COUNT(*) FROM projects")
    migrated_projects = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM project_documents WHERE document_type = 'pitch_deck'")
    migrated_documents = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM project_interactions WHERE interaction_type = 'review'")
    migrated_reviews = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM project_interactions WHERE interaction_type = 'question'")
    migrated_questions = cursor.fetchone()[0]
    
    print(f"\nMigration Summary:")
    print(f"  Original pitch_decks: {original_pitch_decks}")
    print(f"  Original reviews: {original_reviews}")
    print(f"  Original questions: {original_questions}")
    print(f"  ")
    print(f"  Created projects: {migrated_projects}")
    print(f"  Migrated documents: {migrated_documents}")
    print(f"  Migrated reviews: {migrated_reviews}")
    print(f"  Migrated questions: {migrated_questions}")
    
    # Show project breakdown
    cursor.execute("""
        SELECT company_id, project_name, COUNT(pd.id) as document_count
        FROM projects p
        LEFT JOIN project_documents pd ON p.id = pd.project_id
        GROUP BY p.id, company_id, project_name
        ORDER BY company_id
    """)
    
    projects = cursor.fetchall()
    print(f"\nProject Breakdown:")
    for company_id, project_name, doc_count in projects:
        print(f"  {company_id}: '{project_name}' ({doc_count} documents)")

def main():
    """Run the complete project migration"""
    print("Starting Project Migration: Deck Analysis → Multi-Project Funding Management")
    print("=" * 80)
    
    # Get database path
    if hasattr(settings, 'DATABASE_URL') and settings.DATABASE_URL.startswith('sqlite:'):
        db_path = settings.DATABASE_URL.replace('sqlite:///', '')
    else:
        db_path = os.path.join(os.path.dirname(__file__), 'sql_app.db')
    
    print(f"Using database: {db_path}")
    
    if not os.path.exists(db_path):
        print(f"Error: Database file not found at {db_path}")
        return
    
    # Connect to database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Step 1: Create new tables
        print("\n1. Creating new project tables...")
        run_sql_file(cursor, 'migrations/create_project_tables.sql')
        conn.commit()
        
        # Step 2: Migrate existing data
        print("\n2. Migrating existing pitch deck data...")
        run_sql_file(cursor, 'migrations/migrate_pitch_decks_to_projects.sql')
        conn.commit()
        
        # Step 3: Update file sizes
        print("\n3. Updating file metadata...")
        update_file_sizes(cursor)
        conn.commit()
        
        # Step 4: Verify migration
        verify_migration(cursor)
        
        print("\n" + "=" * 80)
        print("✓ Project migration completed successfully!")
        print("  - New project-centric tables created")
        print("  - Existing pitch deck data migrated to projects")
        print("  - Reviews and questions converted to project interactions")
        print("  - File metadata updated")
        print("\nNext steps:")
        print("  1. Define your custom funding process stages")
        print("  2. Update API endpoints to use project-centric structure")
        print("  3. Update frontend to support multi-project view")
        
    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

if __name__ == "__main__":
    main()