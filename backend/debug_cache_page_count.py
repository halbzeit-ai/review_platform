#!/usr/bin/env python3
"""
Debug Visual Analysis Cache for Page Count
Check the visual_analysis_cache table for page count data
"""

import sys
import json
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent))

def check_cache_page_count():
    """Check visual analysis cache for page count"""
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        print("🔍 Visual Analysis Cache Page Count Debug")
        print("=" * 70)
        
        # First check what columns exist in visual_analysis_cache
        try:
            schema = db.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'visual_analysis_cache'
                ORDER BY ordinal_position
            """)).fetchall()
            
            print("📊 visual_analysis_cache columns:")
            columns = []
            for col in schema:
                name, dtype = col
                columns.append(name)
                print(f"   {name}: {dtype}")
            
            if not columns:
                print("   ❌ Table doesn't exist")
                return
                
        except Exception as e:
            print(f"   ❌ Error checking schema: {e}")
            return
        
        # Get recent cache entries
        try:
            # Use actual column names
            cache_entries = db.execute(text(f"""
                SELECT pitch_deck_id, {', '.join(columns)}
                FROM visual_analysis_cache
                ORDER BY created_at DESC
                LIMIT 5
            """)).fetchall()
            
            print(f"\n📊 Recent cache entries ({len(cache_entries)}):")
            
            for entry in cache_entries:
                deck_id = entry[0]
                print(f"\n   Deck ID {deck_id}:")
                
                # Look at each column for potential page count or results
                for i, col_name in enumerate(columns):
                    if i == 0:  # skip deck_id
                        continue
                    value = entry[i]
                    
                    if value and col_name in ['results', 'analysis_data', 'visual_analysis', 'cache_data']:
                        # Try to parse JSON if it looks like results
                        try:
                            if isinstance(value, str):
                                data = json.loads(value)
                                print(f"     {col_name} keys: {list(data.keys()) if isinstance(data, dict) else 'not dict'}")
                                
                                # Look for page count
                                if isinstance(data, dict):
                                    for page_field in ['page_count', 'total_pages_analyzed', 'total_pages']:
                                        if page_field in data:
                                            print(f"     ✅ Found {page_field}: {data[page_field]}")
                                            
                        except json.JSONDecodeError:
                            print(f"     {col_name}: {str(value)[:100]}...")
                        except Exception as e:
                            print(f"     {col_name}: Error parsing - {e}")
                    else:
                        print(f"     {col_name}: {value}")
                        
        except Exception as e:
            print(f"   ❌ Error querying cache: {e}")
        
        print("\n" + "=" * 70)
        print("🎯 This should show us where page count is stored")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_cache_page_count()