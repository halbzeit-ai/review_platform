#!/usr/bin/env python3
"""
Debug Actual Cache Data
Check what's actually stored in the visual_analysis_cache.analysis_result_json
"""

import sys
import json
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent))

def check_actual_cache_data():
    """Check what's actually in the cache"""
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        print("🔍 Actual Visual Analysis Cache Data")
        print("=" * 70)
        
        # Get recent cache entries with actual JSON data
        cache_entries = db.execute(text("""
            SELECT pitch_deck_id, analysis_result_json, vision_model_used, created_at
            FROM visual_analysis_cache
            ORDER BY created_at DESC
            LIMIT 3
        """)).fetchall()
        
        print(f"📊 Found {len(cache_entries)} cache entries:")
        
        for entry in cache_entries:
            deck_id, json_data, model, created = entry
            print(f"\n🔍 Deck ID {deck_id} (Model: {model}, Created: {created}):")
            
            if json_data:
                try:
                    analysis = json.loads(json_data)
                    print(f"   JSON keys: {list(analysis.keys())}")
                    
                    # Look specifically for page count fields
                    page_fields = {
                        "page_count": analysis.get("page_count"),
                        "total_pages_analyzed": analysis.get("total_pages_analyzed"), 
                        "total_pages": analysis.get("total_pages"),
                        "pages_analyzed": analysis.get("pages_analyzed")
                    }
                    
                    found_any = False
                    for field, value in page_fields.items():
                        if value is not None:
                            print(f"   ✅ {field}: {value}")
                            found_any = True
                    
                    if not found_any:
                        print("   ❌ No direct page count fields found")
                        
                        # Check nested structures
                        for key, value in analysis.items():
                            if isinstance(value, dict):
                                print(f"   🔍 Nested object '{key}' keys: {list(value.keys())}")
                                for pf in ["page_count", "total_pages_analyzed", "total_pages"]:
                                    if pf in value:
                                        print(f"   ✅ {key}.{pf}: {value[pf]}")
                                        found_any = True
                        
                        # Show a sample of the actual data structure
                        if not found_any:
                            print("   📋 Sample data structure:")
                            for key, value in list(analysis.items())[:5]:
                                if isinstance(value, (str, int, float, bool)):
                                    print(f"     {key}: {value}")
                                elif isinstance(value, list):
                                    print(f"     {key}: [list with {len(value)} items]")
                                elif isinstance(value, dict):
                                    print(f"     {key}: [dict with keys: {list(value.keys())[:3]}...]")
                                    
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON parsing error: {e}")
                except Exception as e:
                    print(f"   ❌ Error analyzing data: {e}")
            else:
                print("   ❌ No JSON data")
                
        print("\n" + "=" * 70)
        print("🎯 This shows exactly what's stored and if page count exists")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_actual_cache_data()