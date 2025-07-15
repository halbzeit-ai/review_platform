#!/usr/bin/env python3
"""
Fix the missing os import in documents.py
"""

import os
import shutil

def fix_results_import():
    """Add missing os import to documents.py"""
    
    api_file = "/opt/review-platform/backend/app/api/documents.py"
    
    if not os.path.exists(api_file):
        print(f"❌ API file not found: {api_file}")
        return False
    
    # Read the file
    with open(api_file, 'r') as f:
        content = f.read()
    
    # Check if os is already imported
    if 'import os' in content:
        print("✅ os is already imported")
        return True
    
    # Add os import after the existing imports
    import_section = """from fastapi import APIRouter, HTTPException, UploadFile, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from ..core.volume_storage import volume_storage
from ..core.config import settings
from ..db.models import User, PitchDeck
from ..db.database import get_db
from .auth import get_current_user
import uuid
import logging"""
    
    new_import_section = """from fastapi import APIRouter, HTTPException, UploadFile, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from ..core.volume_storage import volume_storage
from ..core.config import settings
from ..db.models import User, PitchDeck
from ..db.database import get_db
from .auth import get_current_user
import uuid
import logging
import os
import json
import glob"""
    
    # Replace the import section
    if import_section in content:
        content = content.replace(import_section, new_import_section)
        
        # Write the updated content
        with open(api_file, 'w') as f:
            f.write(content)
        
        print("✅ Added missing imports: os, json, glob")
        return True
    else:
        print("❌ Could not find import section to update")
        return False

if __name__ == "__main__":
    print("=== FIXING MISSING IMPORTS ===")
    success = fix_results_import()
    
    if success:
        print("\n✅ Imports fixed!")
        print("Restart the backend service: sudo systemctl restart review-platform")
    else:
        print("\n❌ Failed to fix imports")
        print("Manual intervention required")