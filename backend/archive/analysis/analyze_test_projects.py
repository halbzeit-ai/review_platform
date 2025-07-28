#!/usr/bin/env python3
"""
Test Project Analyzer
Identifies and categorizes test projects to help clean up migration artifacts
"""

import json
import os
import sys
from datetime import datetime

def get_database_connection():
    """Get database connection based on environment"""
    try:
        # Try to use the app's database session factory
        sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
        try:
            from app.db.database import SessionLocal
            from sqlalchemy import create_engine
            
            # Use the SessionLocal to get the engine
            session = SessionLocal()
            engine = session.get_bind()
            session.close()
            
            return engine.connect(), 'app_database'
        except Exception as e:
            print(f"App database connection failed: {e}")
        
        # Fallback to manual connection
        from sqlalchemy import create_engine
        
        # Try environment variables first
        db_url = os.getenv('DATABASE_URL')
        if db_url:
            try:
                engine = create_engine(db_url)
                return engine.connect(), 'env_var'
            except Exception as e:
                print(f"Environment DATABASE_URL failed: {e}")
        
        # Check if we're on production (PostgreSQL)
        if os.path.exists('/opt/review-platform'):
            # Try common PostgreSQL configurations
            postgres_configs = [
                "postgresql://postgres:@localhost:5432/review_platform",
                "postgresql://postgres:postgres@localhost:5432/review_platform",
                "postgresql://review_platform:@localhost:5432/review_platform",
            ]
            
            password = os.getenv('POSTGRES_PASSWORD', '')
            if password:
                postgres_configs.insert(0, f"postgresql://postgres:{password}@localhost:5432/review_platform")
            
            for db_url in postgres_configs:
                try:
                    print(f"Trying: {db_url.replace(password, '***' if password else '')}")
                    engine = create_engine(db_url)
                    conn = engine.connect()
                    return conn, 'manual_postgres'
                except Exception as e:
                    print(f"Failed: {e}")
                    continue
        
        # Fallback to SQLite for local development
        sqlite_path = os.path.join(os.path.dirname(__file__), 'sql_app.db')
        if os.path.exists(sqlite_path):
            engine = create_engine(f'sqlite:///{sqlite_path}')
            return engine.connect(), 'sqlite'
        
        raise Exception("Could not establish database connection with any method")
        
    except Exception as e:
        print(f"Database connection error: {e}")
        return None, None

def analyze_test_projects(conn):
    """Analyze test projects and identify migration artifacts"""
    print("=" * 80)
    print(f"TEST PROJECT ANALYSIS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    try:
        from sqlalchemy import text
        
        # Get overall project statistics
        stats_query = text("""
            SELECT 
                COUNT(*) as total_projects,
                COUNT(CASE WHEN is_test = TRUE THEN 1 END) as test_projects,
                COUNT(CASE WHEN is_test = FALSE THEN 1 END) as production_projects,
                COUNT(DISTINCT CASE WHEN is_test = TRUE THEN company_id END) as test_companies
            FROM projects
        """)
        
        stats = conn.execute(stats_query).fetchone()
        print(f"Database Statistics:")
        print(f"  Total Projects: {stats[0]}")
        print(f"  Test Projects: {stats[1]}")
        print(f"  Production Projects: {stats[2]}")
        print(f"  Test Companies: {stats[3]}")
        print()
        
        # Analyze test projects
        test_query = text("""
            SELECT 
                id, company_id, project_name, funding_round, 
                created_at, project_metadata, tags
            FROM projects 
            WHERE is_test = TRUE
            ORDER BY created_at DESC
        """)
        
        test_projects = conn.execute(test_query).fetchall()
        
        # Categorize projects
        dojo_projects = []
        migration_projects = []
        other_projects = []
        
        print(f"Analyzing {len(test_projects)} test projects:")
        print("-" * 50)
        
        for project in test_projects:
            project_id, company_id, project_name, funding_round, created_at, metadata_str, tags_str = project
            
            # Parse metadata and tags
            try:
                # Handle both string and dict formats for metadata
                if isinstance(metadata_str, dict):
                    metadata = metadata_str
                elif metadata_str:
                    metadata = json.loads(metadata_str)
                else:
                    metadata = {}
                
                # Handle both string and list formats for tags
                if isinstance(tags_str, list):
                    tags = tags_str
                elif tags_str:
                    tags = json.loads(tags_str)
                else:
                    tags = []
            except (json.JSONDecodeError, TypeError):
                metadata = {}
                tags = []
            
            # Categorize project
            if metadata.get('created_from_experiment') == True:
                dojo_projects.append(project)
            elif 'migration' in str(metadata).lower() or any('migration' in str(tag).lower() for tag in tags):
                migration_projects.append(project)
            else:
                other_projects.append(project)
        
        print(f"✅ Dojo-created projects: {len(dojo_projects)}")
        print(f"🔄 Migration artifacts: {len(migration_projects)}")
        print(f"❓ Other/Unknown projects: {len(other_projects)}")
        print()
        
        # Show details for non-dojo projects
        problematic_projects = migration_projects + other_projects
        
        if problematic_projects:
            print("NON-DOJO TEST PROJECTS (potential cleanup candidates):")
            print("-" * 60)
            
            cleanup_ids = []
            
            for project in problematic_projects:
                project_id, company_id, project_name, funding_round, created_at, metadata_str, tags_str = project
                
                try:
                    # Handle both string and dict formats for metadata
                    if isinstance(metadata_str, dict):
                        metadata = metadata_str
                    elif metadata_str:
                        metadata = json.loads(metadata_str)
                    else:
                        metadata = {}
                    
                    # Handle both string and list formats for tags
                    if isinstance(tags_str, list):
                        tags = tags_str
                    elif tags_str:
                        tags = json.loads(tags_str)
                    else:
                        tags = []
                except (json.JSONDecodeError, TypeError):
                    metadata = {}
                    tags = []
                
                print(f"Project ID: {project_id}")
                print(f"  Company: {company_id}")
                print(f"  Name: {project_name}")
                print(f"  Created: {created_at}")
                print(f"  Has experiment flag: {'created_from_experiment' in metadata}")
                print(f"  Metadata keys: {list(metadata.keys()) if metadata else 'None'}")
                print(f"  Tags: {tags}")
                
                cleanup_ids.append(project_id)
                print()
            
            # Generate cleanup SQL
            if cleanup_ids:
                print("CLEANUP SCRIPT:")
                print("-" * 30)
                print("-- Run these SQL commands to clean up non-dojo projects:")
                print()
                
                id_list = ', '.join(map(str, cleanup_ids))
                
                print(f"-- First, delete associated documents")
                print(f"DELETE FROM project_documents WHERE project_id IN ({id_list});")
                print()
                print(f"-- Then delete the projects")
                print(f"DELETE FROM projects WHERE id IN ({id_list});")
                print()
                print(f"-- This will remove {len(cleanup_ids)} projects")
                print()
                print("-- Verify the cleanup worked:")
                print("SELECT COUNT(*) FROM projects WHERE is_test = TRUE;")
        else:
            print("✅ All test projects appear to be properly created from dojo experiments!")
        
        # Show document associations
        print("\nDOCUMENT ASSOCIATIONS:")
        print("-" * 30)
        
        doc_query = text("""
            SELECT p.id, p.company_id, p.project_name, COUNT(pd.id) as doc_count,
                   array_agg(pd.document_type) as doc_types
            FROM projects p
            LEFT JOIN project_documents pd ON p.id = pd.project_id
            WHERE p.is_test = TRUE
            GROUP BY p.id, p.company_id, p.project_name
            HAVING COUNT(pd.id) > 0
            ORDER BY p.created_at DESC
        """)
        
        try:
            projects_with_docs = conn.execute(doc_query).fetchall()
            
            if projects_with_docs:
                print(f"Found {len(projects_with_docs)} test projects with documents:")
                for project in projects_with_docs:
                    print(f"  Project {project[0]} ({project[1]}): {project[3]} documents")
                    print(f"    Document types: {project[4]}")
            else:
                print("No test projects have associated documents.")
        except Exception as e:
            print(f"Could not analyze document associations (might be SQLite): {e}")
            
    except Exception as e:
        print(f"Error during analysis: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function"""
    print("Test Project Database Analyzer")
    print("Identifying migration artifacts and cleanup candidates")
    print()
    
    conn, db_type = get_database_connection()
    if not conn:
        print("❌ Could not connect to database. Check your configuration.")
        return
    
    print(f"✅ Connected to database ({db_type})")
    print()
    
    try:
        analyze_test_projects(conn)
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
    finally:
        conn.close()
        print("\nDatabase connection closed.")

if __name__ == "__main__":
    main()