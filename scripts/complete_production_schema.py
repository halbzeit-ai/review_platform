#!/usr/bin/env python3
"""
COMPLETE production database schema creation
Creates ALL 29 tables from development with proper schema
"""

import os
import sys

# Set production environment
os.environ['DATABASE_URL'] = 'postgresql://review_user:SecureProductionPassword2024!@localhost:5432/review-platform'

sys.path.append('/opt/review-platform/backend')

def create_complete_schema():
    """Create ALL tables with complete schema"""
    try:
        # Import ALL models to register with Base
        from app.db.models import (
            Base, User, PitchDeck, Review, Question, Answer, Project, 
            ProjectDocument, ProjectInteraction, ProjectProgress, ProjectStage,
            StageTemplate, VisualAnalysisCache, ExtractionExperiment,
            AnalysisTemplate, TemplateChapter, ChapterQuestion, 
            GPTemplateCustomization, HealthcareSector, ModelConfig,
            PipelinePrompt, ChapterAnalysisResult, QuestionAnalysisResult,
            SpecializedAnalysisResult, ClassificationPerformance,
            TemplatePerformance, StartupClassification, ProductionProject,
            TestProject
        )
        from app.db.database import engine
        
        print("Creating ALL database tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Verify all tables were created
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name"))
            tables = [row[0] for row in result.fetchall()]
            
        print(f"✅ Created {len(tables)} tables:")
        for i, table in enumerate(tables, 1):
            print(f"  {i:2d}. {table}")
            
        expected_tables = [
            'analysis_templates', 'answers', 'chapter_analysis_results', 'chapter_questions',
            'classification_performance', 'extraction_experiments', 'gp_template_customizations',
            'healthcare_sectors', 'model_configs', 'pipeline_prompts', 'pitch_decks',
            'production_projects', 'project_documents', 'project_interactions',
            'project_progress', 'project_stages', 'projects', 'question_analysis_results',
            'questions', 'reviews', 'specialized_analysis_results', 'stage_templates',
            'startup_classifications', 'template_chapters', 'template_performance',
            'test_projects', 'users', 'visual_analysis_cache'
        ]
        
        missing_tables = set(expected_tables) - set(tables)
        if missing_tables:
            print(f"❌ MISSING TABLES: {missing_tables}")
            return False
        else:
            print("✅ ALL EXPECTED TABLES CREATED")
            return True
            
    except Exception as e:
        print(f"❌ Schema creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = create_complete_schema()
    if not success:
        sys.exit(1)
    print("✅ PRODUCTION DATABASE SCHEMA COMPLETE")