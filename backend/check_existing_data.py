#!/usr/bin/env python3
"""
Quick script to check existing database structure and data
"""

import sys
import os
from sqlalchemy import text

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.database import SessionLocal

def main():
    db = SessionLocal()
    
    try:
        print("=== EXISTING DATABASE STRUCTURE ===\n")
        
        # Check healthcare sectors
        print("Healthcare Sectors:")
        result = db.execute(text("SELECT id, name, display_name FROM healthcare_sectors ORDER BY id"))
        for row in result:
            print(f"  ID {row[0]}: {row[1]} ({row[2]})")
        
        # Check existing templates 
        print("\nExisting Analysis Templates:")
        result = db.execute(text("SELECT id, healthcare_sector_id, name FROM analysis_templates ORDER BY id"))
        for row in result:
            print(f"  ID {row[0]}: {row[2]} (sector_id: {row[1]})")
        
        # Check if our target template exists
        print("\nChecking for 'Standard Seven-Chapter Review':")
        result = db.execute(text("SELECT id, name FROM analysis_templates WHERE name = 'Standard Seven-Chapter Review'"))
        existing = result.fetchone()
        if existing:
            print(f"  ✅ EXISTS: ID {existing[0]} - {existing[1]}")
        else:
            print("  ❌ DOES NOT EXIST")
        
        # Check table schemas to understand constraints
        print("\nTable Constraints:")
        result = db.execute(text("""
            SELECT tc.table_name, tc.constraint_name, tc.constraint_type 
            FROM information_schema.table_constraints tc 
            WHERE tc.table_schema = 'public' 
            AND tc.table_name IN ('healthcare_sectors', 'analysis_templates')
            ORDER BY tc.table_name, tc.constraint_type
        """))
        for row in result:
            print(f"  {row[0]}: {row[1]} ({row[2]})")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()