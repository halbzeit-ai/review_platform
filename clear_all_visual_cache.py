#!/usr/bin/env python3
"""
Clear all visual analysis cache entries
Run on production server
"""

import os
import sys

sys.path.append('/opt/review-platform/backend')

def main():
    print("=== CLEAR ALL VISUAL ANALYSIS CACHE ===")
    
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db_session = next(get_db())
        print("✅ Connected to backend database")
        
        # Count existing cache entries
        count_result = db_session.execute(text("SELECT COUNT(*) FROM visual_analysis_cache")).fetchone()
        cache_count = count_result[0] if count_result else 0
        
        print(f"Found {cache_count} visual analysis cache entries")
        
        if cache_count == 0:
            print("No cache entries to clear")
            return
        
        confirm = input(f"Clear all {cache_count} visual analysis cache entries? (yes/no): ")
        
        if confirm.lower() == 'yes':
            # Clear all cache entries
            result = db_session.execute(text("DELETE FROM visual_analysis_cache"))
            deleted_count = result.rowcount
            
            db_session.commit()
            
            print(f"✅ Cleared {deleted_count} visual analysis cache entries")
        else:
            print("Cache clearing cancelled")
        
        db_session.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== CACHE CLEARING COMPLETE ===")

if __name__ == "__main__":
    main()