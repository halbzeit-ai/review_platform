#!/usr/bin/env python3
"""
Verify Company Offering Prompt in Database
Check if the company offering prompt is already in the database
"""

import sys
import os
sys.path.append('/opt/review-platform/backend')

from app.db.database import get_db
from sqlalchemy import text

def verify_company_offering_prompt():
    """Verify company offering prompt exists in database"""
    
    print("Verifying Company Offering Prompt in Database")
    print("=" * 50)
    
    try:
        db = next(get_db())
        
        # Check for offering_extraction prompt
        result = db.execute(
            text("SELECT stage_name, prompt_text, is_active FROM pipeline_prompts WHERE stage_name = 'offering_extraction'")
        ).fetchone()
        
        if result:
            print("✅ Company offering prompt found in database!")
            print(f"   Stage name: {result[0]}")
            print(f"   Active: {result[2]}")
            print(f"   Prompt text: {result[1]}")
            
            # Check if it matches the expected prompt
            expected_prompt = "Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company."
            
            if result[1] == expected_prompt:
                print("\n✅ Prompt text matches exactly with GPU processing code!")
                print("\n📋 Summary:")
                print("   • The company offering prompt is already in the database")
                print("   • It's stored as 'offering_extraction' stage")
                print("   • The GPU processing code should use this stage name")
                print("   • You can edit it through the web UI at /templates")
                return True
            else:
                print("\n⚠️  Prompt text differs from GPU processing code:")
                print(f"   Database: {result[1]}")
                print(f"   GPU code: {expected_prompt}")
                return False
        else:
            print("❌ Company offering prompt not found in database")
            print("   Looking for alternative stage names...")
            
            # Check for any prompt that might be the company offering prompt
            results = db.execute(
                text("SELECT stage_name, prompt_text FROM pipeline_prompts WHERE prompt_text LIKE '%service or product%'")
            ).fetchall()
            
            if results:
                print(f"   Found {len(results)} similar prompts:")
                for row in results:
                    print(f"   • {row[0]}: {row[1][:80]}...")
            else:
                print("   No similar prompts found")
            
            return False
            
    except Exception as e:
        print(f"❌ Error checking database: {e}")
        return False

def show_all_pipeline_prompts():
    """Show all pipeline prompts"""
    print("\n📋 All Pipeline Prompts:")
    print("-" * 50)
    
    try:
        db = next(get_db())
        results = db.execute(
            text("SELECT stage_name, prompt_text, is_active FROM pipeline_prompts ORDER BY stage_name")
        ).fetchall()
        
        for row in results:
            status = "✅ Active" if row[2] else "❌ Inactive"
            print(f"• {row[0]} ({status})")
            print(f"  {row[1][:100]}{'...' if len(row[1]) > 100 else ''}")
            print()
            
    except Exception as e:
        print(f"❌ Error showing pipeline prompts: {e}")

def main():
    """Main function"""
    success = verify_company_offering_prompt()
    show_all_pipeline_prompts()
    
    if success:
        print("\n🎉 SUCCESS!")
        print("The company offering prompt is already available in the database.")
        print("You can now edit it through the web UI at /templates")
    else:
        print("\n❌ The company offering prompt needs to be added to the database.")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)