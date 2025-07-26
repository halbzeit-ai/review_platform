#!/usr/bin/env python3
"""
Company Name Extraction Migration Script
Apply database changes to enable company name extraction in DOJO extraction experiments.

Usage:
    python apply_company_name_migration.py [--database-url DATABASE_URL]
    
Environment Variables:
    DATABASE_URL: PostgreSQL connection string (default: localhost)
"""

import argparse
import psycopg2
import os
import sys
from datetime import datetime

def get_database_url():
    """Get database URL from environment or command line"""
    return os.getenv(
        'DATABASE_URL', 
        'postgresql://review_user:review_password@localhost:5432/review-platform'
    )

def check_if_migration_needed(cursor):
    """Check if company name extraction columns already exist"""
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'extraction_experiments' 
        AND column_name = 'company_name_results_json'
    """)
    return cursor.fetchone() is None

def apply_migration(database_url):
    """Apply the company name extraction migration"""
    
    migration_sql = """
-- Migration: Add company name extraction to extraction experiments
-- Date: 2025-07-26
-- Purpose: Enable company name extraction as incremental enrichment of extraction experiments

-- Add company name extraction columns to extraction_experiments table
ALTER TABLE extraction_experiments 
ADD COLUMN company_name_results_json TEXT DEFAULT NULL,
ADD COLUMN company_name_completed_at TIMESTAMP DEFAULT NULL;

-- Add indexes for company name extraction queries
CREATE INDEX IF NOT EXISTS idx_extraction_experiments_company_name_completed_at 
ON extraction_experiments(company_name_completed_at DESC);

-- Add comments for documentation
COMMENT ON COLUMN extraction_experiments.company_name_results_json IS 'JSON object containing company name extraction results for each deck in the experiment';
COMMENT ON COLUMN extraction_experiments.company_name_completed_at IS 'When company name extraction was completed';
"""
    
    try:
        print(f"🔗 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("🔍 Checking if migration is needed...")
        if not check_if_migration_needed(cursor):
            print("⚠️  Migration already applied - company name extraction columns exist")
            cursor.close()
            conn.close()
            return True
        
        print("📝 Applying company name extraction migration...")
        cursor.execute(migration_sql)
        
        print("💾 Committing changes...")
        conn.commit()
        
        print("✅ Company name extraction migration applied successfully!")
        print(f"📊 Applied at: {datetime.now().isoformat()}")
        
        # Verify the migration
        print("🔍 Verifying migration...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'extraction_experiments' 
            AND column_name LIKE 'company_name_%'
            ORDER BY column_name
        """)
        
        columns = cursor.fetchall()
        print(f"✅ Added {len(columns)} company name extraction columns:")
        for col_name, data_type, nullable, default in columns:
            print(f"  - {col_name} ({data_type}, nullable: {nullable}, default: {default})")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Apply company name extraction migration')
    parser.add_argument(
        '--database-url', 
        default=None,
        help='PostgreSQL connection string (overrides environment variable)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without applying changes'
    )
    
    args = parser.parse_args()
    
    # Get database URL
    database_url = args.database_url or get_database_url()
    
    print("🚀 Company Name Extraction Migration")
    print("=" * 50)
    print(f"Database: {database_url.split('@')[-1] if '@' in database_url else 'localhost'}")
    print(f"Dry run: {'Yes' if args.dry_run else 'No'}")
    print()
    
    if args.dry_run:
        print("📋 DRY RUN - Would apply the following changes:")
        print("  - Add company_name_results_json (TEXT)")
        print("  - Add company_name_completed_at (TIMESTAMP)")
        print("  - Create company name extraction indexes")
        print("  - Add column comments")
        print()
        print("🔧 To apply migration, run without --dry-run flag")
        return True
    
    # Confirm before applying
    response = input("Apply migration? (y/N): ").strip().lower()
    if response != 'y':
        print("❌ Migration cancelled")
        return False
    
    # Apply migration
    success = apply_migration(database_url)
    
    if success:
        print()
        print("🎉 Migration completed successfully!")
        print("📋 Next steps:")
        print("  1. Update API endpoints to support company name extraction")
        print("  2. Add company name UI controls to DOJO frontend")
        print("  3. Test company name extraction integration")
    else:
        print()
        print("❌ Migration failed - check error messages above")
        sys.exit(1)

if __name__ == '__main__':
    main()