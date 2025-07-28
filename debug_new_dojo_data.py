#!/usr/bin/env python3
"""
Debug script to check the newly created dojo projects after the fix
"""

import sys
import os
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'app'))

def debug_new_dojo_data():
    """Debug the newly created dojo projects to see if classification data is properly stored"""
    try:
        from backend.app.db.database import SessionLocal
        from sqlalchemy import text
        
        # Get database session
        db = SessionLocal()
        
        print("=== DEBUGGING NEW DOJO PROJECTS DATA ===")
        print(f"Timestamp: {datetime.now()}")
        print()
        
        # Find the most recent dojo experiment projects
        project_query = text("""
            SELECT 
                id, company_id, project_name, funding_sought,
                project_metadata, created_at
            FROM projects 
            WHERE is_test = TRUE 
            AND project_metadata::json->>'created_from_experiment' = 'true'
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        projects = db.execute(project_query).fetchall()
        
        if not projects:
            print("❌ No dojo experiment projects found!")
            db.close()
            return
            
        print(f"✅ Found {len(projects)} recent dojo experiment projects")
        print("-" * 80)
        
        for i, project in enumerate(projects):
            project_id, company_id, project_name, funding_sought, metadata_raw, created_at = project
            
            print(f"\n📄 Project {i+1}: {company_id}")
            print(f"   ID: {project_id}")
            print(f"   Name: {project_name}")
            print(f"   Created: {created_at}")
            print(f"   🏦 Funding Sought: '{funding_sought}'")
            
            # Check if funding is fixed
            if funding_sought and funding_sought not in ['TBD', 'N/A', '']:
                print(f"       ✅ FUNDING FIX WORKED: Has actual funding data")
            else:
                print(f"       ❌ FUNDING ISSUE: Still shows '{funding_sought}'")
            
            # Analyze classification metadata
            print(f"   🏷️  CLASSIFICATION ANALYSIS:")
            try:
                if isinstance(metadata_raw, dict):
                    metadata = metadata_raw
                    print(f"       ✅ Metadata is already a dict (PostgreSQL)")
                else:
                    metadata = json.loads(metadata_raw) if metadata_raw else {}
                    print(f"       ℹ️  Metadata was JSON string, parsed successfully")
                
                print(f"       metadata keys: {list(metadata.keys())}")
                
                classification = metadata.get('classification', {})
                print(f"       classification: {classification}")
                
                if classification:
                    primary_sector = classification.get('primary_sector')
                    print(f"       primary_sector: '{primary_sector}'")
                    
                    if primary_sector and primary_sector != 'N/A':
                        print(f"       ✅ CLASSIFICATION FIX WORKED: Has '{primary_sector}'")
                    else:
                        print(f"       ❌ CLASSIFICATION ISSUE: primary_sector is '{primary_sector}'")
                else:
                    print(f"       ❌ CLASSIFICATION ISSUE: No classification object found")
                    
                # Check experiment source info
                experiment_id = metadata.get('experiment_id')
                source_deck_id = metadata.get('source_deck_id')
                print(f"       experiment_id: {experiment_id}")
                print(f"       source_deck_id: {source_deck_id}")
                
            except Exception as e:
                print(f"       ❌ METADATA PARSE ERROR: {e}")
                print(f"       Raw metadata type: {type(metadata_raw)}")
                print(f"       Raw metadata: {str(metadata_raw)[:200]}...")
        
        # Also check the source experiment data
        print(f"\n🔍 CHECKING SOURCE EXPERIMENT DATA...")
        
        # Get the experiment that was just used
        exp_query = text("""
            SELECT id, experiment_name, classification_results_json, funding_amount_results_json
            FROM extraction_experiments 
            WHERE id = 21
        """)
        
        experiment = db.execute(exp_query).fetchone()
        
        if experiment:
            exp_id, exp_name, classification_json, funding_json = experiment
            print(f"\n🧪 Experiment {exp_id}: {exp_name}")
            
            # Check classification data
            try:
                classification_data = json.loads(classification_json) if classification_json else {}
                if classification_data.get('classification_by_deck'):
                    classifications = classification_data['classification_by_deck']
                    print(f"   🏷️  Classification Results Available: {len(classifications)} decks")
                    
                    # Show first few classifications
                    for i, (deck_id, classification) in enumerate(list(classifications.items())[:3]):
                        print(f"       Deck {deck_id}: {classification.get('primary_sector', 'N/A')}")
                else:
                    print(f"   ❌ No classification_by_deck found in experiment")
            except Exception as e:
                print(f"   ❌ Classification parse error: {e}")
            
            # Check funding data
            try:
                funding_data = json.loads(funding_json) if funding_json else {}
                if funding_data.get('funding_amount_results'):
                    funding_results = funding_data['funding_amount_results']
                    print(f"   💰 Funding Results Available: {len(funding_results)} decks")
                    
                    # Show first few funding amounts
                    for i, funding_result in enumerate(funding_results[:3]):
                        deck_id = funding_result.get('deck_id')
                        amount = funding_result.get('funding_amount')
                        print(f"       Deck {deck_id}: {amount}")
                else:
                    print(f"   ❌ No funding_amount_results found in experiment")
            except Exception as e:
                print(f"   ❌ Funding parse error: {e}")
        else:
            print(f"   ❌ Experiment 21 not found")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_new_dojo_data()