#!/usr/bin/env python3
"""
Add Company Offering Prompt to Database
Extract the company offering prompt from GPU processing code and store it in the database
"""

import sys
import os
sys.path.append('/opt/review-platform/backend')

from datetime import datetime
from app.db.database import get_db
from sqlalchemy import text

def add_company_offering_prompt():
    """Add company offering prompt to pipeline_prompts table"""
    
    # The exact prompt from gpu_processing/utils/pitch_deck_analyzer.py line 194
    COMPANY_OFFERING_PROMPT = "Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company."
    
    print("Adding Company Offering Prompt to Database")
    print("=" * 50)
    
    try:
        db = next(get_db())
        
        # Check if company_offering prompt already exists
        existing = db.execute(
            text("SELECT id, prompt_text FROM pipeline_prompts WHERE stage_name = 'company_offering'")
        ).fetchone()
        
        if existing:
            print(f"✅ Company offering prompt already exists in database (ID: {existing[0]})")
            print(f"Current prompt: {existing[1]}")
            
            # Ask if user wants to update it
            update = input("\nDo you want to update the existing prompt? (y/n): ").lower().strip()
            if update == 'y':
                db.execute(
                    text("""
                        UPDATE pipeline_prompts 
                        SET prompt_text = :prompt_text, 
                            updated_at = :updated_at 
                        WHERE stage_name = 'company_offering'
                    """),
                    {
                        'prompt_text': COMPANY_OFFERING_PROMPT,
                        'updated_at': datetime.utcnow()
                    }
                )
                db.commit()
                print("✅ Company offering prompt updated successfully!")
            else:
                print("❌ Keeping existing prompt unchanged")
                return False
        else:
            # Insert new company_offering prompt
            db.execute(
                text("""
                    INSERT INTO pipeline_prompts (stage_name, prompt_text, description, is_active, created_at, updated_at)
                    VALUES (:stage_name, :prompt_text, :description, :is_active, :created_at, :updated_at)
                """),
                {
                    'stage_name': 'company_offering',
                    'prompt_text': COMPANY_OFFERING_PROMPT,
                    'description': 'Prompt for generating a single sentence description of what the startup offers',
                    'is_active': True,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }
            )
            db.commit()
            print("✅ Company offering prompt added successfully!")
        
        # Verify the prompt was added/updated
        result = db.execute(
            text("SELECT stage_name, prompt_text, is_active FROM pipeline_prompts WHERE stage_name = 'company_offering'")
        ).fetchone()
        
        if result:
            print(f"\n📋 Final verification:")
            print(f"   Stage: {result[0]}")
            print(f"   Active: {result[2]}")
            print(f"   Prompt: {result[1]}")
            print(f"\n🎉 Success! Company offering prompt is now available in the web UI.")
            return True
        else:
            print("❌ Error: Could not verify prompt was added")
            return False
            
    except Exception as e:
        print(f"❌ Error adding company offering prompt: {e}")
        return False

def show_all_pipeline_prompts():
    """Show all current pipeline prompts"""
    print("\n📋 Current Pipeline Prompts:")
    print("-" * 50)
    
    try:
        db = next(get_db())
        results = db.execute(
            text("SELECT stage_name, prompt_text, is_active FROM pipeline_prompts ORDER BY stage_name")
        ).fetchall()
        
        for row in results:
            status = "✅ Active" if row[2] else "❌ Inactive"
            print(f"• {row[0]} ({status})")
            print(f"  {row[1][:80]}{'...' if len(row[1]) > 80 else ''}")
            print()
            
    except Exception as e:
        print(f"❌ Error showing pipeline prompts: {e}")

def main():
    """Main function"""
    print("Company Offering Prompt Setup")
    print("=" * 50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Show current prompts
    show_all_pipeline_prompts()
    
    # Add company offering prompt
    success = add_company_offering_prompt()
    
    if success:
        print("\n✅ SETUP COMPLETE!")
        print("The company offering prompt is now available in the web UI.")
        print("You can now edit it through the Template Management page.")
        print("\nNext steps:")
        print("1. Go to /templates in the web UI")
        print("2. Look for 'company_offering' in the pipeline prompts section")
        print("3. Edit the prompt as needed")
    else:
        print("\n❌ Setup failed - please check the errors above")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)