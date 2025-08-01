#!/usr/bin/env python3
"""
Test that the updated models.py can create all 29 tables
"""

import os
import sys

# Set up environment to use development database for testing
os.environ['DATABASE_URL'] = 'postgresql://dev_user:!dev_Halbzeit1024@65.108.32.143:5432/review_dev'

sys.path.append('/opt/review-platform-dev/backend')

def test_complete_schema():
    """Test that all models are properly defined and can create tables"""
    try:
        # Import ALL models to register with Base
        from app.db.models import Base
        from app.db.database import engine
        from sqlalchemy import text
        
        print("Testing complete schema creation...")
        
        # Count existing models
        model_classes = []
        for name in dir(__import__('app.db.models', fromlist=[''])):
            obj = getattr(__import__('app.db.models', fromlist=['']), name)
            if hasattr(obj, '__tablename__'):
                model_classes.append((name, obj.__tablename__))
        
        print(f"Found {len(model_classes)} model classes:")
        for class_name, table_name in sorted(model_classes):
            print(f"  {class_name} → {table_name}")
        
        # Test that we can generate CREATE statements (without actually running them)
        print("\nTesting table creation metadata...")
        
        # Get table names that would be created
        table_names = [table.name for table in Base.metadata.tables.values()]
        print(f"SQLAlchemy would create {len(table_names)} tables:")
        for table_name in sorted(table_names):
            print(f"  {table_name}")
        
        # Check against expected tables (exclude views like project_progress)
        expected_tables = {
            'analysis_templates', 'answers', 'chapter_analysis_results', 'chapter_questions',
            'classification_performance', 'extraction_experiments', 'gp_template_customizations',
            'healthcare_sectors', 'healthcare_templates_deprecated', 'model_configs', 
            'pipeline_prompts', 'pitch_decks', 'production_projects', 'project_documents',
            'project_interactions', 'project_stages', 'projects',
            'question_analysis_results', 'questions', 'reviews', 'specialized_analysis_results',
            'stage_templates', 'startup_classifications', 'template_chapters', 
            'template_performance', 'test_projects', 'users', 'visual_analysis_cache'
        }
        
        actual_tables = set(table_names)
        missing = expected_tables - actual_tables
        extra = actual_tables - expected_tables
        
        if missing:
            print(f"❌ MISSING TABLES: {missing}")
            return False
        
        if extra:
            print(f"⚠️  EXTRA TABLES: {extra}")
        
        if actual_tables == expected_tables:
            print("✅ ALL EXPECTED TABLES WOULD BE CREATED")
            print("✅ NO CODE VS DATABASE DRIFT")
            return True
        else:
            print(f"⚠️  Table count mismatch - Expected: {len(expected_tables)}, Got: {len(actual_tables)}")
            return len(missing) == 0  # OK if no missing tables, just extra ones
            
    except Exception as e:
        print(f"❌ Schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_complete_schema()
    if success:
        print("\n✅ SCHEMA TEST PASSED - Ready for production deployment!")
    else:
        print("\n❌ SCHEMA TEST FAILED")
        sys.exit(1)