#!/usr/bin/env python3
"""
Comprehensive verification script to ensure complete elimination of pitch_deck_id references
and alignment between database schema, models.py, and backend code.

This script checks:
1. Database schema for any pitch_deck_id columns or pitch_decks tables
2. Models.py for any pitch_deck_id references
3. Backend code for any pitch_deck_id references (excluding archives/tests)
4. Alignment between database and models
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import List, Dict, Tuple

# Add backend to path to import models
sys.path.append('/opt/review-platform/backend')

try:
    import psycopg2
    from sqlalchemy import create_engine, text, inspect
    from sqlalchemy.orm import sessionmaker
    from app.core.config import settings
    from app.db.models import Base
except ImportError as e:
    print(f"❌ Error importing required modules: {e}")
    print("Make sure you're running this from the correct environment with dependencies installed")
    sys.exit(1)

class PitchDeckCleanupVerifier:
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.success_count = 0
        self.total_checks = 0
        
        # Database connection
        try:
            self.engine = create_engine(settings.DATABASE_URL)
            self.inspector = inspect(self.engine)
        except Exception as e:
            print(f"❌ Failed to connect to database: {e}")
            sys.exit(1)
    
    def log_error(self, message: str):
        self.errors.append(message)
        print(f"❌ {message}")
    
    def log_warning(self, message: str):
        self.warnings.append(message)
        print(f"⚠️  {message}")
    
    def log_success(self, message: str):
        self.success_count += 1
        print(f"✅ {message}")
    
    def check_database_schema(self):
        """Check database for any pitch_deck_id columns or pitch_decks tables"""
        print("\n🔍 Checking Database Schema...")
        self.total_checks += 1
        
        with self.engine.connect() as conn:
            # Check for pitch_decks tables
            tables_query = text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' AND tablename LIKE '%pitch%'
            """)
            pitch_tables = conn.execute(tables_query).fetchall()
            
            if pitch_tables:
                for table in pitch_tables:
                    self.log_error(f"Found pitch_deck related table: {table[0]}")
            else:
                self.log_success("No pitch_deck related tables found")
            
            # Check for pitch_deck_id columns
            columns_query = text("""
                SELECT table_name, column_name, data_type 
                FROM information_schema.columns 
                WHERE column_name LIKE '%pitch_deck%'
                AND table_schema = 'public'
            """)
            pitch_columns = conn.execute(columns_query).fetchall()
            
            if pitch_columns:
                for table, column, dtype in pitch_columns:
                    self.log_error(f"Found pitch_deck column: {table}.{column} ({dtype})")
            else:
                self.log_success("No pitch_deck_id columns found in database")
                
            # Check for required document_id columns in key tables
            required_tables = ['visual_analysis_cache', 'specialized_analysis_results', 
                             'question_analysis_results', 'chapter_analysis_results',
                             'startup_classifications', 'template_performance', 'slide_feedback']
            
            for table in required_tables:
                check_query = text(f"""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_name = '{table}' AND column_name = 'document_id'
                    AND table_schema = 'public'
                """)
                result = conn.execute(check_query).fetchone()
                if result:
                    self.log_success(f"Table {table} has document_id column")
                else:
                    if table in [t.name for t in self.inspector.get_table_names()]:
                        self.log_error(f"Table {table} exists but missing document_id column")
                    else:
                        self.log_warning(f"Table {table} does not exist")
    
    def check_models_py(self):
        """Check models.py for any pitch_deck_id references"""
        print("\n🔍 Checking Models.py...")
        self.total_checks += 1
        
        models_path = Path('/opt/review-platform/backend/app/db/models.py')
        if not models_path.exists():
            self.log_error("models.py not found")
            return
            
        with open(models_path, 'r') as f:
            content = f.read()
            
        # Check for pitch_deck_id references (excluding comments about document types)
        lines = content.split('\n')
        pitch_deck_refs = []
        
        for i, line in enumerate(lines, 1):
            if 'pitch_deck_id' in line.lower() and not ('pitch_deck, financial_report' in line):
                pitch_deck_refs.append(f"Line {i}: {line.strip()}")
        
        if pitch_deck_refs:
            for ref in pitch_deck_refs:
                self.log_error(f"Found pitch_deck_id reference in models.py: {ref}")
        else:
            self.log_success("No pitch_deck_id references found in models.py")
    
    def check_backend_code(self):
        """Check backend code for pitch_deck_id references"""
        print("\n🔍 Checking Backend Code...")
        self.total_checks += 1
        
        backend_path = Path('/opt/review-platform/backend')
        excluded_paths = ['archive', 'tests', '__pycache__', '.git']
        
        pitch_deck_files = []
        
        for py_file in backend_path.rglob('*.py'):
            # Skip excluded directories
            if any(excluded in str(py_file) for excluded in excluded_paths):
                continue
                
            try:
                with open(py_file, 'r') as f:
                    content = f.read()
                    
                if 'pitch_deck_id' in content:
                    # Find specific lines
                    lines = content.split('\n')
                    for i, line in enumerate(lines, 1):
                        if 'pitch_deck_id' in line and not line.strip().startswith('#'):
                            pitch_deck_files.append(f"{py_file}:{i} - {line.strip()}")
            except Exception as e:
                self.log_warning(f"Could not read {py_file}: {e}")
        
        if pitch_deck_files:
            for ref in pitch_deck_files:
                self.log_error(f"Found pitch_deck_id reference: {ref}")
        else:
            self.log_success("No pitch_deck_id references found in active backend code")
    
    def check_database_model_alignment(self):
        """Check that database schema aligns with SQLAlchemy models"""
        print("\n🔍 Checking Database-Model Alignment...")
        self.total_checks += 1
        
        # Get all model classes that have document_id
        model_classes = []
        for name in dir(Base.registry._class_registry):
            cls = Base.registry._class_registry[name]
            if hasattr(cls, '__table__') and hasattr(cls, 'document_id'):
                model_classes.append(cls)
        
        alignment_errors = []
        
        with self.engine.connect() as conn:
            for model_cls in model_classes:
                table_name = model_cls.__tablename__
                
                # Check if table exists in database
                if table_name not in self.inspector.get_table_names():
                    alignment_errors.append(f"Model {model_cls.__name__} references table {table_name} which doesn't exist")
                    continue
                
                # Check if document_id column exists and has correct type
                columns = {col['name']: col for col in self.inspector.get_columns(table_name)}
                
                if 'document_id' not in columns:
                    alignment_errors.append(f"Table {table_name} missing document_id column required by model {model_cls.__name__}")
                elif str(columns['document_id']['type']) != 'INTEGER':
                    alignment_errors.append(f"Table {table_name}.document_id has wrong type: {columns['document_id']['type']} (expected INTEGER)")
                else:
                    self.log_success(f"Table {table_name} properly aligned with model {model_cls.__name__}")
        
        if alignment_errors:
            for error in alignment_errors:
                self.log_error(error)
        
        self.total_checks += len(model_classes)
    
    def check_gpu_code(self):
        """Check GPU processing code for compatibility"""
        print("\n🔍 Checking GPU Code Compatibility...")
        self.total_checks += 1
        
        gpu_path = Path('/opt/review-platform/gpu_processing')
        main_files = ['gpu_http_server.py', 'main.py']
        
        all_compatible = True
        
        for filename in main_files:
            file_path = gpu_path / filename
            if not file_path.exists():
                self.log_warning(f"GPU file {filename} not found")
                continue
                
            with open(file_path, 'r') as f:
                content = f.read()
                
            # Check for backwards compatibility handling
            if 'document_id' in content and ('pitch_deck_id' in content or 'data.get(\'document_id\', data.get(\'pitch_deck_id\'))' in content):
                self.log_success(f"GPU file {filename} has backwards compatibility for document_id")
            elif 'document_id' in content:
                self.log_success(f"GPU file {filename} uses document_id")
            else:
                self.log_error(f"GPU file {filename} may not support document_id parameter")
                all_compatible = False
        
        if all_compatible:
            self.log_success("GPU processing code is compatible with document_id")
    
    def run_all_checks(self):
        """Run all verification checks"""
        print("🚀 Starting Comprehensive Pitch Deck Cleanup Verification\n")
        print("="*60)
        
        self.check_database_schema()
        self.check_models_py()
        self.check_backend_code()
        self.check_database_model_alignment()
        self.check_gpu_code()
        
        print("\n" + "="*60)
        print(f"\n📊 VERIFICATION SUMMARY")
        print(f"Total Checks: {self.total_checks}")
        print(f"✅ Successful: {self.success_count}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"❌ Errors: {len(self.errors)}")
        
        if self.errors:
            print(f"\n❌ CRITICAL ISSUES FOUND:")
            for error in self.errors:
                print(f"   • {error}")
            print(f"\n🚨 System is NOT ready - fix these issues before proceeding!")
            return False
        elif self.warnings:
            print(f"\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   • {warning}")
            print(f"\n✅ System appears ready but review warnings!")
            return True
        else:
            print(f"\n🎉 PERFECT! All checks passed - system is fully clean of pitch_deck_id references!")
            print(f"✅ Database, models, and code are properly aligned using document_id")
            return True

if __name__ == "__main__":
    verifier = PitchDeckCleanupVerifier()
    success = verifier.run_all_checks()
    sys.exit(0 if success else 1)