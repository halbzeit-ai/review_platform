#\!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '.')
from app.db.database import get_db
from sqlalchemy import text
import json

def add_classification_to_deck_150():
    db = next(get_db())
    
    # Classification result for deck 150
    classification_result = {
        "deck_id": 150,
        "classification_result": {
            "primary_sector": "consumer_health",
            "subcategory": "Preventive Care Platforms",
            "confidence_score": 0.9,
            "reasoning": "The company's offering of 'personalized guidance and support for families navigating early childhood development' directly aligns with the focus of Consumer Health & Wellness. Specifically, it falls under Preventive Care Platforms because it aims to proactively support healthy development and address potential challenges early on.",
            "secondary_sector": "Digital Therapeutics & Mental Health",
            "keywords_matched": ["personalized guidance","early childhood development","families","support","development"]
        }
    }
    
    try:
        # Find experiments with deck 150
        experiments = db.execute(text("""
            SELECT id, experiment_name, classification_results_json, classification_enabled
            FROM extraction_experiments 
            WHERE pitch_deck_ids::text LIKE '%150%'
            ORDER BY id DESC
        """)).fetchall()
        
        print(f"Found {len(experiments)} experiments containing deck 150")
        
        for exp in experiments:
            exp_id = exp[0]
            exp_name = exp[1]
            existing_results = exp[2]
            classification_enabled = exp[3]
            
            print(f"\nExperiment {exp_id}: {exp_name}")
            print(f"Classification enabled: {classification_enabled}")
            
            # Parse existing classification results
            if existing_results:
                try:
                    results_list = json.loads(existing_results)
                    if not isinstance(results_list, list):
                        results_list = []
                except:
                    results_list = []
            else:
                results_list = []
            
            # Check if deck 150 already has classification
            has_deck_150 = any(r.get('deck_id') == 150 for r in results_list)
            
            if has_deck_150:
                print(f"Deck 150 already has classification in experiment {exp_id}")
                # Update existing
                for i, r in enumerate(results_list):
                    if r.get('deck_id') == 150:
                        results_list[i] = classification_result
                        break
            else:
                print(f"Adding classification for deck 150 to experiment {exp_id}")
                results_list.append(classification_result)
            
            # Update the experiment
            db.execute(text("""
                UPDATE extraction_experiments 
                SET classification_results_json = :results,
                    classification_enabled = true,
                    classification_completed_at = NOW()
                WHERE id = :exp_id
            """), {
                "results": json.dumps(results_list),
                "exp_id": exp_id
            })
            
            print(f"Updated experiment {exp_id} with classification for deck 150")
        
        db.commit()
        print("\nSuccess\! Classification data added for deck 150")
        
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    add_classification_to_deck_150()
