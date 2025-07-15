#!/usr/bin/env python3
"""
Quick script to manually check and update results for completed jobs
"""

import os
import json
import sys
sys.path.append('/home/ramin/halbzeit-ai/review_platform/backend')

from app.services.file_based_processing import file_based_gpu_service
from app.db.database import SessionLocal
from app.db.models import PitchDeck

def check_and_update_results():
    """Check for completed results and update database"""
    
    # Check what result files exist
    results_dir = "/mnt/shared/results"
    if not os.path.exists(results_dir):
        print(f"Results directory {results_dir} does not exist")
        return
    
    result_files = [f for f in os.listdir(results_dir) if f.endswith('_results.json')]
    print(f"Found {len(result_files)} result files: {result_files}")
    
    for result_file in result_files:
        # Extract job_id from filename
        job_id = result_file.replace('_results.json', '')
        print(f"\nProcessing result file: {result_file}")
        print(f"Job ID: {job_id}")
        
        # Try to extract pitch_deck_id from job_id
        if job_id.startswith('job_'):
            parts = job_id.split('_')
            if len(parts) >= 2:
                try:
                    pitch_deck_id = int(parts[1])
                    print(f"Pitch deck ID: {pitch_deck_id}")
                    
                    # Read results
                    result_path = os.path.join(results_dir, result_file)
                    with open(result_path, 'r') as f:
                        results = json.load(f)
                    
                    print(f"Results summary: {results.get('summary', 'No summary')}")
                    
                    # Update database
                    db = SessionLocal()
                    pitch_deck = db.query(PitchDeck).filter(PitchDeck.id == pitch_deck_id).first()
                    if pitch_deck:
                        pitch_deck.processing_status = "completed"
                        pitch_deck.ai_analysis_results = json.dumps(results)
                        db.commit()
                        print(f"Updated pitch deck {pitch_deck_id} status to completed")
                    else:
                        print(f"Pitch deck {pitch_deck_id} not found in database")
                    db.close()
                    
                except ValueError:
                    print(f"Could not extract pitch deck ID from job_id: {job_id}")
    
    print("\n=== Database Status ===")
    db = SessionLocal()
    pitch_decks = db.query(PitchDeck).all()
    for deck in pitch_decks:
        print(f"Pitch Deck {deck.id}: {deck.file_name} - Status: {deck.processing_status}")
    db.close()

if __name__ == "__main__":
    check_and_update_results()