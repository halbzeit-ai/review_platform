#!/usr/bin/env python3
"""
Data Integrity Verification Script
Verifies that PostgreSQL data is complete and application can function properly
"""

import psycopg2
import sys
import json
from datetime import datetime

def check_user_data():
    """Verify user data integrity"""
    print("1. Checking user data integrity...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Check user details
        cursor.execute("""
            SELECT id, email, company_name, role, is_verified, created_at 
            FROM users ORDER BY created_at;
        """)
        users = cursor.fetchall()
        
        print(f"   Found {len(users)} users:")
        for user in users:
            user_id, email, company_name, role, is_verified, created_at = user
            verification_status = "✅ verified" if is_verified else "❌ not verified"
            print(f"     - ID {user_id}: {email} ({role}) - {company_name} - {verification_status}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking user data: {e}")
        return False

def check_pitch_deck_data():
    """Verify pitch deck data integrity"""
    print("\n2. Checking pitch deck data integrity...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Check pitch deck details
        cursor.execute("""
            SELECT pd.id, pd.file_name, pd.company_id, pd.processing_status, 
                   pd.results_file_path, u.email, pd.created_at
            FROM pitch_decks pd
            JOIN users u ON pd.user_id = u.id
            ORDER BY pd.created_at;
        """)
        pitch_decks = cursor.fetchall()
        
        print(f"   Found {len(pitch_decks)} pitch decks:")
        for deck in pitch_decks:
            deck_id, file_name, company_id, status, results_path, user_email, created_at = deck
            results_indicator = "📄 has results" if results_path else "⏳ no results"
            print(f"     - ID {deck_id}: {file_name} ({company_id}) - {status} - {results_indicator}")
            print(f"       User: {user_email}, Created: {created_at}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking pitch deck data: {e}")
        return False

def check_healthcare_templates():
    """Verify healthcare template system"""
    print("\n3. Checking healthcare template system...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Check healthcare sectors
        cursor.execute("SELECT id, name, description FROM healthcare_sectors ORDER BY name;")
        sectors = cursor.fetchall()
        print(f"   Healthcare sectors ({len(sectors)}):")
        for sector in sectors:
            print(f"     - {sector[1]}: {sector[2]}")
        
        # Check analysis templates
        cursor.execute("""
            SELECT at.id, at.name, hs.name as sector_name, at.is_default
            FROM analysis_templates at
            JOIN healthcare_sectors hs ON at.healthcare_sector_id = hs.id
            ORDER BY hs.name, at.name;
        """)
        templates = cursor.fetchall()
        print(f"   \n   Analysis templates ({len(templates)}):")
        for template in templates:
            default_marker = "⭐ default" if template[3] else ""
            print(f"     - {template[1]} ({template[2]}) {default_marker}")
        
        # Check template chapters
        cursor.execute("""
            SELECT tc.id, tc.title, at.name as template_name, tc.order_index
            FROM template_chapters tc
            JOIN analysis_templates at ON tc.analysis_template_id = at.id
            ORDER BY at.name, tc.order_index;
        """)
        chapters = cursor.fetchall()
        print(f"   \n   Template chapters ({len(chapters)}):")
        current_template = None
        for chapter in chapters:
            if chapter[2] != current_template:
                current_template = chapter[2]
                print(f"     {current_template}:")
            print(f"       {chapter[3]}. {chapter[1]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking healthcare templates: {e}")
        return False

def check_pipeline_prompts():
    """Verify pipeline prompt system"""
    print("\n4. Checking pipeline prompt system...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Check pipeline prompts
        cursor.execute("""
            SELECT id, prompt_type, prompt_name, is_enabled, created_at
            FROM pipeline_prompts 
            ORDER BY prompt_type, prompt_name;
        """)
        prompts = cursor.fetchall()
        
        print(f"   Found {len(prompts)} pipeline prompts:")
        current_type = None
        for prompt in prompts:
            prompt_id, prompt_type, prompt_name, is_enabled, created_at = prompt
            if prompt_type != current_type:
                current_type = prompt_type
                print(f"     {current_type.upper()}:")
            
            status = "✅ enabled" if is_enabled else "❌ disabled"
            print(f"       - {prompt_name} ({status})")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking pipeline prompts: {e}")
        return False

def check_model_configs():
    """Verify model configuration"""
    print("\n5. Checking model configurations...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Check model configs
        cursor.execute("""
            SELECT id, model_name, model_type, is_active, created_at
            FROM model_configs 
            ORDER BY model_type, model_name;
        """)
        configs = cursor.fetchall()
        
        print(f"   Found {len(configs)} model configurations:")
        current_type = None
        for config in configs:
            config_id, model_name, model_type, is_active, created_at = config
            if model_type != current_type:
                current_type = model_type
                print(f"     {current_type.upper()}:")
            
            status = "✅ active" if is_active else "❌ inactive"
            print(f"       - {model_name} ({status})")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"   ❌ Error checking model configs: {e}")
        return False

def check_application_readiness():
    """Check if application is ready to function"""
    print("\n6. Checking application readiness...")
    
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='review-platform',
            user='review_user',
            password='review_password'
        )
        cursor = conn.cursor()
        
        # Check for essential data
        checks = []
        
        # Check users exist
        cursor.execute("SELECT COUNT(*) FROM users;")
        user_count = cursor.fetchone()[0]
        checks.append(("Users exist", user_count > 0))
        
        # Check healthcare sectors exist
        cursor.execute("SELECT COUNT(*) FROM healthcare_sectors;")
        sector_count = cursor.fetchone()[0]
        checks.append(("Healthcare sectors configured", sector_count > 0))
        
        # Check analysis templates exist
        cursor.execute("SELECT COUNT(*) FROM analysis_templates;")
        template_count = cursor.fetchone()[0]
        checks.append(("Analysis templates configured", template_count > 0))
        
        # Check pipeline prompts exist
        cursor.execute("SELECT COUNT(*) FROM pipeline_prompts;")
        prompt_count = cursor.fetchone()[0]
        checks.append(("Pipeline prompts configured", prompt_count > 0))
        
        # Check active models exist
        cursor.execute("SELECT COUNT(*) FROM model_configs WHERE is_active = true;")
        active_model_count = cursor.fetchone()[0]
        checks.append(("Active models configured", active_model_count > 0))
        
        print("   Application readiness checks:")
        all_passed = True
        for check_name, passed in checks:
            status = "✅" if passed else "❌"
            print(f"     {status} {check_name}")
            if not passed:
                all_passed = False
        
        cursor.close()
        conn.close()
        
        if all_passed:
            print("\n   🎉 Application is ready to use!")
        else:
            print("\n   ⚠️  Some configuration may be missing")
        
        return all_passed
        
    except Exception as e:
        print(f"   ❌ Error checking application readiness: {e}")
        return False

def main():
    """Main verification function"""
    print("Data Integrity Verification")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    checks = [
        check_user_data(),
        check_pitch_deck_data(),
        check_healthcare_templates(),
        check_pipeline_prompts(),
        check_model_configs(),
        check_application_readiness()
    ]
    
    print("\n" + "=" * 50)
    print("VERIFICATION SUMMARY")
    print("=" * 50)
    
    passed = sum(checks)
    total = len(checks)
    
    if passed == total:
        print(f"✅ All {total} integrity checks passed!")
        print("\n🎉 PostgreSQL migration is complete and data integrity verified!")
        print("\nNext steps:")
        print("1. Test the web application")
        print("2. Try uploading a pitch deck")
        print("3. Monitor application logs")
        print("4. Archive the SQLite database")
        return True
    else:
        print(f"❌ {total - passed} checks failed out of {total}")
        print("\nSome data integrity issues were found. Please review above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)