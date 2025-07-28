#!/usr/bin/env python3
"""
Direct database check for templates
"""

import sys
import os
sys.path.append('.')

from sqlalchemy import create_engine, text
from app.core.config import settings

def check_templates_db():
    # Connect to database
    engine = create_engine(settings.DATABASE_URL)
    
    with engine.connect() as connection:
        # Check if healthcare_templates table exists
        result = connection.execute(text("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'healthcare_templates'
        """))
        
        if not result.fetchone():
            print("healthcare_templates table does not exist!")
            return
        
        # Get all templates
        result = connection.execute(text("""
            SELECT id, template_name, is_active, is_default, 
                   SUBSTRING(analysis_prompt, 1, 100) as prompt_preview
            FROM healthcare_templates 
            ORDER BY id
        """))
        
        templates = result.fetchall()
        print("Templates in database:")
        for template in templates:
            print(f"  ID: {template[0]}")
            print(f"  Name: '{template[1]}'")
            print(f"  Active: {template[2]}")
            print(f"  Default: {template[3]}")
            print(f"  Prompt preview: {template[4]}...")
            print("  ---")

if __name__ == "__main__":
    check_templates_db()