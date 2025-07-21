#!/usr/bin/env python3
"""
Classification Enrichment Migration Script
Apply database changes to enable classification testing in DOJO extraction experiments.

Usage:
    python apply_classification_migration.py [--database-url DATABASE_URL]
    
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
    """Check if classification columns already exist"""
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'extraction_experiments' 
        AND column_name = 'classification_enabled'
    """)
    return cursor.fetchone() is None

def apply_migration(database_url):
    """Apply the classification enrichment migration"""
    
    migration_sql = """
-- Migration: Add classification enrichment to extraction experiments
-- Date: 2025-07-21
-- Purpose: Enable classification testing as incremental enrichment of extraction experiments

-- Add classification columns to extraction_experiments table
ALTER TABLE extraction_experiments 
ADD COLUMN classification_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN classification_results_json TEXT DEFAULT NULL,
ADD COLUMN classification_model_used VARCHAR(255) DEFAULT NULL,
ADD COLUMN classification_prompt_used TEXT DEFAULT NULL,
ADD COLUMN classification_completed_at TIMESTAMP DEFAULT NULL;

-- Add indexes for classification queries
CREATE INDEX IF NOT EXISTS idx_extraction_experiments_classification_enabled 
ON extraction_experiments(classification_enabled);

CREATE INDEX IF NOT EXISTS idx_extraction_experiments_classification_completed_at 
ON extraction_experiments(classification_completed_at DESC);

-- Add comments for documentation
COMMENT ON COLUMN extraction_experiments.classification_enabled IS 'Whether classification enrichment has been requested for this experiment';
COMMENT ON COLUMN extraction_experiments.classification_results_json IS 'JSON object containing classification results for each deck in the experiment';
COMMENT ON COLUMN extraction_experiments.classification_model_used IS 'Model used for classification (if different from text model)';
COMMENT ON COLUMN extraction_experiments.classification_prompt_used IS 'Prompt used for classification';
COMMENT ON COLUMN extraction_experiments.classification_completed_at IS 'When classification enrichment was completed';
"""
    
    try:
        print(f"🔗 Connecting to database...")
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        print("🔍 Checking if migration is needed...")
        if not check_if_migration_needed(cursor):
            print("⚠️  Migration already applied - classification columns exist")
            cursor.close()
            conn.close()
            return True
        
        print("📝 Applying classification enrichment migration...")
        cursor.execute(migration_sql)
        
        print("💾 Committing changes...")
        conn.commit()
        
        print("✅ Classification enrichment migration applied successfully!")
        print(f"📊 Applied at: {datetime.now().isoformat()}")
        
        # Verify the migration
        print("🔍 Verifying migration...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'extraction_experiments' 
            AND column_name LIKE 'classification_%'
            ORDER BY column_name
        """)
        
        columns = cursor.fetchall()
        print(f"✅ Added {len(columns)} classification columns:")
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
    parser = argparse.ArgumentParser(description='Apply classification enrichment migration')
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
    
    print("🚀 Classification Enrichment Migration")
    print("=" * 50)
    print(f"Database: {database_url.split('@')[-1] if '@' in database_url else 'localhost'}")
    print(f"Dry run: {'Yes' if args.dry_run else 'No'}")
    print()
    
    if args.dry_run:
        print("📋 DRY RUN - Would apply the following changes:")
        print("  - Add classification_enabled (BOOLEAN)")
        print("  - Add classification_results_json (TEXT)")
        print("  - Add classification_model_used (VARCHAR)")
        print("  - Add classification_prompt_used (TEXT)")
        print("  - Add classification_completed_at (TIMESTAMP)")
        print("  - Create classification indexes")
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
        print("  1. Update API endpoints to support classification enrichment")
        print("  2. Add classification UI controls to DOJO frontend")
        print("  3. Test classification integration")
    else:
        print()
        print("❌ Migration failed - check error messages above")
        sys.exit(1)

if __name__ == '__main__':
    main()