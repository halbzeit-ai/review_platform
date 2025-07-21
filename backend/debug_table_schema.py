#!/usr/bin/env python3
"""
Debug Database Table Schema
Check the actual structure of tables to understand where data is stored
"""

import sys
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent))

def check_table_schemas():
    """Check the schema of relevant tables"""
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        print("🔍 Database Schema Debug")
        print("=" * 70)
        
        # Check visual_analysis_cache table structure
        print("\n📊 visual_analysis_cache table structure:")
        try:
            schema = db.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'visual_analysis_cache'
                ORDER BY ordinal_position
            """)).fetchall()
            
            if schema:
                for col in schema:
                    name, dtype, nullable = col
                    print(f"   {name}: {dtype} ({'NULL' if nullable == 'YES' else 'NOT NULL'})")
            else:
                print("   ❌ Table doesn't exist")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        # Check extraction_experiments table structure  
        print("\n📊 extraction_experiments table structure:")
        try:
            schema = db.execute(text("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns 
                WHERE table_name = 'extraction_experiments'
                ORDER BY ordinal_position
            """)).fetchall()
            
            if schema:
                for col in schema:
                    name, dtype, nullable = col
                    print(f"   {name}: {dtype} ({'NULL' if nullable == 'YES' else 'NOT NULL'})")
            else:
                print("   ❌ Table doesn't exist")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
        # Check what tables exist
        print("\n📊 Available tables:")
        try:
            tables = db.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)).fetchall()
            
            for table in tables:
                print(f"   - {table[0]}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
            
        # Check recent activity in extraction experiments
        print("\n📊 Recent extraction experiments (fixed query):")
        try:
            # Reset transaction first
            db.rollback()
            
            experiments = db.execute(text("""
                SELECT id, experiment_name, created_at
                FROM extraction_experiments
                ORDER BY created_at DESC
                LIMIT 5
            """)).fetchall()
            
            for exp in experiments:
                exp_id, name, created = exp
                print(f"   Experiment {exp_id}: {name} - {created}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print("\n" + "=" * 70)
        print("🎯 This will show us the correct table structure")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_table_schemas()