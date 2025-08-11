#!/bin/bash
# Simple Database/Models Sync Checker using direct psql

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}DATABASE/MODELS SYNCHRONIZATION CHECK${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Get database tables
sudo -u postgres psql review-platform -t -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name;" | sed 's/^ *//;/^$/d' > /tmp/db_tables.txt

# Get model tables from models.py
grep "__tablename__" /opt/review-platform/backend/app/db/models.py | grep -v "^#" | sed 's/.*= *//' | sed 's/"//g' | sort > /tmp/model_tables.txt

# Count tables
DB_COUNT=$(wc -l < /tmp/db_tables.txt)
MODEL_COUNT=$(wc -l < /tmp/model_tables.txt)

echo -e "Database tables: ${BLUE}$DB_COUNT${NC}"
echo -e "Model tables:    ${BLUE}$MODEL_COUNT${NC}"
echo ""

# Find differences
echo "Checking for differences..."
echo ""

# Tables only in database
ONLY_IN_DB=$(comm -23 /tmp/db_tables.txt /tmp/model_tables.txt)
if [ ! -z "$ONLY_IN_DB" ]; then
    echo -e "${YELLOW}⚠️  Tables ONLY in database (missing from models.py):${NC}"
    echo "$ONLY_IN_DB" | sed 's/^/   - /'
    echo ""
fi

# Tables only in models
ONLY_IN_MODELS=$(comm -13 /tmp/db_tables.txt /tmp/model_tables.txt)
if [ ! -z "$ONLY_IN_MODELS" ]; then
    echo -e "${YELLOW}⚠️  Tables ONLY in models.py (missing from database):${NC}"
    echo "$ONLY_IN_MODELS" | sed 's/^/   - /'
    echo ""
fi

# Check if in sync
if [ -z "$ONLY_IN_DB" ] && [ -z "$ONLY_IN_MODELS" ]; then
    echo -e "${GREEN}✅ Database and models.py are IN SYNC!${NC}"
    echo ""
    
    # Additional validation: check for orphaned foreign keys
    echo "Checking foreign key integrity..."
    ORPHANED_FKS=$(sudo -u postgres psql review-platform -t -c "
        SELECT COUNT(*)
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu 
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage ccu 
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND ccu.table_name NOT IN (
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        )
    " | tr -d ' ')
    
    if [ "$ORPHANED_FKS" -eq "0" ]; then
        echo -e "${GREEN}✅ All foreign keys are valid${NC}"
    else
        echo -e "${YELLOW}⚠️  Found $ORPHANED_FKS orphaned foreign key(s)${NC}"
    fi
    exit 0
else
    echo -e "${RED}❌ Database and models.py are OUT OF SYNC${NC}"
    echo ""
    echo -e "${BLUE}Recommended Actions:${NC}"
    if [ ! -z "$ONLY_IN_DB" ]; then
        echo "  • Add models for database tables or drop unused tables"
    fi
    if [ ! -z "$ONLY_IN_MODELS" ]; then
        echo "  • Run migrations to create missing database tables"
    fi
    exit 1
fi