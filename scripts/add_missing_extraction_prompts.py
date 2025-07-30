#!/usr/bin/env python3
"""
Add missing extraction prompts to pipeline_prompts table
This script adds the funding_amount_extraction and deck_date_extraction prompts 
that are required by the API but missing from the database.
"""

import psycopg2
import sys
import os
from datetime import datetime

# Database configuration - can be overridden by environment variables
DEV_DB_URL = os.getenv("DEV_DB_URL", "postgresql://dev_user:!dev_Halbzeit1024@65.108.32.143:5432/review_dev")
PROD_DB_URL = os.getenv("PROD_DB_URL", "postgresql://review_user:review_password@localhost:5432/review-platform")

# Missing prompts to add
MISSING_PROMPTS = [
    {
        "stage_name": "funding_amount_extraction",
        "prompt_text": "Please extract the specific funding amount the startup is seeking from the pitch deck. Look for phrases like 'seeking €X', 'raising $X', 'funding requirement of X', or similar. If you find multiple amounts (seed, Series A, total, etc.), focus on the primary funding amount being sought in this round. Provide only the amount (e.g., '€2.5M', '$500K', '£1M') without additional explanation. If no specific amount is mentioned, respond with 'Not specified'.",
        "prompt_type": "extraction",
        "prompt_name": "Funding Amount Extraction"
    },
    {
        "stage_name": "deck_date_extraction", 
        "prompt_text": "Please identify when this pitch deck was created or last updated. Look for dates in headers, footers, slide timestamps, version information, or any date references that indicate when the deck was prepared. Focus on the most recent date that reflects when the current version was created. Provide the date in a clear format (e.g., 'March 2024', '2024-03-15', 'Q1 2024'). If no date information is available, respond with 'Date not found'.",
        "prompt_type": "extraction", 
        "prompt_name": "Deck Date Extraction"
    }
]

def add_prompts_to_database(db_url: str, db_name: str):
    """Add missing prompts to the specified database"""
    
    try:
        print(f"🔗 Connecting to {db_name} database...")
        conn = psycopg2.connect(db_url)
        cur = conn.cursor()
        
        print(f"📋 Adding {len(MISSING_PROMPTS)} missing prompts to {db_name}...")
        
        for prompt in MISSING_PROMPTS:
            # Check if prompt already exists
            cur.execute(
                "SELECT id FROM pipeline_prompts WHERE stage_name = %s",
                (prompt["stage_name"],)
            )
            
            existing = cur.fetchone()
            
            if existing:
                print(f"   ⚠️  {prompt['stage_name']} already exists (ID: {existing[0]}) - skipping")
                continue
                
            # Insert new prompt
            cur.execute("""
                INSERT INTO pipeline_prompts 
                (stage_name, prompt_text, is_active, created_by, created_at, updated_at, prompt_type, prompt_name, is_enabled)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (
                prompt["stage_name"],
                prompt["prompt_text"], 
                True,  # is_active
                "system",  # created_by
                datetime.utcnow(),  # created_at
                datetime.utcnow(),  # updated_at
                prompt["prompt_type"],  # prompt_type
                prompt["prompt_name"],  # prompt_name
                True  # is_enabled
            ))
            
            prompt_id = cur.fetchone()[0]
            print(f"   ✅ Added {prompt['stage_name']} (ID: {prompt_id})")
            print(f"      Preview: {prompt['prompt_text'][:100]}...")
        
        conn.commit()
        
        # Verify the prompts were added
        print(f"\n🔍 Verifying prompts in {db_name}...")
        cur.execute("""
            SELECT stage_name, prompt_name, is_active, LENGTH(prompt_text) as text_length
            FROM pipeline_prompts 
            WHERE stage_name IN ('funding_amount_extraction', 'deck_date_extraction')
            ORDER BY stage_name
        """)
        
        results = cur.fetchall()
        if results:
            print(f"✅ Verification successful - found {len(results)} extraction prompts:")
            for stage_name, prompt_name, is_active, text_length in results:
                status = "✅ active" if is_active else "⏸️  inactive"  
                print(f"   {status} {stage_name} ({text_length} chars) - {prompt_name}")
        else:
            print("❌ Verification failed - no extraction prompts found")
            
        cur.close()
        conn.close()
        
        return True
        
    except psycopg2.OperationalError as e:
        print(f"❌ Database connection error for {db_name}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error adding prompts to {db_name}: {e}")
        return False

def export_prompts_to_shared_filesystem():
    """Export the new prompts to shared filesystem for production import"""
    
    try:
        print("\n📤 Exporting prompts to shared filesystem...")
        
        # Create SQL export for production import
        export_sql = "-- Missing extraction prompts export\n"
        export_sql += "-- Generated by add_missing_extraction_prompts.py\n\n"
        
        for prompt in MISSING_PROMPTS:
            # Use INSERT ... ON CONFLICT to handle duplicates safely
            export_sql += f"""
INSERT INTO pipeline_prompts 
(stage_name, prompt_text, is_active, created_by, created_at, updated_at, prompt_type, prompt_name, is_enabled)
VALUES (
    '{prompt["stage_name"]}',
    $${prompt["prompt_text"]}$$,
    true,
    'system',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    '{prompt["prompt_type"]}',
    '{prompt["prompt_name"]}', 
    true
)
ON CONFLICT (stage_name) DO UPDATE SET
    prompt_text = EXCLUDED.prompt_text,
    updated_at = CURRENT_TIMESTAMP,
    prompt_name = EXCLUDED.prompt_name;

"""
        
        # Write to shared filesystem for production import
        shared_export_path = "/mnt/production-shared/temp/missing_extraction_prompts.sql"
        
        with open(shared_export_path, 'w') as f:
            f.write(export_sql)
            
        print(f"✅ Exported prompts to {shared_export_path}")
        print("📌 Next steps:")
        print(f"   1. Run this SQL file on production: psql [connection] -f {shared_export_path}")
        print("   2. Re-run the export_prompts_production.sh script to verify")
        
        return True
        
    except Exception as e:
        print(f"❌ Error exporting prompts: {e}")
        return False

def main():
    """Main execution function"""
    
    print("🚀 Adding missing extraction prompts to databases...")
    print("=" * 60)
    
    # Add to development database
    dev_success = add_prompts_to_database(DEV_DB_URL, "development")
    
    print("\n" + "=" * 60)
    
    # Try to add to production database (if accessible)
    prod_success = False
    try:
        prod_success = add_prompts_to_database(PROD_DB_URL, "production")
    except:
        print("ℹ️  Production database not accessible from development server")
        print("   Will export SQL file for manual production import instead")
    
    print("\n" + "=" * 60)
    
    # Always export for production import
    export_success = export_prompts_to_shared_filesystem()
    
    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"   Development database: {'✅ Success' if dev_success else '❌ Failed'}")
    print(f"   Production database:  {'✅ Success' if prod_success else '📤 Export created'}")
    print(f"   Shared export:        {'✅ Success' if export_success else '❌ Failed'}")
    
    if dev_success:
        print("\n🎉 Development database is ready!")
        print("   The Dojo extraction tests should now work without 'prompt not found' errors")
        
    if export_success:
        print("\n📋 For production:")
        print("   1. SSH to production server")
        print("   2. Run: psql postgresql://review_user:review_password@localhost:5432/review-platform -f /mnt/CPU-GPU/temp/missing_extraction_prompts.sql")
        print("   3. Run: ./scripts/export_prompts_production.sh")
        print("   4. Verify prompts appear in export")

if __name__ == "__main__":
    main()