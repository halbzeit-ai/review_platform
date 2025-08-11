#!/usr/bin/env python3
"""
Database and Models Synchronization Checker
Compares SQLAlchemy models with actual database schema and reports discrepancies.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.core.config import settings
from app.db.models import Base
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker
import logging
from typing import Set, Dict, List, Tuple

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseSyncChecker:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        self.inspector = inspect(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
    
    def get_model_tables(self) -> Dict[str, Set[str]]:
        """Get all tables and columns defined in models.py"""
        model_tables = {}
        for model_class in Base.__subclasses__():
            table_name = model_class.__tablename__
            columns = set()
            for column in model_class.__table__.columns:
                columns.add(column.name)
            model_tables[table_name] = columns
        return model_tables
    
    def get_database_tables(self) -> Dict[str, Set[str]]:
        """Get all tables and columns from the actual database"""
        db_tables = {}
        for table_name in self.inspector.get_table_names():
            columns = set()
            for column in self.inspector.get_columns(table_name):
                columns.add(column['name'])
            db_tables[table_name] = columns
        return db_tables
    
    def compare_tables(self) -> Tuple[Set[str], Set[str], Set[str]]:
        """Compare tables between models and database"""
        model_tables = set(self.get_model_tables().keys())
        db_tables = set(self.get_database_tables().keys())
        
        only_in_models = model_tables - db_tables
        only_in_db = db_tables - model_tables
        in_both = model_tables & db_tables
        
        return only_in_models, only_in_db, in_both
    
    def compare_columns(self, table_name: str) -> Tuple[Set[str], Set[str]]:
        """Compare columns for a specific table"""
        model_tables = self.get_model_tables()
        db_tables = self.get_database_tables()
        
        model_columns = model_tables.get(table_name, set())
        db_columns = db_tables.get(table_name, set())
        
        only_in_model = model_columns - db_columns
        only_in_db = db_columns - model_columns
        
        return only_in_model, only_in_db
    
    def check_foreign_keys(self) -> List[Dict]:
        """Check foreign key consistency"""
        issues = []
        with self.SessionLocal() as db:
            # Get all foreign keys from database
            result = db.execute(text("""
                SELECT 
                    tc.table_name, 
                    kcu.column_name, 
                    ccu.table_name AS foreign_table_name,
                    ccu.column_name AS foreign_column_name
                FROM information_schema.table_constraints AS tc 
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                ORDER BY tc.table_name, kcu.column_name
            """)).fetchall()
            
            for row in result:
                table, column, ref_table, ref_column = row
                # Check if referenced table exists in models
                model_tables = self.get_model_tables()
                if ref_table not in model_tables:
                    issues.append({
                        'table': table,
                        'column': column,
                        'issue': f'References missing table {ref_table}'
                    })
        
        return issues
    
    def generate_report(self) -> str:
        """Generate a comprehensive sync report"""
        report = []
        report.append("=" * 80)
        report.append("DATABASE SYNCHRONIZATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Get data
        model_tables_dict = self.get_model_tables()
        db_tables_dict = self.get_database_tables()
        only_in_models, only_in_db, in_both = self.compare_tables()
        
        # Summary
        report.append("SUMMARY")
        report.append("-" * 40)
        report.append(f"Tables in models.py: {len(model_tables_dict)}")
        report.append(f"Tables in database: {len(db_tables_dict)}")
        report.append(f"Tables in both: {len(in_both)}")
        report.append("")
        
        # Tables only in models
        if only_in_models:
            report.append("⚠️  TABLES ONLY IN MODELS.PY (not in database)")
            report.append("-" * 40)
            for table in sorted(only_in_models):
                report.append(f"  - {table}")
            report.append("")
        
        # Tables only in database
        if only_in_db:
            report.append("⚠️  TABLES ONLY IN DATABASE (not in models.py)")
            report.append("-" * 40)
            for table in sorted(only_in_db):
                report.append(f"  - {table}")
            report.append("")
        
        # Column mismatches
        column_issues = []
        for table in in_both:
            only_in_model, only_in_db = self.compare_columns(table)
            if only_in_model or only_in_db:
                column_issues.append((table, only_in_model, only_in_db))
        
        if column_issues:
            report.append("⚠️  COLUMN MISMATCHES")
            report.append("-" * 40)
            for table, model_cols, db_cols in column_issues:
                report.append(f"\nTable: {table}")
                if model_cols:
                    report.append(f"  Columns only in model: {', '.join(sorted(model_cols))}")
                if db_cols:
                    report.append(f"  Columns only in database: {', '.join(sorted(db_cols))}")
            report.append("")
        
        # Foreign key issues
        fk_issues = self.check_foreign_keys()
        if fk_issues:
            report.append("⚠️  FOREIGN KEY ISSUES")
            report.append("-" * 40)
            for issue in fk_issues:
                report.append(f"  {issue['table']}.{issue['column']}: {issue['issue']}")
            report.append("")
        
        # Status
        if not only_in_models and not only_in_db and not column_issues and not fk_issues:
            report.append("✅ DATABASE AND MODELS ARE IN SYNC!")
        else:
            report.append("❌ SYNCHRONIZATION ISSUES FOUND")
            report.append("")
            report.append("RECOMMENDED ACTIONS:")
            if only_in_models:
                report.append("  - Run migrations to create missing database tables")
            if only_in_db:
                report.append("  - Add models for database tables or drop unused tables")
            if column_issues:
                report.append("  - Update models or run migrations to sync columns")
        
        return "\n".join(report)
    
    def generate_fixes(self) -> List[str]:
        """Generate SQL commands to fix discrepancies"""
        fixes = []
        only_in_models, only_in_db, in_both = self.compare_tables()
        
        # Generate CREATE TABLE for tables only in models
        if only_in_models:
            fixes.append("-- Tables to create in database:")
            for table in only_in_models:
                fixes.append(f"-- TODO: Generate CREATE TABLE for {table}")
        
        # Generate DROP TABLE for tables only in database
        if only_in_db:
            fixes.append("\n-- Tables to drop from database (or add to models):")
            for table in only_in_db:
                fixes.append(f"-- DROP TABLE IF EXISTS {table} CASCADE;")
        
        # Column fixes
        for table in in_both:
            only_in_model, only_in_db = self.compare_columns(table)
            if only_in_model:
                fixes.append(f"\n-- Columns to add to {table}:")
                for col in only_in_model:
                    fixes.append(f"-- ALTER TABLE {table} ADD COLUMN {col} TYPE;")
            if only_in_db:
                fixes.append(f"\n-- Columns to drop from {table} (or add to model):")
                for col in only_in_db:
                    fixes.append(f"-- ALTER TABLE {table} DROP COLUMN {col};")
        
        return fixes

def main():
    checker = DatabaseSyncChecker()
    
    # Generate and print report
    report = checker.generate_report()
    print(report)
    
    # Check if fixes are needed
    only_in_models, only_in_db, _ = checker.compare_tables()
    if only_in_models or only_in_db:
        print("\n" + "=" * 80)
        print("SUGGESTED SQL FIXES")
        print("=" * 80)
        fixes = checker.generate_fixes()
        for fix in fixes:
            print(fix)
    
    # Exit with appropriate code
    model_tables = checker.get_model_tables()
    db_tables = checker.get_database_tables()
    if len(model_tables) == len(db_tables) and set(model_tables.keys()) == set(db_tables.keys()):
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Issues found

if __name__ == "__main__":
    main()