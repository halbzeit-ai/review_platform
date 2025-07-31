#!/usr/bin/env python3
"""
Manual dojo cleanup script to fix the sync issue between database and filesystem
"""

import os
import sys
import glob

# Add the app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend', 'app'))

from backend.app.db.database import SessionLocal
from backend.app.db.models import PitchDeck
from sqlalchemy import text

def main():
    print("🧹 Manual Dojo Cleanup")
    print("=" * 50)
    
    # Create database session
    db = SessionLocal()
    
    try:
        # 1. Show current state
        dojo_files = db.query(PitchDeck).filter(PitchDeck.data_source == 'dojo').all()
        print(f"📊 Database: {len(dojo_files)} dojo records")
        
        filesystem_files = glob.glob("/mnt/dev-shared/dojo/*.pdf")
        print(f"📁 Filesystem: {len(filesystem_files)} PDF files")
        
        print()
        
        # 2. Delete all filesystem files
        print("🗑️  Deleting all filesystem files...")
        deleted_fs = 0
        for file_path in filesystem_files:
            try:
                os.remove(file_path)
                deleted_fs += 1
                print(f"   ✅ Deleted: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"   ❌ Failed to delete {file_path}: {e}")
        
        print(f"   Total deleted from filesystem: {deleted_fs}")
        print()
        
        # 3. Delete all database records
        print("🗑️  Deleting all database records...")
        try:
            # Clear visual analysis cache first
            cache_result = db.execute(text("DELETE FROM visual_analysis_cache WHERE pitch_deck_id IN (SELECT id FROM pitch_decks WHERE data_source = 'dojo')"))
            print(f"   ✅ Cleared {cache_result.rowcount} cache entries")
            
            # Delete project documents
            project_result = db.execute(text("DELETE FROM project_documents WHERE document_type = 'pitch_deck' AND file_path LIKE 'dojo/%'"))
            print(f"   ✅ Deleted {project_result.rowcount} project documents")
            
            # Delete dojo pitch deck records
            deck_result = db.execute(text("DELETE FROM pitch_decks WHERE data_source = 'dojo'"))
            print(f"   ✅ Deleted {deck_result.rowcount} pitch deck records")
            
            db.commit()
            print("   ✅ Database cleanup committed")
            
        except Exception as e:
            print(f"   ❌ Database cleanup failed: {e}")
            db.rollback()
            return False
        
        print()
        
        # 4. Verify cleanup
        remaining_db = db.query(PitchDeck).filter(PitchDeck.data_source == 'dojo').count()
        remaining_fs = len(glob.glob("/mnt/dev-shared/dojo/*.pdf"))
        
        print("✅ Cleanup Complete!")
        print(f"   Database records remaining: {remaining_db}")
        print(f"   Filesystem files remaining: {remaining_fs}")
        
        if remaining_db == 0 and remaining_fs == 0:
            print("🎉 All dojo data successfully cleaned up!")
            return True
        else:
            print("⚠️  Some data still remains")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        return False
        
    finally:
        db.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)