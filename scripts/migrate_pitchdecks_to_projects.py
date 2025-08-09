#!/usr/bin/env python3
"""
Migration script to move all pitch_decks data into the project system.
This consolidates the two systems into one unified project-based approach.
"""

import sys
import os
from pathlib import Path

# Add backend to path and load environment
backend_path = Path(__file__).parent.parent / "backend"
sys.path.append(str(backend_path))

from dotenv import load_dotenv
load_dotenv(backend_path / ".env")

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json
from datetime import datetime

# Use backend database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://review_user:simpleprod2024@localhost:5432/review-platform")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def migrate_pitch_decks_to_projects():
    """Migrate all pitch_decks to the project system"""
    db = SessionLocal()
    
    try:
        print("🚀 Starting pitch deck to project system migration...")
        
        # Step 1: Analyze current state
        print("\n📊 Analyzing current data...")
        
        pitch_deck_analysis = db.execute(text("""
            SELECT 
                pd.company_id,
                COUNT(*) as deck_count,
                COUNT(DISTINCT pd.user_id) as unique_users,
                STRING_AGG(DISTINCT u.email, ', ') as user_emails,
                ARRAY_AGG(DISTINCT pd.user_id) as user_ids,
                ARRAY_AGG(pd.id) as deck_ids,
                ARRAY_AGG(pd.file_name) as file_names
            FROM pitch_decks pd
            LEFT JOIN users u ON pd.user_id = u.id
            WHERE pd.company_id IS NOT NULL
            GROUP BY pd.company_id
            ORDER BY deck_count DESC
        """)).fetchall()
        
        if not pitch_deck_analysis:
            print("✅ No pitch decks found. Migration not needed.")
            return
        
        print(f"Found {len(pitch_deck_analysis)} companies with pitch decks:")
        for row in pitch_deck_analysis:
            print(f"  - {row[0]}: {row[1]} decks, {row[2]} users ({row[3]})")
        
        # Step 2: Create missing projects and fix orphaned ones
        print("\n🏗️  Creating/fixing projects...")
        
        for company_id, deck_count, unique_users, user_emails, user_ids, deck_ids, file_names in pitch_deck_analysis:
            print(f"\n  Processing {company_id}...")
            
            # Check if project exists
            existing_project = db.execute(text("""
                SELECT id, project_name, owner_id FROM projects 
                WHERE company_id = :company_id
            """), {"company_id": company_id}).fetchone()
            
            if existing_project:
                project_id, project_name, owner_id = existing_project
                print(f"    ✅ Project {project_id} exists: {project_name}")
                
                # Check if project has members
                member_count = db.execute(text("""
                    SELECT COUNT(*) FROM project_members WHERE project_id = :project_id
                """), {"project_id": project_id}).fetchone()[0]
                
                if member_count == 0:
                    print(f"    🔧 Project is orphaned, adding members...")
                    # Add all users who have pitch decks for this company as project members
                    for user_id in user_ids:
                        if user_id:  # Skip NULL user_ids
                            db.execute(text("""
                                INSERT INTO project_members (project_id, user_id, role, added_at)
                                VALUES (:project_id, :user_id, 'member', CURRENT_TIMESTAMP)
                                ON CONFLICT (project_id, user_id) DO NOTHING
                            """), {"project_id": project_id, "user_id": user_id})
                            print(f"      ✅ Added user {user_id} as member")
                    
                    # Set owner if not set
                    if not owner_id and user_ids:
                        first_user_id = next(uid for uid in user_ids if uid is not None)
                        db.execute(text("""
                            UPDATE projects SET owner_id = :owner_id WHERE id = :project_id
                        """), {"owner_id": first_user_id, "project_id": project_id})
                        print(f"      ✅ Set user {first_user_id} as project owner")
                
            else:
                print(f"    🆕 Creating new project for {company_id}...")
                
                # Create new project
                # Get first user for project creation
                first_user_id = next(uid for uid in user_ids if uid is not None)
                first_user_email = db.execute(text("""
                    SELECT email FROM users WHERE id = :user_id
                """), {"user_id": first_user_id}).fetchone()[0]
                
                project_result = db.execute(text("""
                    INSERT INTO projects (
                        company_id, project_name, project_metadata, 
                        owner_id, is_active, created_at, updated_at
                    ) VALUES (
                        :company_id, :project_name, :metadata,
                        :owner_id, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    ) RETURNING id
                """), {
                    "company_id": company_id,
                    "project_name": f"{company_id.title()} - Migrated Project",
                    "metadata": json.dumps({
                        "migrated_from_pitch_decks": True,
                        "migration_date": datetime.now().isoformat(),
                        "original_deck_count": deck_count
                    }),
                    "owner_id": first_user_id
                })
                
                project_id = project_result.fetchone()[0]
                print(f"    ✅ Created project {project_id}")
                
                # Add all users as project members
                for user_id in user_ids:
                    if user_id:  # Skip NULL user_ids
                        role = "owner" if user_id == first_user_id else "member"
                        db.execute(text("""
                            INSERT INTO project_members (project_id, user_id, role, added_by_id, added_at)
                            VALUES (:project_id, :user_id, :role, :added_by_id, CURRENT_TIMESTAMP)
                        """), {
                            "project_id": project_id, 
                            "user_id": user_id, 
                            "role": role,
                            "added_by_id": first_user_id
                        })
                        print(f"      ✅ Added user {user_id} as {role}")
            
            # Step 3: Migrate pitch decks to project_documents
            print(f"    📄 Migrating {deck_count} pitch decks to project_documents...")
            
            for i, deck_id in enumerate(deck_ids):
                if deck_id:
                    # Get pitch deck details
                    deck_details = db.execute(text("""
                        SELECT user_id, file_name, file_path, results_file_path, 
                               processing_status, created_at
                        FROM pitch_decks WHERE id = :deck_id
                    """), {"deck_id": deck_id}).fetchone()
                    
                    if deck_details:
                        user_id, file_name, file_path, results_file_path, processing_status, created_at = deck_details
                        
                        # Check if document already exists
                        existing_doc = db.execute(text("""
                            SELECT id FROM project_documents 
                            WHERE project_id = :project_id AND file_name = :file_name
                        """), {"project_id": project_id, "file_name": file_name}).fetchone()
                        
                        if not existing_doc:
                            # Insert into project_documents (using extracted_data for metadata)
                            db.execute(text("""
                                INSERT INTO project_documents (
                                    project_id, document_type, file_name, file_path,
                                    original_filename, processing_status, uploaded_by,
                                    upload_date, is_active, extracted_data
                                ) VALUES (
                                    :project_id, 'pitch_deck', :file_name, :file_path,
                                    :original_filename, :processing_status, :uploaded_by,
                                    :upload_date, TRUE, :metadata
                                )
                            """), {
                                "project_id": project_id,
                                "file_name": file_name,
                                "file_path": file_path,
                                "original_filename": file_name,
                                "processing_status": processing_status or "completed",
                                "uploaded_by": user_id,
                                "upload_date": created_at,
                                "metadata": json.dumps({
                                    "migrated_from_pitch_deck_id": deck_id,
                                    "original_results_file_path": results_file_path,
                                    "migration_date": datetime.now().isoformat()
                                })
                            })
                            print(f"      ✅ Migrated deck {deck_id}: {file_name}")
                        else:
                            print(f"      ⏭️ Document {file_name} already exists, skipping")
        
        # Commit all changes
        db.commit()
        
        print("\n🎉 Migration completed successfully!")
        print("📋 Summary:")
        print(f"   - Processed {len(pitch_deck_analysis)} companies")
        print(f"   - All pitch decks migrated to project_documents")
        print(f"   - All users added as project members")
        print("\n⚠️  Next steps:")
        print("   - Review migrated projects in GP dashboard")
        print("   - Test that all functionality works with project system")
        print("   - Consider archiving pitch_decks table after verification")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_pitch_decks_to_projects()