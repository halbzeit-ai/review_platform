#!/usr/bin/env python3
"""
Direct PostgreSQL debug script for visual_analysis_cache - production server
"""

import os
import sys
import json
import psycopg2
from datetime import datetime

def main():
    print("=== VISUAL ANALYSIS CACHE DEBUG (Direct PostgreSQL) ===")
    
    # Production database connection
    # These should match your production database settings
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="review_platform",  # Adjust if different
            user="postgres",  # Adjust if different
            password=os.environ.get("POSTGRES_PASSWORD", "")
        )
        
        cur = conn.cursor()
        
        print("✅ Connected to PostgreSQL database")
        
        print("\n1. Checking visual_analysis_cache for deck 5947...")
        
        cur.execute("""
            SELECT pitch_deck_id, analysis_result_json, vision_model_used, prompt_used, created_at
            FROM visual_analysis_cache 
            WHERE pitch_deck_id = %s
            ORDER BY created_at DESC
        """, (5947,))
        
        results = cur.fetchall()
        
        if results:
            print(f"✅ Found {len(results)} cached entries for deck 5947:")
            for i, row in enumerate(results):
                pitch_deck_id, analysis_json, vision_model, prompt_used, created_at = row
                print(f"\n--- Entry {i+1} ---")
                print(f"Pitch Deck ID: {pitch_deck_id}")
                print(f"Vision Model: {vision_model}")
                print(f"Prompt Used: {prompt_used[:100] if prompt_used else 'None'}...")
                print(f"Created At: {created_at}")
                
                # Try to parse the JSON
                try:
                    if isinstance(analysis_json, str):
                        parsed_json = json.loads(analysis_json)
                    else:
                        parsed_json = analysis_json
                    
                    print(f"JSON Type: {type(parsed_json)}")
                    
                    if isinstance(parsed_json, dict):
                        print(f"JSON Keys: {list(parsed_json.keys())}")
                        
                        if "visual_analysis_results" in parsed_json:
                            visual_results = parsed_json["visual_analysis_results"]
                            print(f"Visual Results Type: {type(visual_results)}")
                            print(f"Visual Results Count: {len(visual_results) if isinstance(visual_results, list) else 'Not a list'}")
                            
                            if isinstance(visual_results, list) and visual_results:
                                print(f"First Result Keys: {list(visual_results[0].keys()) if isinstance(visual_results[0], dict) else 'Not a dict'}")
                                if isinstance(visual_results[0], dict):
                                    first_desc = visual_results[0].get('description', 'No description')
                                    print(f"First Description: {first_desc[:200]}...")
                        else:
                            print("❌ No 'visual_analysis_results' key found")
                    
                    elif isinstance(parsed_json, list):
                        print(f"JSON is a list with {len(parsed_json)} items")
                        if parsed_json and isinstance(parsed_json[0], dict):
                            print(f"First Item Keys: {list(parsed_json[0].keys())}")
                            first_desc = parsed_json[0].get('description', 'No description')
                            print(f"First Description: {first_desc[:200]}...")
                    
                    print(f"Raw JSON Preview: {str(parsed_json)[:500]}...")
                    
                except Exception as e:
                    print(f"❌ Error parsing JSON: {e}")
                    print(f"Raw JSON type: {type(analysis_json)}")
                    print(f"Raw JSON (first 500 chars): {str(analysis_json)[:500]}...")
        else:
            print("❌ No cached entries found for deck 5947")
            
            # Check if there are any entries at all
            print("\n2. Checking for any cached entries...")
            cur.execute("""
                SELECT pitch_deck_id, vision_model_used, created_at
                FROM visual_analysis_cache 
                ORDER BY created_at DESC
                LIMIT 10
            """)
            
            all_results = cur.fetchall()
            if all_results:
                print(f"Found {len(all_results)} total cached entries (showing last 10):")
                for row in all_results:
                    print(f"  Deck ID: {row[0]}, Model: {row[1]}, Created: {row[2]}")
            else:
                print("No cached entries found at all")
        
        print("\n3. Checking projects table for deck 5947...")
        cur.execute("""
            SELECT p.id, p.company_id, p.project_name, p.company_offering, pd.id as doc_id
            FROM projects p
            JOIN project_documents pd ON p.id = pd.project_id
            WHERE pd.id = %s AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE
        """, (5947,))
        
        project_results = cur.fetchall()
        
        if project_results:
            print("✅ Found project data:")
            for row in project_results:
                project_id, company_id, project_name, company_offering, doc_id = row
                print(f"  Project ID: {project_id}")
                print(f"  Company ID: {company_id}")
                print(f"  Project Name: {project_name}")
                print(f"  Document ID: {doc_id}")
                if company_offering:
                    print(f"  Company Offering: {company_offering[:200]}...")
                else:
                    print("  Company Offering: None")
        else:
            print("❌ No project data found for deck 5947")
            
        print("\n4. Checking if deck 5947 exists in any table...")
        
        # Check pitch_decks table
        cur.execute("SELECT id, file_path FROM pitch_decks WHERE id = %s", (5947,))
        pitch_deck_result = cur.fetchone()
        if pitch_deck_result:
            print(f"✅ Found in pitch_decks: ID {pitch_deck_result[0]}, Path: {pitch_deck_result[1]}")
        else:
            print("❌ Not found in pitch_decks table")
            
        # Check project_documents table
        cur.execute("SELECT id, file_name FROM project_documents WHERE id = %s", (5947,))
        project_doc_result = cur.fetchone()
        if project_doc_result:
            print(f"✅ Found in project_documents: ID {project_doc_result[0]}, File: {project_doc_result[1]}")
        else:
            print("❌ Not found in project_documents table")
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        print("Make sure PostgreSQL is running and credentials are correct")
        
        # Try alternative database names
        print("\nTrying alternative database configurations...")
        for db_name in ["halbzeit", "review_platform_db", "postgres"]:
            try:
                print(f"Trying database: {db_name}")
                test_conn = psycopg2.connect(
                    host="localhost",
                    database=db_name,
                    user="postgres",
                    password=os.environ.get("POSTGRES_PASSWORD", "")
                )
                test_conn.close()
                print(f"✅ Connection successful with database: {db_name}")
                break
            except Exception as e2:
                print(f"❌ Failed with {db_name}: {e2}")
    
    except Exception as e:
        print(f"❌ General error: {e}")
    
    finally:
        if 'conn' in locals():
            conn.close()
    
    print("\n=== DEBUG COMPLETE ===")
    print("If you see database connection errors, please check:")
    print("1. PostgreSQL service is running")
    print("2. Database name is correct")
    print("3. POSTGRES_PASSWORD environment variable is set")

if __name__ == "__main__":
    main()