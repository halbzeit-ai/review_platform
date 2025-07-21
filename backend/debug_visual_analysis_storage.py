#!/usr/bin/env python3
"""
Debug Visual Analysis Results Storage
Check where visual analysis results are actually stored
"""

import sys
import json
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent))

def check_visual_analysis_storage():
    """Check where visual analysis results are stored"""
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        print("🔍 Visual Analysis Storage Debug")
        print("=" * 70)
        
        # Check recent dojo decks
        print("\n📊 Recent DOJO decks:")
        decks = db.execute(text("""
            SELECT id, file_name, processing_status, ai_analysis_results IS NOT NULL as has_analysis,
                   LENGTH(ai_analysis_results) as analysis_length, created_at
            FROM pitch_decks 
            WHERE data_source = 'dojo'
            ORDER BY created_at DESC 
            LIMIT 10
        """)).fetchall()
        
        for deck in decks:
            deck_id, filename, status, has_analysis, length, created = deck
            print(f"   Deck {deck_id}: {filename}")
            print(f"   Status: {status}, Has Analysis: {has_analysis}, Length: {length}")
            print(f"   Created: {created}")
            print()
        
        # Check visual_analysis_cache table
        print("\n📊 Visual Analysis Cache:")
        try:
            cache_entries = db.execute(text("""
                SELECT pitch_deck_id, created_at, LENGTH(analysis_results) as result_length
                FROM visual_analysis_cache
                ORDER BY created_at DESC
                LIMIT 10
            """)).fetchall()
            
            print(f"Found {len(cache_entries)} cache entries:")
            for entry in cache_entries:
                deck_id, created, length = entry
                print(f"   Deck {deck_id}: Created {created}, Results length: {length}")
                
            # Check if any cache entry has page count
            if cache_entries:
                sample_entry = db.execute(text("""
                    SELECT analysis_results
                    FROM visual_analysis_cache
                    ORDER BY created_at DESC
                    LIMIT 1
                """)).fetchone()
                
                if sample_entry and sample_entry[0]:
                    try:
                        analysis_data = json.loads(sample_entry[0])
                        print(f"\n🔍 Sample cache analysis keys: {list(analysis_data.keys())}")
                        
                        # Look for page count
                        page_fields = ["page_count", "total_pages_analyzed", "total_pages"]
                        for field in page_fields:
                            if field in analysis_data:
                                print(f"   ✅ Found {field}: {analysis_data[field]}")
                                
                        # Check nested structures
                        for key, value in analysis_data.items():
                            if isinstance(value, dict) and any(pf in value for pf in page_fields):
                                for pf in page_fields:
                                    if pf in value:
                                        print(f"   ✅ Found {key}.{pf}: {value[pf]}")
                                        
                    except json.JSONDecodeError:
                        print("   ❌ Cache results not valid JSON")
                        
        except Exception as e:
            print(f"   ❌ Visual analysis cache table doesn't exist or error: {e}")
        
        # Check extraction_experiments table for recent results
        print("\n📊 Recent Extraction Experiments:")
        try:
            experiments = db.execute(text("""
                SELECT id, experiment_name, created_at, 
                       LENGTH(results_json) as results_length,
                       pitch_deck_ids
                FROM extraction_experiments
                ORDER BY created_at DESC
                LIMIT 5
            """)).fetchall()
            
            for exp in experiments:
                exp_id, name, created, length, deck_ids = exp
                print(f"   Experiment {exp_id}: {name}")
                print(f"   Created: {created}, Results length: {length}")
                print(f"   Deck IDs: {deck_ids}")
                print()
                
        except Exception as e:
            print(f"   ❌ Error checking extraction experiments: {e}")
        
        print("=" * 70)
        print("🎯 Summary: Check where visual analysis results are actually stored")
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_visual_analysis_storage()