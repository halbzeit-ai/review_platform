#!/usr/bin/env python3
"""
Deploy the robust processing queue system to the database.

This script runs the SQL migration to create the persistent task queue system
that handles server restarts gracefully.
"""

import os
import sys
import logging
from pathlib import Path

# Add backend to Python path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.db.database import SessionLocal, engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def run_migration():
    """Run the processing queue system migration"""
    
    migration_file = Path(__file__).parent.parent / "migrations" / "create_processing_queue_system.sql"
    
    if not migration_file.exists():
        logger.error(f"Migration file not found: {migration_file}")
        return False
    
    logger.info(f"Running migration: {migration_file}")
    
    try:
        # Read migration SQL
        with open(migration_file, 'r') as f:
            migration_sql = f.read()
        
        # Execute migration
        db = SessionLocal()
        try:
            # Split SQL into individual statements (PostgreSQL functions need to be executed separately)
            statements = []
            current_statement = []
            in_function = False
            
            for line in migration_sql.split('\n'):
                line = line.strip()
                
                # Skip empty lines and comments at start of line
                if not line or line.startswith('--'):
                    continue
                
                current_statement.append(line)
                
                # Check for function definitions
                if 'CREATE OR REPLACE FUNCTION' in line:
                    in_function = True
                elif in_function and line.endswith('$$ LANGUAGE plpgsql;'):
                    in_function = False
                    statements.append('\n'.join(current_statement))
                    current_statement = []
                elif not in_function and line.endswith(';'):
                    statements.append('\n'.join(current_statement))
                    current_statement = []
            
            # Add any remaining statement
            if current_statement:
                statements.append('\n'.join(current_statement))
            
            # Execute each statement
            for i, statement in enumerate(statements):
                if statement.strip():
                    try:
                        logger.info(f"Executing statement {i+1}/{len(statements)}")
                        logger.debug(f"Statement preview: {statement[:100]}...")
                        db.execute(text(statement))
                        db.commit()
                        logger.info(f"Statement {i+1} executed successfully")
                    except Exception as e:
                        logger.error(f"Error executing statement {i+1}: {e}")
                        logger.debug(f"Failed statement: {statement}")
                        db.rollback()
                        # Continue with other statements - some might be "IF NOT EXISTS"
            
            logger.info("Migration completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            db.rollback()
            return False
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Failed to read migration file: {e}")
        return False

def verify_migration():
    """Verify that the migration was applied correctly"""
    
    logger.info("Verifying migration...")
    
    verification_queries = [
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'processing_queue'",
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'processing_progress'", 
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'processing_servers'",
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'task_dependencies'",
        "SELECT COUNT(*) FROM information_schema.routines WHERE routine_name = 'cleanup_expired_locks'",
        "SELECT COUNT(*) FROM information_schema.routines WHERE routine_name = 'get_next_processing_task'",
        "SELECT COUNT(*) FROM information_schema.routines WHERE routine_name = 'update_task_progress'",
        "SELECT COUNT(*) FROM information_schema.routines WHERE routine_name = 'complete_task'",
        "SELECT COUNT(*) FROM information_schema.routines WHERE routine_name = 'retry_failed_task'",
    ]
    
    expected_results = [1, 1, 1, 1, 1, 1, 1, 1, 1]  # Each should return 1 (exists)
    
    try:
        db = SessionLocal()
        try:
            for i, query in enumerate(verification_queries):
                result = db.execute(text(query)).fetchone()
                count = result[0] if result else 0
                
                if count == expected_results[i]:
                    logger.info(f"✅ Verification {i+1}/9 passed")
                else:
                    logger.error(f"❌ Verification {i+1}/9 failed: {query}")
                    return False
            
            # Test that we can call the functions
            logger.info("Testing function calls...")
            
            # Test cleanup function
            result = db.execute(text("SELECT cleanup_expired_locks()")).fetchone()
            logger.info(f"✅ cleanup_expired_locks() returned: {result[0]}")
            
            logger.info("🎉 All verifications passed! Processing queue system is ready.")
            return True
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Database connection failed during verification: {e}")
        return False

def main():
    """Main migration runner"""
    
    logger.info("=== Processing Queue System Migration ===")
    logger.info("This will create a robust task queue system that survives server restarts")
    
    # Check database connection
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("✅ Database connection successful")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        logger.error("Please check your database configuration and ensure PostgreSQL is running")
        return 1
    
    # Run migration
    if not run_migration():
        logger.error("❌ Migration failed")
        return 1
    
    # Verify migration
    if not verify_migration():
        logger.error("❌ Migration verification failed")
        return 1
    
    logger.info("🎉 Processing queue system deployed successfully!")
    logger.info("Next steps:")
    logger.info("1. Update backend to use robust processing API")
    logger.info("2. Create systemd service for processing worker")
    logger.info("3. Test with actual uploads")
    
    return 0

if __name__ == "__main__":
    exit(main())