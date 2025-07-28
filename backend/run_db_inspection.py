#!/usr/bin/env python3
"""
Database inspection script to run various database queries via FastAPI database connection
"""

import sys
import os
from sqlalchemy import text
from typing import Dict, Any, List

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.database import SessionLocal

def inspect_experiment_fields(experiment_id: int = None):
    """Inspect experiment table structure and specific experiment data"""
    db = SessionLocal()
    
    try:
        print("🔍 Inspecting experiment table structure...")
        
        # Get table structure
        structure_query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'extraction_experiments'
        ORDER BY ordinal_position;
        """
        
        result = db.execute(text(structure_query))
        columns = result.fetchall()
        
        print("\n📋 Extraction Experiments Table Structure:")
        print("-" * 80)
        for col in columns:
            print(f"  {col.column_name:<30} {col.data_type:<15} {'NULL' if col.is_nullable == 'YES' else 'NOT NULL':<10} {col.column_default or ''}")
        
        if experiment_id:
            print(f"\n🔎 Inspecting experiment ID {experiment_id}:")
            print("-" * 80)
            
            # Get specific experiment data
            exp_query = "SELECT * FROM extraction_experiments WHERE id = :exp_id"
            result = db.execute(text(exp_query), {"exp_id": experiment_id})
            experiment = result.fetchone()
            
            if experiment:
                # Convert to dict for easier inspection
                exp_dict = dict(experiment._mapping)
                for key, value in exp_dict.items():
                    print(f"  {key:<30}: {value}")
            else:
                print(f"  ❌ Experiment {experiment_id} not found")
        
        return True
        
    except Exception as e:
        print(f"❌ Inspection failed: {e}")
        return False
        
    finally:
        db.close()

def inspect_api_endpoints():
    """List all available API endpoints by inspecting the backend route structure"""
    print("🌐 Available API endpoints pattern based on backend structure:")
    print("-" * 80)
    
    endpoints = [
        "GET    /api/dojo/extraction-test/experiments",
        "GET    /api/dojo/extraction-test/experiments/{experiment_id}",
        "POST   /api/dojo/extraction-test/run-offering-extraction",
        "POST   /api/dojo/extraction-test/run-classification", 
        "POST   /api/dojo/extraction-test/run-company-name-extraction",
        "POST   /api/dojo/extraction-test/run-funding-amount-extraction",
        "POST   /api/dojo/extraction-test/run-visual-analysis",
        "POST   /api/dojo/extraction-test/run-deck-date-extraction",
        "POST   /api/dojo-experiments/add-companies",
        "GET    /api/dojo/files",
        "POST   /api/pipeline/process"
    ]
    
    for endpoint in endpoints:
        print(f"  {endpoint}")
    
    print(f"\n❗ Missing endpoint needed:")
    print(f"  POST   /api/dojo/extraction-test/run-template-processing")

def inspect_experiment_data(experiment_id: int):
    """Detailed inspection of experiment data for debugging"""
    db = SessionLocal()
    
    try:
        print(f"🧐 Detailed inspection of experiment {experiment_id}:")
        print("-" * 80)
        
        # Get experiment with all fields
        query = "SELECT * FROM extraction_experiments WHERE id = :exp_id"
        result = db.execute(text(query), {"exp_id": experiment_id})
        experiment = result.fetchone()
        
        if not experiment:
            print(f"❌ Experiment {experiment_id} not found")
            return False
        
        exp_dict = dict(experiment._mapping)
        
        # Focus on completion timestamps and extraction fields
        important_fields = [
            'id', 'experiment_name', 'created_at', 'successful_extractions',
            'company_name_completed_at', 'funding_amount_completed_at', 
            'classification_completed_at', 'classification_enabled',
            'deck_ids', 'pitch_deck_ids'
        ]
        
        print("🎯 Key fields for boolean column logic:")
        for field in important_fields:
            value = exp_dict.get(field, 'FIELD_NOT_FOUND')
            print(f"  {field:<30}: {value}")
        
        # Check obligatory extractions logic
        successful_extractions = exp_dict.get('successful_extractions', 0)
        company_name_completed = bool(exp_dict.get('company_name_completed_at'))
        funding_amount_completed = bool(exp_dict.get('funding_amount_completed_at'))
        
        obligatory_result = (successful_extractions > 0) and company_name_completed and funding_amount_completed
        
        print(f"\n📊 Boolean column calculations:")
        print(f"  successful_extractions > 0    : {successful_extractions > 0}")
        print(f"  company_name_completed_at     : {company_name_completed}")
        print(f"  funding_amount_completed_at   : {funding_amount_completed}")
        print(f"  Obligatory Extractions result : {obligatory_result}")
        
        # Check templates processed logic
        classification_enabled = exp_dict.get('classification_enabled', False)
        classification_completed = bool(exp_dict.get('classification_completed_at'))
        templates_result = classification_enabled and classification_completed
        
        print(f"  classification_enabled        : {classification_enabled}")
        print(f"  classification_completed_at   : {classification_completed}")
        print(f"  Templates Processed result    : {templates_result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Inspection failed: {e}")
        return False
        
    finally:
        db.close()

def run_custom_query(query: str):
    """Run a custom SQL query"""
    db = SessionLocal()
    
    try:
        print(f"🔧 Running custom query:")
        print(f"   {query}")
        print("-" * 80)
        
        result = db.execute(text(query))
        
        if query.strip().upper().startswith('SELECT'):
            rows = result.fetchall()
            if rows:
                # Print column headers
                columns = result.keys()
                header = " | ".join(f"{col:<20}" for col in columns)
                print(header)
                print("-" * len(header))
                
                # Print rows
                for row in rows:
                    row_data = " | ".join(f"{str(val):<20}" for val in row)
                    print(row_data)
            else:
                print("No results found")
        else:
            print(f"Query executed successfully. Rows affected: {result.rowcount}")
            db.commit()
        
        return True
        
    except Exception as e:
        print(f"❌ Query failed: {e}")
        return False
        
    finally:
        db.close()

def main():
    """Main inspection function with argument parsing"""
    if len(sys.argv) < 2:
        print("Usage: python run_db_inspection.py <inspection_type> [args...]")
        print("")
        print("Available inspection types:")
        print("  fields [experiment_id]     - Inspect experiment table structure and optionally specific experiment")
        print("  endpoints                  - List available API endpoints")
        print("  experiment <experiment_id> - Detailed inspection of specific experiment")
        print("  query '<sql_query>'        - Run custom SQL query")
        print("")
        print("Examples:")
        print("  python run_db_inspection.py fields")
        print("  python run_db_inspection.py fields 21")
        print("  python run_db_inspection.py experiment 21")
        print("  python run_db_inspection.py endpoints")
        print("  python run_db_inspection.py query 'SELECT COUNT(*) FROM extraction_experiments'")
        sys.exit(1)
    
    inspection_type = sys.argv[1].lower()
    
    if inspection_type == "fields":
        experiment_id = int(sys.argv[2]) if len(sys.argv) > 2 else None
        success = inspect_experiment_fields(experiment_id)
        
    elif inspection_type == "endpoints":
        inspect_api_endpoints()
        success = True
        
    elif inspection_type == "experiment":
        if len(sys.argv) < 3:
            print("Error: experiment inspection requires experiment_id")
            sys.exit(1)
        experiment_id = int(sys.argv[2])
        success = inspect_experiment_data(experiment_id)
        
    elif inspection_type == "query":
        if len(sys.argv) < 3:
            print("Error: query inspection requires SQL query")
            sys.exit(1)
        query = sys.argv[2]
        success = run_custom_query(query)
        
    else:
        print(f"Error: Unknown inspection type '{inspection_type}'")
        sys.exit(1)
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()