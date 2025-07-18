#!/usr/bin/env python3
"""
Script to fix the dojo stats endpoint SQLAlchemy compatibility issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def fix_dojo_stats():
    print("=== Fixing Dojo Stats Endpoint ===")
    
    # Path to the dojo.py file
    dojo_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'app', 'api', 'dojo.py')
    
    print(f"Reading: {dojo_file_path}")
    
    try:
        with open(dojo_file_path, 'r') as f:
            content = f.read()
        
        # Replace the problematic func.case syntax
        old_stats_query = """        stats = db.query(
            func.count(PitchDeck.id).label('total_files'),
            func.sum(func.case([(PitchDeck.processing_status == 'completed', 1)], else_=0)).label('processed_files'),
            func.sum(func.case([(PitchDeck.processing_status == 'pending', 1)], else_=0)).label('pending_files'),
            func.sum(func.case([(PitchDeck.processing_status == 'failed', 1)], else_=0)).label('failed_files')
        ).filter(PitchDeck.data_source == "dojo").first()"""
        
        new_stats_query = """        # Get counts using separate queries (SQLAlchemy compatibility)
        total_files = db.query(PitchDeck).filter(PitchDeck.data_source == "dojo").count()
        processed_files = db.query(PitchDeck).filter(
            PitchDeck.data_source == "dojo",
            PitchDeck.processing_status == 'completed'
        ).count()
        pending_files = db.query(PitchDeck).filter(
            PitchDeck.data_source == "dojo",
            PitchDeck.processing_status == 'pending'
        ).count()
        failed_files = db.query(PitchDeck).filter(
            PitchDeck.data_source == "dojo",
            PitchDeck.processing_status == 'failed'
        ).count()"""
        
        # Replace the return statement
        old_return = """        return {
            "total_files": stats.total_files or 0,
            "processed_files": stats.processed_files or 0,
            "pending_files": stats.pending_files or 0,
            "failed_files": stats.failed_files or 0,
            "directory": DOJO_PATH
        }"""
        
        new_return = """        return {
            "total_files": total_files,
            "processed_files": processed_files,
            "pending_files": pending_files,
            "failed_files": failed_files,
            "directory": DOJO_PATH
        }"""
        
        # Remove the func import if it exists
        content = content.replace("        from sqlalchemy import func\n        \n", "")
        
        # Apply the fixes
        if old_stats_query in content:
            content = content.replace(old_stats_query, new_stats_query)
            print("✓ Fixed stats query")
        else:
            print("⚠ Stats query not found - may already be fixed")
        
        if old_return in content:
            content = content.replace(old_return, new_return)
            print("✓ Fixed return statement")
        else:
            print("⚠ Return statement not found - may already be fixed")
        
        # Write the fixed content
        with open(dojo_file_path, 'w') as f:
            f.write(content)
        
        print("✓ Dojo stats endpoint fixed")
        print("✓ Please restart FastAPI application")
        
    except Exception as e:
        print(f"✗ Error fixing dojo stats: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = fix_dojo_stats()
    if not success:
        sys.exit(1)