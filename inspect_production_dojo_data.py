#!/usr/bin/env python3
"""
Production Database Inspector for Dojo Company Data
Investigates why funding and classification data from dojo experiments isn't showing in GP dashboard

This script should be run on the production server to inspect the actual PostgreSQL database.
"""

import sys
import os
import json
from datetime import datetime

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'app'))

def inspect_production_dojo_data():
    """Inspect production database to debug funding and classification display issues"""
    try:
        from backend.app.db.database import SessionLocal
        from sqlalchemy import text
        
        # Get database session
        db = SessionLocal()
        
        print("=== PRODUCTION DOJO COMPANIES DATA INSPECTION ===")
        print(f"Timestamp: {datetime.now()}")
        print()
        
        # Step 1: Find recent dojo experiment projects
        print("🔍 STEP 1: Finding recent dojo experiment projects...")
        
        project_query = text("""
            SELECT 
                id, company_id, project_name, funding_round, funding_sought,
                company_offering, tags, project_metadata, created_at
            FROM projects 
            WHERE is_test = TRUE 
            AND project_metadata::json->>'created_from_experiment' = 'true'
            ORDER BY created_at DESC
            LIMIT 15
        """)
        
        projects = db.execute(project_query).fetchall()
        
        if not projects:
            print("❌ No dojo experiment projects found!")
            
            # Check if there are any test projects at all
            test_count_query = text("SELECT COUNT(*) FROM projects WHERE is_test = TRUE")
            test_count = db.execute(test_count_query).fetchone()[0]
            print(f"   Total test projects: {test_count}")
            
            if test_count > 0:
                # Show some examples
                example_query = text("""
                    SELECT company_id, project_name, project_metadata 
                    FROM projects WHERE is_test = TRUE 
                    ORDER BY created_at DESC LIMIT 5
                """)
                examples = db.execute(example_query).fetchall()
                print("   Recent test projects:")
                for ex in examples:
                    metadata = json.loads(ex[2]) if ex[2] else {}
                    print(f"     - {ex[0]}: metadata keys = {list(metadata.keys())}")
            
            db.close()
            return
            
        print(f"✅ Found {len(projects)} dojo experiment projects")
        
        # Step 2: Analyze each project's data structure
        print("\n🔍 STEP 2: Analyzing project data structure...")
        print("-" * 80)
        
        funding_issues = []
        classification_issues = []
        
        for i, project in enumerate(projects[:5]):  # Analyze first 5 in detail
            project_id, company_id, project_name, funding_round, funding_sought, company_offering, tags_raw, metadata_raw, created_at = project
            
            print(f"\n📄 Project {i+1}: {company_id}")
            print(f"   ID: {project_id}")
            print(f"   Name: {project_name}")
            print(f"   Created: {created_at}")
            
            # Analyze funding data
            print(f"   🏦 FUNDING ANALYSIS:")
            print(f"       funding_round: '{funding_round}'")
            print(f"       funding_sought: '{funding_sought}'")
            
            if not funding_sought or funding_sought in ['TBD', 'N/A', '']:
                funding_issues.append({
                    'project_id': project_id,
                    'company_id': company_id,
                    'funding_sought': funding_sought
                })
                print(f"       ❌ ISSUE: funding_sought is '{funding_sought}'")
            else:
                print(f"       ✅ OK: Has funding data")
            
            # Analyze classification data
            print(f"   🏷️  CLASSIFICATION ANALYSIS:")
            try:
                metadata = json.loads(metadata_raw) if metadata_raw else {}
                classification = metadata.get('classification', {})
                
                print(f"       metadata keys: {list(metadata.keys())}")
                print(f"       classification: {classification}")
                
                primary_sector = classification.get('primary_sector')
                print(f"       primary_sector: '{primary_sector}'")
                
                if not primary_sector or primary_sector in ['N/A', '']:
                    classification_issues.append({
                        'project_id': project_id,
                        'company_id': company_id,
                        'classification': classification
                    })
                    print(f"       ❌ ISSUE: No primary_sector found")
                else:
                    print(f"       ✅ OK: Has classification '{primary_sector}'")
                    
                # Check experiment source
                experiment_id = metadata.get('experiment_id')
                source_deck_id = metadata.get('source_deck_id')
                print(f"       experiment_id: {experiment_id}")
                print(f"       source_deck_id: {source_deck_id}")
                
            except Exception as e:
                print(f"       ❌ METADATA PARSE ERROR: {e}")
                classification_issues.append({
                    'project_id': project_id,
                    'company_id': company_id,
                    'error': str(e)
                })
            
            # Analyze tags
            try:
                tags = json.loads(tags_raw) if tags_raw else []
                print(f"   🏷️  Tags: {tags}")
            except:
                print(f"   🏷️  Tags (raw): {tags_raw}")
        
        # Step 3: Investigate experiment data
        print(f"\n🔍 STEP 3: Investigating source experiment data...")
        
        # Get recent experiments that have classification enabled
        exp_query = text("""
            SELECT id, experiment_name, results_json, classification_results_json,
                   company_name_results_json, funding_amount_results_json, created_at
            FROM extraction_experiments 
            WHERE classification_enabled = TRUE
            ORDER BY created_at DESC
            LIMIT 5
        """)
        
        experiments = db.execute(exp_query).fetchall()
        
        if not experiments:
            print("❌ No classification-enabled experiments found!")
        else:
            print(f"✅ Found {len(experiments)} recent classification experiments")
            
            for exp in experiments[:2]:  # Analyze first 2 in detail
                exp_id, exp_name, results_json, classification_json, company_name_json, funding_json, created_at = exp
                
                print(f"\n🧪 Experiment {exp_id}: {exp_name}")
                print(f"   Created: {created_at}")
                
                # Check extraction results
                try:
                    results = json.loads(results_json) if results_json else {}
                    if results.get('results'):
                        extraction_results = results['results']
                        print(f"   📊 Extraction Results: {len(extraction_results)} decks")
                        
                        # Sample first result
                        if extraction_results:
                            first_result = extraction_results[0]
                            print(f"       Sample deck_id: {first_result.get('deck_id')}")
                            print(f"       Sample funding_extraction: '{first_result.get('funding_extraction', 'MISSING')}'")
                            print(f"       Sample offering_extraction: '{first_result.get('offering_extraction', 'MISSING')[:50]}...'")
                            
                            # Count how many have funding data
                            funding_count = sum(1 for r in extraction_results if r.get('funding_extraction') and r.get('funding_extraction') not in ['TBD', '', 'N/A'])
                            print(f"       Decks with funding data: {funding_count}/{len(extraction_results)}")
                    else:
                        print(f"   ❌ No extraction results found")
                except Exception as e:
                    print(f"   ❌ Results parse error: {e}")
                
                # Check classification results
                try:
                    classification_data = json.loads(classification_json) if classification_json else {}
                    if classification_data.get('classification_by_deck'):
                        classifications = classification_data['classification_by_deck']
                        print(f"   🏷️  Classification Results: {len(classifications)} decks")
                        
                        # Sample first classification
                        if classifications:
                            first_deck_id = next(iter(classifications.keys()))
                            first_classification = classifications[first_deck_id]
                            print(f"       Sample deck {first_deck_id}: {first_classification}")
                            
                            # Count valid classifications
                            valid_classifications = sum(1 for c in classifications.values() if c.get('primary_sector'))
                            print(f"       Valid classifications: {valid_classifications}/{len(classifications)}")
                    else:
                        print(f"   ❌ No classification results found")
                except Exception as e:
                    print(f"   ❌ Classification parse error: {e}")
                
                # Check funding amount results
                try:
                    funding_data = json.loads(funding_json) if funding_json else {}
                    if funding_data.get('funding_amount_results'):
                        funding_results = funding_data['funding_amount_results']
                        print(f"   💰 Funding Amount Results: {len(funding_results)} decks")
                        
                        if funding_results:
                            first_funding = funding_results[0]
                            print(f"       Sample: deck {first_funding.get('deck_id')} = '{first_funding.get('funding_amount', 'MISSING')}'")
                            
                            # Count valid funding amounts
                            valid_funding = sum(1 for f in funding_results if f.get('funding_amount') and f.get('funding_amount') not in ['TBD', '', 'N/A', 'Not specified'])
                            print(f"       Valid funding amounts: {valid_funding}/{len(funding_results)}")
                    else:
                        print(f"   ❌ No funding amount results found")
                except Exception as e:
                    print(f"   ❌ Funding parse error: {e}")
        
        # Step 4: Summary and recommendations
        print(f"\n📋 STEP 4: SUMMARY AND RECOMMENDATIONS")
        print("=" * 60)
        
        if funding_issues:
            print(f"🏦 FUNDING ISSUES FOUND: {len(funding_issues)}")
            for issue in funding_issues[:3]:
                print(f"   - {issue['company_id']}: funding_sought = '{issue['funding_sought']}'")
        else:
            print(f"✅ No funding issues found in analyzed projects")
        
        if classification_issues:
            print(f"🏷️  CLASSIFICATION ISSUES FOUND: {len(classification_issues)}")
            for issue in classification_issues[:3]:
                if 'error' in issue:
                    print(f"   - {issue['company_id']}: Parse error")
                else:
                    print(f"   - {issue['company_id']}: classification = {issue['classification']}")
        else:
            print(f"✅ No classification issues found in analyzed projects")
        
        print(f"\n💡 NEXT STEPS:")
        print(f"1. If funding_sought contains 'TBD', check if funding_extraction in experiments has actual values")
        print(f"2. If classification.primary_sector is missing, check if classification_by_deck has valid data")
        print(f"3. Verify the add-companies endpoint is properly mapping experiment data to project fields")
        
        db.close()
        
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    inspect_production_dojo_data()