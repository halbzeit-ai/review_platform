#!/usr/bin/env python3
"""
Production migration script to add data_source field to pitch_decks table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import engine
from sqlalchemy import text

def run_dojo_migration():
    print("=== Running Dojo Migration ===")
    
    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Check if data_source column exists
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'pitch_decks' 
                    AND column_name = 'data_source'
                """))
                
                if result.fetchone():
                    print("✓ data_source column already exists")
                else:
                    print("Adding data_source column...")
                    conn.execute(text("""
                        ALTER TABLE pitch_decks 
                        ADD COLUMN data_source VARCHAR DEFAULT 'startup'
                    """))
                    print("✓ data_source column added")
                
                # Check if ai_extracted_startup_name column exists
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'pitch_decks' 
                    AND column_name = 'ai_extracted_startup_name'
                """))
                
                if result.fetchone():
                    print("✓ ai_extracted_startup_name column already exists")
                else:
                    print("Adding ai_extracted_startup_name column...")
                    conn.execute(text("""
                        ALTER TABLE pitch_decks 
                        ADD COLUMN ai_extracted_startup_name VARCHAR
                    """))
                    print("✓ ai_extracted_startup_name column added")
                
                # Commit transaction
                trans.commit()
                print("✓ Migration completed successfully")
                
            except Exception as e:
                trans.rollback()
                raise e
                
    except Exception as e:
        print(f"✗ Migration failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = run_dojo_migration()
    if success:
        print("\n=== Migration Summary ===")
        print("✓ data_source column added (default: 'startup')")
        print("✓ ai_extracted_startup_name column added")
        print("✓ Ready to restart FastAPI application")
    else:
        print("\n✗ Migration failed - check errors above")
        sys.exit(1)