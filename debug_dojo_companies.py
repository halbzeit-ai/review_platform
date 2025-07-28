#!/usr/bin/env python3
"""
Debug script to check dojo company data in the database
Investigates why funding and classification data isn't showing in GP dashboard
"""

import sys
import os
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'app'))

def debug_dojo_companies():
    """Debug dojo companies to see their funding and classification data"""
    try:
        # Try multiple database connection methods
        db = None
        
        # Method 1: Try SQLite first
        try:
            import sqlite3
            sqlite_path = os.path.join(os.path.dirname(__file__), 'backend', 'sql_app.db')
            if os.path.exists(sqlite_path):
                print(f"✅ Using SQLite database: {sqlite_path}")
                conn = sqlite3.connect(sqlite_path)
                conn.row_factory = sqlite3.Row  # For dict-like access
                cursor = conn.cursor()
                use_sqlite = True
            else:
                raise Exception("SQLite not found")
        except Exception as e:
            print(f"SQLite connection failed: {e}")
            
            # Method 2: Try SessionLocal
            from backend.app.db.database import SessionLocal
            from sqlalchemy import text
            db = SessionLocal()
            use_sqlite = False
        
        print("=== DEBUGGING DOJO COMPANIES DATA ===")
        print()
        
        # Find projects created from dojo experiments
        if use_sqlite:
            # SQLite version - JSON queries are different
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
        else:
            # PostgreSQL version
            query = text("""
                SELECT 
                    id, company_id, project_name, funding_round, funding_sought,
                    company_offering, tags, project_metadata, created_at
                FROM projects 
                WHERE is_test = TRUE 
                AND project_metadata::json->>'created_from_experiment' = 'true'
                ORDER BY created_at DESC
                LIMIT 10
            """)
            projects = db.execute(query).fetchall()
        
        if not projects:
            print("❌ No dojo experiment projects found!")
            return
            
        print(f"✅ Found {len(projects)} dojo experiment projects:")
        print("-" * 80)
        
        for project in projects:
            project_id, company_id, project_name, funding_round, funding_sought, company_offering, tags_raw, metadata_raw, created_at = project
            
            print(f"📄 Project ID: {project_id}")
            print(f"   Company ID: {company_id}")
            print(f"   Project Name: {project_name}")
            print(f"   Funding Round: {funding_round}")
            print(f"   Funding Sought: {funding_sought}")
            print(f"   Created: {created_at}")
            
            # Parse tags
            try:
                tags = json.loads(tags_raw) if tags_raw else []
                print(f"   Tags: {tags}")
            except:
                print(f"   Tags (raw): {tags_raw}")
            
            # Parse metadata
            try:
                metadata = json.loads(metadata_raw) if metadata_raw else {}
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
                print(f"   Raw metadata: {metadata_raw[:200]}...")
            
            print(f"   Company Offering: {company_offering[:100]}...")
            print()
        
        print("=== CHECKING EXPERIMENT RESULTS ===")
        print()
        
        # Check the original experiment data to see what was extracted
        exp_query = text("""
            SELECT id, experiment_name, results_json, classification_results_json,
                   company_name_results_json, funding_amount_results_json
            FROM extraction_experiments 
            WHERE classification_enabled = TRUE
            ORDER BY created_at DESC
            LIMIT 3
        """)
        
        experiments = db.execute(exp_query).fetchall()
        
        for exp in experiments:
            exp_id, exp_name, results_json, classification_json, company_name_json, funding_json = exp
            print(f"🧪 Experiment {exp_id}: {exp_name}")
            
            # Check results
            try:
                results = json.loads(results_json) if results_json else {}
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
                classification_data = json.loads(classification_json) if classification_json else {}
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
                funding_data = json.loads(funding_json) if funding_json else {}
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
            
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if 'db' in locals():
            db.close()

if __name__ == "__main__":
    debug_dojo_companies()