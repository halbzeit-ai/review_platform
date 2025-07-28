#!/usr/bin/env python3
"""
Debug Page Count in AI Analysis Results
Check what's actually stored in ai_analysis_results for recent decks
"""

import sys
import json
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent))

def check_page_count_storage():
    """Check what's stored in ai_analysis_results for page count"""
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        # Get recent decks with ai_analysis_results
        decks = db.execute(text("""
            SELECT id, file_name, ai_analysis_results
            FROM pitch_decks 
            WHERE ai_analysis_results IS NOT NULL 
            AND data_source = 'dojo'
            ORDER BY created_at DESC 
            LIMIT 5
        """)).fetchall()
        
        print("🔍 Page Count Debug - Recent Decks with AI Analysis:")
        print("=" * 70)
        
        for deck in decks:
            deck_id, filename, analysis_results = deck
            print(f"\n📄 Deck ID {deck_id}: {filename}")
            
            if analysis_results:
                try:
                    analysis_data = json.loads(analysis_results)
                    print(f"   Analysis keys: {list(analysis_data.keys())}")
                    
                    # Check for various page count fields
                    page_fields = {
                        "page_count": analysis_data.get("page_count"),
                        "total_pages_analyzed": analysis_data.get("total_pages_analyzed"),
                        "total_pages": analysis_data.get("total_pages"),
                        "pages_analyzed": analysis_data.get("pages_analyzed")
                    }
                    
                    found_pages = False
                    for field, value in page_fields.items():
                        if value is not None:
                            print(f"   ✅ {field}: {value}")
                            found_pages = True
                    
                    if not found_pages:
                        print("   ❌ No page count fields found")
                        
                    # Check if there's a processing_info section
                    if "processing_info" in analysis_data:
                        proc_info = analysis_data["processing_info"]
                        print(f"   Processing info keys: {list(proc_info.keys())}")
                        for field, value in page_fields.items():
                            if proc_info.get(field) is not None:
                                print(f"   ✅ processing_info.{field}: {proc_info.get(field)}")
                                
                    # Check nested structures
                    for key, value in analysis_data.items():
                        if isinstance(value, dict):
                            nested_pages = value.get("total_pages_analyzed")
                            if nested_pages:
                                print(f"   ✅ {key}.total_pages_analyzed: {nested_pages}")
                                
                except json.JSONDecodeError as e:
                    print(f"   ❌ JSON decode error: {e}")
                except Exception as e:
                    print(f"   ❌ Error parsing analysis: {e}")
            else:
                print("   ❌ No analysis results")
                
        print("\n" + "=" * 70)
        print("🎯 Summary: Check above for any page count fields found")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_page_count_storage()