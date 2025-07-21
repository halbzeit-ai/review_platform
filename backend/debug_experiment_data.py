#!/usr/bin/env python3
"""
Debug Experiment Classification Data
Check what's actually stored in the database for experiment 11
"""

import sys
import json
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent))

def check_experiment_data():
    """Check what data is stored for experiment 11"""
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        # Get experiment 11 data
        experiment = db.execute(text("""
            SELECT id, experiment_name, classification_enabled, classification_results_json, 
                   classification_model_used, classification_completed_at
            FROM extraction_experiments 
            WHERE id = 11
        """)).fetchone()
        
        if not experiment:
            print("❌ Experiment 11 not found")
            return
            
        print("🔍 Experiment 11 Data:")
        print(f"ID: {experiment[0]}")
        print(f"Name: {experiment[1]}")
        print(f"Classification Enabled: {experiment[2]}")
        print(f"Model Used: {experiment[4]}")
        print(f"Completed At: {experiment[5]}")
        print()
        
        # Parse classification results
        if experiment[3]:
            print("📊 Classification Results JSON:")
            try:
                classification_data = json.loads(experiment[3])
                print(f"Keys: {list(classification_data.keys())}")
                
                if "statistics" in classification_data:
                    stats = classification_data["statistics"]
                    print(f"Statistics: {stats}")
                    
                if "classification_by_deck" in classification_data:
                    by_deck = classification_data["classification_by_deck"]
                    print(f"Classification by deck: {len(by_deck)} entries")
                    for deck_id, data in list(by_deck.items())[:3]:  # Show first 3
                        print(f"  Deck {deck_id}: {data.get('primary_sector', 'None')} ({data.get('confidence_score', 0):.2f})")
                        
            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON: {e}")
                print(f"Raw data: {experiment[3][:200]}...")
        else:
            print("❌ No classification results JSON")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_experiment_data()