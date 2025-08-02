#!/bin/bash
# Setup Unified Dojo Structure
# Creates new unified dojo structure and cleans up old data

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Detect environment based on mount path
if [[ -d "/mnt/CPU-GPU" ]]; then
    ENVIRONMENT="production"
    SHARED_PATH="/mnt/CPU-GPU"
    DB_NAME="review-platform"
elif [[ -d "/mnt/dev-shared" ]]; then
    ENVIRONMENT="development"
    SHARED_PATH="/mnt/dev-shared"
    DB_NAME="review_dev"
else
    echo -e "${RED}❌ Cannot detect environment - no shared filesystem found${NC}"
    exit 1
fi

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

# Function to clean database
clean_database() {
    local db_name=$1
    
    echo -e "${YELLOW}🗄️ Cleaning database...${NC}"
    
    # Clean up dojo entries from database
    sudo -u postgres psql -d "${db_name}" << EOF
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

SELECT 'Database cleaned - dojo entries removed' as status;
EOF
    
    echo -e "${GREEN}✅ Database cleaned${NC}"
}

# Function to add file_hash column
add_file_hash_column() {
    local db_name=$1
    
    echo -e "${YELLOW}🔧 Adding file_hash column to pitch_decks table...${NC}"
    
    sudo -u postgres psql -d "${db_name}" << EOF
-- Add file_hash column if it doesn't exist
DO \$\$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'pitch_decks' AND column_name = 'file_hash'
    ) THEN
        ALTER TABLE pitch_decks ADD COLUMN file_hash VARCHAR(64);
        CREATE INDEX idx_pitch_decks_file_hash ON pitch_decks(file_hash);
        SELECT 'Added file_hash column and index' as status;
    ELSE
        SELECT 'file_hash column already exists' as status;
    END IF;
END
\$\$;
EOF
    
    echo -e "${GREEN}✅ File hash column ready${NC}"
}

# Main execution
echo -e "${BLUE}Starting setup process...${NC}"
echo ""

# Step 1: Clean up old structures
cleanup_old_dojo "${SHARED_PATH}"

# Step 2: Create new unified structure
create_dojo_structure "${SHARED_PATH}"

# Step 3: Clean database
clean_database "${DB_NAME}"

# Step 4: Add file_hash column
add_file_hash_column "${DB_NAME}"

echo ""
echo -e "${GREEN}🎉 Unified dojo structure setup complete!${NC}"
echo ""
echo -e "${BLUE}📋 Next steps:${NC}"
echo -e "  1. Upload your ZIP file through Dojo Management"
echo -e "  2. Files will be stored in: ${SHARED_PATH}/projects/dojo/uploads/"
echo -e "  3. Duplicate detection will prevent conflicts"
echo -e "  4. Analysis results will go to: ${SHARED_PATH}/projects/dojo/analysis/"
echo ""
echo -e "${YELLOW}⚠️  Remember to restart services if needed:${NC}"
if [[ "$ENVIRONMENT" == "production" ]]; then
    echo -e "  sudo systemctl restart review-platform.service"
    echo -e "  sudo systemctl restart gpu-http-server.service"
else
    echo -e "  ./dev-services-improved.sh restart"
fi