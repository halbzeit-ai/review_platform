#!/usr/bin/env python3
"""
Simple debug script to check dojo company data in SQLite database
"""

import sqlite3
import json
import os

def debug_dojo_companies():
    """Debug dojo companies to see their funding and classification data"""
    
    # Connect to SQLite database
    sqlite_path = os.path.join(os.path.dirname(__file__), 'backend', 'sql_app.db')
    
    if not os.path.exists(sqlite_path):
        print(f"❌ SQLite database not found at: {sqlite_path}")
        return
    
    print(f"✅ Using SQLite database: {sqlite_path}")
    
    conn = sqlite3.connect(sqlite_path)
    conn.row_factory = sqlite3.Row  # For dict-like access
    cursor = conn.cursor()
    
    print("=== DEBUGGING DOJO COMPANIES DATA ===")
    print()
    
    # Find projects created from dojo experiments
    query = """
        SELECT 
            id, company_id, project_name, funding_round, funding_sought,
            company_offering, tags, project_metadata, created_at
        FROM projects 
        WHERE is_test = 1 
        AND json_extract(project_metadata, '$.created_from_experiment') = 'true'
        ORDER BY created_at DESC
        LIMIT 10
    """
    
    cursor.execute(query)
    projects = cursor.fetchall()
    
    if not projects:
        print("❌ No dojo experiment projects found!")
        
        # Check if there are any test projects at all
        cursor.execute("SELECT COUNT(*) FROM projects WHERE is_test = 1")
        test_count = cursor.fetchone()[0]
        print(f"   Total test projects: {test_count}")
        
        if test_count > 0:
            # Show some examples
            cursor.execute("SELECT company_id, project_name, project_metadata FROM projects WHERE is_test = 1 LIMIT 3")
            examples = cursor.fetchall()
            print("   Example test projects:")
            for ex in examples:
                metadata = ex[2] or '{}'
                print(f"     - {ex[0]}: metadata keys = {list(json.loads(metadata).keys()) if metadata != '{}' else []}")
        
        conn.close()
        return
        
    print(f"✅ Found {len(projects)} dojo experiment projects:")
    print("-" * 80)
    
    for project in projects:
        print(f"📄 Project ID: {project['id']}")
        print(f"   Company ID: {project['company_id']}")
        print(f"   Project Name: {project['project_name']}")
        print(f"   Funding Round: {project['funding_round']}")
        print(f"   Funding Sought: {project['funding_sought']}")
        print(f"   Created: {project['created_at']}")
        
        # Parse tags
        try:
            tags = json.loads(project['tags']) if project['tags'] else []
            print(f"   Tags: {tags}")
        except:
            print(f"   Tags (raw): {project['tags']}")
        
        # Parse metadata
        try:
            metadata = json.loads(project['project_metadata']) if project['project_metadata'] else {}
            print(f"   Experiment ID: {metadata.get('experiment_id')}")
            print(f"   Original Filename: {metadata.get('original_filename')}")
            
            # Check classification info
            classification = metadata.get('classification', {})
            if classification:
                print(f"   Classification: {classification}")
                print(f"     - Primary Sector: {classification.get('primary_sector')}")
            else:
                print(f"   Classification: None found")
                
        except Exception as e:
            print(f"   Metadata parse error: {e}")
            print(f"   Raw metadata: {project['project_metadata'][:200] if project['project_metadata'] else 'None'}...")
        
        print(f"   Company Offering: {project['company_offering'][:100] if project['company_offering'] else 'None'}...")
        print()
    
    print("=== CHECKING EXTRACTION EXPERIMENTS ===")
    print()
    
    # Check the original experiment data
    exp_query = """
        SELECT id, experiment_name, results_json, classification_results_json,
               company_name_results_json, funding_amount_results_json
        FROM extraction_experiments 
        WHERE classification_enabled = 1
        ORDER BY created_at DESC
        LIMIT 3
    """
    
    cursor.execute(exp_query)
    experiments = cursor.fetchall()
    
    if not experiments:
        print("❌ No classification-enabled experiments found!")
        conn.close()
        return
    
    for exp in experiments:
        print(f"🧪 Experiment {exp['id']}: {exp['experiment_name']}")
        
        # Check results
        try:
            results = json.loads(exp['results_json']) if exp['results_json'] else {}
            if results.get('results'):
                print(f"   Extraction results: {len(results['results'])} decks")
                
                # Show first result as example
                first_result = results['results'][0] if results['results'] else {}
                print(f"   Example funding extraction: {first_result.get('funding_extraction', 'N/A')}")
                print(f"   Example offering: {first_result.get('offering_extraction', 'N/A')[:50]}...")
        except Exception as e:
            print(f"   Results parse error: {e}")
        
        # Check classification data
        try:
            classification_data = json.loads(exp['classification_results_json']) if exp['classification_results_json'] else {}
            if classification_data.get('classification_by_deck'):
                classifications = classification_data['classification_by_deck']
                print(f"   Classifications: {len(classifications)} decks")
                
                # Show first classification as example
                first_deck_id = next(iter(classifications.keys())) if classifications else None
                if first_deck_id:
                    first_classification = classifications[first_deck_id]
                    print(f"   Example classification: {first_classification}")
        except Exception as e:
            print(f"   Classification parse error: {e}")
        
        # Check funding amount data
        try:
            funding_data = json.loads(exp['funding_amount_results_json']) if exp['funding_amount_results_json'] else {}
            if funding_data.get('funding_amount_results'):
                funding_results = funding_data['funding_amount_results']
                print(f"   Funding results: {len(funding_results)} decks")
                
                # Show first funding result as example
                if funding_results:
                    first_funding = funding_results[0]
                    print(f"   Example funding: {first_funding.get('funding_amount', 'N/A')}")
        except Exception as e:
            print(f"   Funding parse error: {e}")
        
        print()
    
    conn.close()

if __name__ == "__main__":
    debug_dojo_companies()