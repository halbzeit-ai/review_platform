#!/bin/bash
# Setup Unified Dojo Structure for Development Environment
# Creates new unified dojo structure and cleans up old data on development server

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Development environment configuration
ENVIRONMENT="development"
SHARED_PATH="/mnt/dev-shared"
DB_NAME="review_dev"
DB_USER="dev_user"
DB_PASSWORD="!dev_Halbzeit1024"
DB_HOST="65.108.32.143"

echo -e "${BLUE}🚀 Setting up unified dojo structure for ${ENVIRONMENT}${NC}"
echo -e "Shared filesystem: ${SHARED_PATH}"
echo -e "Database: ${DB_NAME}"
echo ""

# Function to create directory structure
create_dojo_structure() {
    local base_path=$1
    
    echo -e "${YELLOW}📁 Creating unified dojo directory structure...${NC}"
    
    # Create main dojo project directory
    sudo mkdir -p "${base_path}/projects/dojo"
    
    # Create subdirectories following project pattern
    sudo mkdir -p "${base_path}/projects/dojo/uploads"
    sudo mkdir -p "${base_path}/projects/dojo/analysis"
    sudo mkdir -p "${base_path}/projects/dojo/exports"
    
    # Set proper permissions
    sudo chmod -R 777 "${base_path}/projects/dojo"
    
    echo -e "${GREEN}✅ Created directory structure:${NC}"
    echo -e "  ${base_path}/projects/dojo/uploads/  (PDF files)"
    echo -e "  ${base_path}/projects/dojo/analysis/ (AI results)"
    echo -e "  ${base_path}/projects/dojo/exports/  (Exported data)"
}

# Function to clean up old dojo directories
cleanup_old_dojo() {
    local base_path=$1
    
    echo -e "${YELLOW}🧹 Cleaning up old dojo directories...${NC}"
    
    # Remove old dojo directory if it exists
    if [[ -d "${base_path}/dojo" ]]; then
        sudo rm -rf "${base_path}/dojo"
        echo -e "${GREEN}✅ Removed old ${base_path}/dojo${NC}"
    fi
    
    # Clean up any files in old projects/dojo if it exists
    if [[ -d "${base_path}/projects/dojo" ]]; then
        sudo rm -rf "${base_path}/projects/dojo"
        echo -e "${GREEN}✅ Cleaned up old ${base_path}/projects/dojo${NC}"
    fi
}

# Function to clean database (development version)
clean_database() {
    echo -e "${YELLOW}🗄️ Cleaning development database...${NC}"
    
    # Clean up dojo entries from development database
    PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" << EOF
-- Clean up all dojo-related data
DELETE FROM visual_analysis_cache 
WHERE pitch_deck_id IN (SELECT id FROM pitch_decks WHERE data_source = 'dojo');

DELETE FROM reviews 
WHERE pitch_deck_id IN (SELECT id FROM pitch_decks WHERE data_source = 'dojo');

DELETE FROM chapter_analysis_results
WHERE pitch_deck_id IN (SELECT id FROM pitch_decks WHERE data_source = 'dojo');

DELETE FROM question_analysis_results
WHERE pitch_deck_id IN (SELECT id FROM pitch_decks WHERE data_source = 'dojo');

DELETE FROM pitch_decks WHERE data_source = 'dojo';

SELECT 'Development database cleaned - dojo entries removed' as status;
EOF
    
    echo -e "${GREEN}✅ Development database cleaned${NC}"
}

# Function to add file_hash column (development version)
add_file_hash_column() {
    echo -e "${YELLOW}🔧 Adding file_hash column to development database...${NC}"
    
    PGPASSWORD="${DB_PASSWORD}" psql -h "${DB_HOST}" -U "${DB_USER}" -d "${DB_NAME}" << EOF
-- Add file_hash column if it doesn't exist
DO \$\$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'pitch_decks' AND column_name = 'file_hash'
    ) THEN
        ALTER TABLE pitch_decks ADD COLUMN file_hash VARCHAR(64);
        CREATE INDEX idx_pitch_decks_file_hash ON pitch_decks(file_hash);
        SELECT 'Added file_hash column and index to development database' as status;
    ELSE
        SELECT 'file_hash column already exists in development database' as status;
    END IF;
END
\$\$;
EOF
    
    echo -e "${GREEN}✅ Development file hash column ready${NC}"
}

# Check if we're on the development server
if [[ ! -d "${SHARED_PATH}" ]]; then
    echo -e "${RED}❌ Development shared filesystem not found at ${SHARED_PATH}${NC}"
    echo -e "${YELLOW}This script should be run on the development server${NC}"
    exit 1
fi

# Main execution
echo -e "${BLUE}Starting development setup process...${NC}"
echo ""

# Step 1: Clean up old structures
cleanup_old_dojo "${SHARED_PATH}"

# Step 2: Create new unified structure
create_dojo_structure "${SHARED_PATH}"

# Step 3: Clean database
clean_database

# Step 4: Add file_hash column
add_file_hash_column

echo ""
echo -e "${GREEN}🎉 Development unified dojo structure setup complete!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps for development:${NC}"
echo -e "  1. Upload your ZIP file through Dojo Management"
echo -e "  2. Files will be stored in: ${SHARED_PATH}/projects/dojo/uploads/"
echo -e "  3. Duplicate detection will prevent conflicts"
echo -e "  4. Analysis results will go to: ${SHARED_PATH}/projects/dojo/analysis/"
echo ""
echo -e "${YELLOW}⚠️  Remember to restart development services:${NC}"
echo -e "  ./dev-services-improved.sh restart"
echo ""
echo -e "${BLUE}💡 To use the enhanced upload endpoint:${NC}"
echo -e "  POST /api/dojo/upload-enhanced (instead of /api/dojo/upload)"