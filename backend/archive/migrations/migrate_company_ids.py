#!/usr/bin/env python3
"""
Migration script to update company_id in pitch_decks table
from email-based format to company name slug format
"""

import sqlite3
import re
import os

def company_name_to_slug(company_name):
    """Convert company name to URL-safe slug"""
    if not company_name:
        return None
    return re.sub(r'[^a-z0-9-]', '', company_name.lower().replace(' ', '-'))

def migrate_company_ids():
    """Update all pitch_decks records to use company name slug as company_id"""
    
    db_path = "/opt/review_platform/backend/sql_app.db"
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Get all pitch_decks with their associated user company names
        cursor.execute("""
            SELECT pd.id, pd.company_id, u.company_name, u.email, pd.file_name
            FROM pitch_decks pd
            JOIN users u ON pd.user_id = u.id
            ORDER BY pd.id
        """)
        
        records = cursor.fetchall()
        
        print(f"Found {len(records)} pitch deck records to migrate")
        print("-" * 80)
        
        updated_count = 0
        
        for record in records:
            deck_id, old_company_id, company_name, email, file_name = record
            
            # Generate new company_id from company name
            new_company_id = company_name_to_slug(company_name)
            
            if not new_company_id:
                # Fallback to email prefix if company name is empty
                new_company_id = email.split('@')[0]
            
            print(f"Deck {deck_id} ({file_name}):")
            print(f"  Old company_id: {old_company_id}")
            print(f"  Company name: {company_name}")
            print(f"  New company_id: {new_company_id}")
            
            if old_company_id != new_company_id:
                # Update the database record
                cursor.execute("""
                    UPDATE pitch_decks 
                    SET company_id = ? 
                    WHERE id = ?
                """, (new_company_id, deck_id))
                
                updated_count += 1
                print(f"  ✅ Updated")
            else:
                print(f"  ⏭️  No change needed")
            
            print()
        
        # Commit the changes
        conn.commit()
        
        print("-" * 80)
        print(f"Migration completed successfully!")
        print(f"Updated {updated_count} out of {len(records)} records")
        
        # Show final state
        print("\nFinal state:")
        cursor.execute("""
            SELECT pd.id, pd.company_id, u.company_name, pd.file_name
            FROM pitch_decks pd
            JOIN users u ON pd.user_id = u.id
            ORDER BY pd.id
        """)
        
        final_records = cursor.fetchall()
        for record in final_records:
            deck_id, company_id, company_name, file_name = record
            print(f"  Deck {deck_id}: {company_id} ({company_name}) - {file_name}")
        
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_company_ids()