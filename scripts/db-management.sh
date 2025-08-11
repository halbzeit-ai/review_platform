#!/bin/bash
# Database Management Helper Script
# Provides easy commands for database and model synchronization

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

function print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}"
}

function print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

function print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

function print_error() {
    echo -e "${RED}❌ $1${NC}"
}

function check_sync() {
    print_header "Checking Database/Model Synchronization"
    python "$SCRIPT_DIR/db_sync_check.py"
}

function auto_sync() {
    print_header "Auto-Sync Database with Models"
    
    # First check current state
    python "$SCRIPT_DIR/db_sync_check.py" > /tmp/sync_report.txt 2>&1
    
    if [ $? -eq 0 ]; then
        print_success "Already in sync!"
        return 0
    fi
    
    print_warning "Out of sync - generating migration..."
    
    cd "$PROJECT_ROOT/backend"
    
    # Generate migration
    alembic revision --autogenerate -m "Auto-sync models and database" 2>/dev/null || {
        print_error "Failed to generate migration. Setting up Alembic..."
        "$SCRIPT_DIR/setup_alembic.sh"
        alembic revision --autogenerate -m "Auto-sync models and database"
    }
    
    print_success "Migration generated. Review and apply with: alembic upgrade head"
}

function create_model_from_table() {
    local table_name=$1
    
    if [ -z "$table_name" ]; then
        echo "Usage: $0 create-model <table_name>"
        exit 1
    fi
    
    print_header "Generating Model for Table: $table_name"
    
    python << EOF
import sys
import os
sys.path.append('$PROJECT_ROOT/backend')

from app.core.config import settings
from sqlalchemy import create_engine, inspect, MetaData
from sqlalchemy.ext.automap import automap_base

engine = create_engine(settings.DATABASE_URL)
metadata = MetaData()
metadata.reflect(engine, only=['$table_name'])

if '$table_name' not in metadata.tables:
    print("Table '$table_name' not found in database")
    sys.exit(1)

table = metadata.tables['$table_name']

# Generate model code
model_code = []
model_code.append(f"class {table.name.title().replace('_', '')}(Base):")
model_code.append(f'    __tablename__ = "{table.name}"')
model_code.append('    ')

for column in table.columns:
    col_def = f"    {column.name} = Column("
    
    # Add type
    col_type = str(column.type).split('(')[0]
    if 'VARCHAR' in str(column.type).upper():
        col_def += "String"
    elif 'INT' in str(column.type).upper():
        col_def += "Integer"
    elif 'TEXT' in str(column.type).upper():
        col_def += "Text"
    elif 'TIMESTAMP' in str(column.type).upper():
        col_def += "DateTime"
    elif 'BOOL' in str(column.type).upper():
        col_def += "Boolean"
    else:
        col_def += str(column.type)
    
    # Add constraints
    if column.primary_key:
        col_def += ", primary_key=True"
    if column.index:
        col_def += ", index=True"
    if not column.nullable:
        col_def += ", nullable=False"
    if column.default:
        col_def += f", default={column.default}"
    
    col_def += ")"
    model_code.append(col_def)

print("Generated Model:")
print("=" * 50)
for line in model_code:
    print(line)
print("=" * 50)
print("Add this to your models.py file")
EOF
}

function list_orphan_tables() {
    print_header "Tables Without Models"
    
    python << EOF
import sys
sys.path.append('$PROJECT_ROOT/backend')

from app.core.config import settings
from app.db.models import Base
from sqlalchemy import create_engine, inspect

engine = create_engine(settings.DATABASE_URL)
inspector = inspect(engine)

model_tables = {model.__tablename__ for model in Base.__subclasses__()}
db_tables = set(inspector.get_table_names())

orphan_tables = db_tables - model_tables

if orphan_tables:
    print("Tables in database but not in models.py:")
    for table in sorted(orphan_tables):
        print(f"  - {table}")
    print("\nTo create models for these tables, run:")
    for table in sorted(orphan_tables):
        print(f"  $0 create-model {table}")
else:
    print("✅ All database tables have corresponding models")
EOF
}

function validate_foreign_keys() {
    print_header "Validating Foreign Keys"
    
    python << EOF
import sys
sys.path.append('$PROJECT_ROOT/backend')

from app.core.config import settings
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

engine = create_engine(settings.DATABASE_URL)
Session = sessionmaker(bind=engine)

with Session() as db:
    # Check for orphaned foreign keys
    result = db.execute(text("""
        SELECT 
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name
        FROM information_schema.table_constraints AS tc 
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND ccu.table_name NOT IN (
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        )
    """)).fetchall()
    
    if result:
        print("⚠️  Foreign keys referencing non-existent tables:")
        for row in result:
            print(f"  {row[0]}.{row[1]} -> {row[2]}")
    else:
        print("✅ All foreign keys are valid")
EOF
}

function show_help() {
    print_header "Database Management Commands"
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  check         - Check if database and models are in sync"
    echo "  auto-sync     - Generate Alembic migration to sync database"
    echo "  orphans       - List database tables without models"
    echo "  create-model  - Generate a model from existing table"
    echo "  validate-fk   - Validate all foreign key constraints"
    echo "  help          - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 check"
    echo "  $0 create-model pitch_decks"
    echo "  $0 auto-sync"
}

# Main command dispatcher
case "$1" in
    check)
        check_sync
        ;;
    auto-sync)
        auto_sync
        ;;
    orphans)
        list_orphan_tables
        ;;
    create-model)
        create_model_from_table "$2"
        ;;
    validate-fk)
        validate_foreign_keys
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        show_help
        exit 1
        ;;
esac