#!/usr/bin/env python3
"""
Enhanced Migration Runner for Review Platform
Supports multiple environments and database management
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from typing import List, Optional
import subprocess
from datetime import datetime

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import get_environment, load_environment_config
from app.db.database import engine
from app.db.models import Base
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self, environment: str = None):
        self.environment = environment or get_environment()
        self.settings = load_environment_config()
        self.migrations_dir = Path(__file__).parent / "migrations"
        
        logger.info(f"Migration runner initialized for environment: {self.environment}")
        logger.info(f"Database URL: {self.settings.DATABASE_URL}")
        
    def create_database_if_not_exists(self):
        """Create database if it doesn't exist (PostgreSQL only)"""
        if not self.settings.DATABASE_URL.startswith('postgresql'):
            logger.info("Not PostgreSQL, skipping database creation")
            return
            
        try:
            # Extract database name from URL
            db_url_parts = self.settings.DATABASE_URL.split('/')
            db_name = db_url_parts[-1]
            base_url = '/'.join(db_url_parts[:-1]) + '/postgres'
            
            # Connect to postgres database to create target database
            temp_engine = create_engine(base_url)
            
            with temp_engine.connect() as conn:
                # Set autocommit mode for database creation
                conn.execute(text("COMMIT"))
                
                # Check if database exists
                result = conn.execute(
                    text("SELECT 1 FROM pg_database WHERE datname = :db_name"),
                    {"db_name": db_name}
                )
                
                if not result.fetchone():
                    logger.info(f"Creating database: {db_name}")
                    conn.execute(text(f"CREATE DATABASE \"{db_name}\""))
                    logger.info(f"Database {db_name} created successfully")
                else:
                    logger.info(f"Database {db_name} already exists")
                    
            temp_engine.dispose()
            
        except Exception as e:
            logger.error(f"Failed to create database: {e}")
            raise
    
    def create_tables(self):
        """Create all tables using SQLAlchemy models"""
        try:
            logger.info("Creating tables from SQLAlchemy models...")
            Base.metadata.create_all(bind=engine)
            logger.info("Tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def get_migration_files(self) -> List[Path]:
        """Get all SQL migration files in order"""
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return []
        
        sql_files = list(self.migrations_dir.glob("*.sql"))
        # Sort by filename to ensure proper order
        sql_files.sort()
        
        logger.info(f"Found {len(sql_files)} migration files")
        return sql_files
    
    def execute_sql_file(self, sql_file: Path):
        """Execute a SQL migration file"""
        logger.info(f"Executing migration: {sql_file.name}")
        
        try:
            with open(sql_file, 'r') as f:
                sql_content = f.read()
            
            # Split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
            
            with engine.connect() as conn:
                # Start transaction
                trans = conn.begin()
                try:
                    for statement in statements:
                        if statement:
                            logger.debug(f"Executing: {statement[:100]}...")
                            conn.execute(text(statement))
                    
                    trans.commit()
                    logger.info(f"Migration {sql_file.name} completed successfully")
                    
                except Exception as e:
                    trans.rollback()
                    logger.error(f"Migration {sql_file.name} failed: {e}")
                    raise
                    
        except Exception as e:
            logger.error(f"Failed to execute {sql_file.name}: {e}")
            raise
    
    def run_migrations(self, specific_file: Optional[str] = None):
        """Run database migrations"""
        migration_files = self.get_migration_files()
        
        if not migration_files:
            logger.info("No migration files found")
            return
        
        if specific_file:
            # Run specific migration file
            target_file = self.migrations_dir / specific_file
            if target_file.exists():
                self.execute_sql_file(target_file)
            else:
                logger.error(f"Migration file not found: {specific_file}")
                raise FileNotFoundError(f"Migration file not found: {specific_file}")
        else:
            # Run all migrations
            for migration_file in migration_files:
                try:
                    self.execute_sql_file(migration_file)
                except Exception as e:
                    logger.error(f"Migration failed, stopping at {migration_file.name}")
                    raise
    
    def backup_database(self) -> Optional[str]:
        """Create database backup (PostgreSQL only)"""
        if not self.settings.DATABASE_URL.startswith('postgresql'):
            logger.info("Not PostgreSQL, skipping backup")
            return None
        
        try:
            # Create backup directory
            backup_dir = Path("/opt/backups") if Path("/opt/backups").exists() else Path("/tmp/backups")
            backup_dir.mkdir(exist_ok=True)
            
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            db_name = self.settings.DATABASE_URL.split('/')[-1]
            backup_file = backup_dir / f"{db_name}_{self.environment}_{timestamp}.sql"
            
            logger.info(f"Creating database backup: {backup_file}")
            
            # Run pg_dump
            result = subprocess.run([
                "pg_dump",
                self.settings.DATABASE_URL,
                "-f", str(backup_file)
            ], capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Database backup created: {backup_file}")
                return str(backup_file)
            else:
                logger.error(f"pg_dump failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return None
    
    def test_database_connection(self):
        """Test database connection"""
        try:
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    def get_database_info(self):
        """Get database information"""
        try:
            with engine.connect() as conn:
                # Get database version
                if self.settings.DATABASE_URL.startswith('postgresql'):
                    result = conn.execute(text("SELECT version()"))
                    version = result.fetchone()[0]
                    logger.info(f"Database version: {version}")
                    
                    # Get table count
                    result = conn.execute(text(
                        "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"
                    ))
                    table_count = result.fetchone()[0]
                    logger.info(f"Number of tables: {table_count}")
                    
                else:
                    result = conn.execute(text("SELECT sqlite_version()"))
                    version = result.fetchone()[0]
                    logger.info(f"SQLite version: {version}")
                    
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")

def main():
    parser = argparse.ArgumentParser(description="Enhanced Migration Runner for Review Platform")
    parser.add_argument(
        "--environment", "-e",
        choices=["development", "staging", "production"],
        help="Target environment"
    )
    parser.add_argument(
        "--create-db",
        action="store_true",
        help="Create database if it doesn't exist"
    )
    parser.add_argument(
        "--create-tables",
        action="store_true", 
        help="Create tables from SQLAlchemy models"
    )
    parser.add_argument(
        "--run-migrations",
        action="store_true",
        help="Run SQL migration files"
    )
    parser.add_argument(
        "--migration-file",
        help="Run specific migration file"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create database backup before operations"
    )
    parser.add_argument(
        "--test-connection",
        action="store_true",
        help="Test database connection"
    )
    parser.add_argument(
        "--info",
        action="store_true", 
        help="Show database information"
    )
    parser.add_argument(
        "--full-setup",
        action="store_true",
        help="Complete setup: create DB, tables, and run migrations"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Set environment variable if specified
    if args.environment:
        os.environ["ENVIRONMENT"] = args.environment
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    
    try:
        runner = MigrationRunner(args.environment)
        
        # Test connection first
        if not runner.test_database_connection() and not args.create_db:
            logger.error("Database connection failed. Use --create-db to create database.")
            sys.exit(1)
        
        # Create backup if requested
        if args.backup and not args.dry_run:
            runner.backup_database()
        
        # Execute operations
        if args.create_db:
            if args.dry_run:
                logger.info("Would create database if it doesn't exist")
            else:
                runner.create_database_if_not_exists()
        
        if args.create_tables:
            if args.dry_run:
                logger.info("Would create tables from SQLAlchemy models")
            else:
                runner.create_tables()
        
        if args.run_migrations:
            if args.dry_run:
                migration_files = runner.get_migration_files()
                logger.info(f"Would run {len(migration_files)} migration files")
                for f in migration_files:
                    logger.info(f"  - {f.name}")
            else:
                runner.run_migrations(args.migration_file)
        
        if args.full_setup:
            if args.dry_run:
                logger.info("Would perform full setup: create DB, tables, and migrations")
            else:
                logger.info("Performing full database setup...")
                runner.create_database_if_not_exists()
                runner.create_tables()
                runner.run_migrations()
                logger.info("Full setup completed successfully")
        
        if args.test_connection:
            runner.test_database_connection()
        
        if args.info:
            runner.get_database_info()
        
        # If no specific actions requested, show help
        if not any([
            args.create_db, args.create_tables, args.run_migrations,
            args.test_connection, args.info, args.full_setup
        ]):
            parser.print_help()
            
    except Exception as e:
        logger.error(f"Migration runner failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()