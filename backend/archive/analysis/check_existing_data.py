#!/usr/bin/env python3
"""
Quick script to check existing database structure and data
"""

import sys
import os
from sqlalchemy import text

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

from app.db.database import SessionLocal

def main():
    db = SessionLocal()
    
    try:
        print("=== EXISTING DATABASE STRUCTURE ===\n")
        
        # Check healthcare sectors
        print("Healthcare Sectors:")
        result = db.execute(text("SELECT id, name, display_name FROM healthcare_sectors ORDER BY id"))
        for row in result:
            print(f"  ID {row[0]}: {row[1]} ({row[2]})")
        
        # Check existing templates 
        print("\nExisting Analysis Templates:")
        result = db.execute(text("SELECT id, healthcare_sector_id, name FROM analysis_templates ORDER BY id"))
        for row in result:
            print(f"  ID {row[0]}: {row[2]} (sector_id: {row[1]})")
        
        # Check if our target template exists
        print("\nChecking for 'Standard Seven-Chapter Review':")
        result = db.execute(text("SELECT id, name FROM analysis_templates WHERE name = 'Standard Seven-Chapter Review'"))
        existing = result.fetchone()
        if existing:
            print(f"  ✅ EXISTS: ID {existing[0]} - {existing[1]}")
        else:
            print("  ❌ DOES NOT EXIST")
        
        # Check ALL related table data to understand the full structure
        print("\nTemplate Chapters (count by template):")
        result = db.execute(text("SELECT template_id, COUNT(*) FROM template_chapters GROUP BY template_id ORDER BY template_id"))
        for row in result:
            print(f"  Template {row[0]}: {row[1]} chapters")
        
        print("\nMax IDs in each table:")
        result = db.execute(text("SELECT MAX(id) FROM healthcare_sectors"))
        print(f"  healthcare_sectors max ID: {result.fetchone()[0]}")
        
        result = db.execute(text("SELECT MAX(id) FROM analysis_templates"))
        print(f"  analysis_templates max ID: {result.fetchone()[0]}")
        
        result = db.execute(text("SELECT MAX(id) FROM template_chapters"))
        print(f"  template_chapters max ID: {result.fetchone()[0]}")
        
        result = db.execute(text("SELECT MAX(id) FROM chapter_questions"))
        print(f"  chapter_questions max ID: {result.fetchone()[0]}")
        
        # Check sequences
        print("\nSequence current values:")
        try:
            result = db.execute(text("SELECT last_value FROM healthcare_sectors_id_seq"))
            print(f"  healthcare_sectors_id_seq: {result.fetchone()[0]}")
        except: pass
        
        try:
            result = db.execute(text("SELECT last_value FROM analysis_templates_id_seq"))
            print(f"  analysis_templates_id_seq: {result.fetchone()[0]}")
        except: pass
        
        try:
            result = db.execute(text("SELECT last_value FROM template_chapters_id_seq"))
            print(f"  template_chapters_id_seq: {result.fetchone()[0]}")
        except: pass
        
        try:
            result = db.execute(text("SELECT last_value FROM chapter_questions_id_seq"))
            print(f"  chapter_questions_id_seq: {result.fetchone()[0]}")
        except: pass
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()