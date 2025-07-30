#!/bin/bash
# Export ALL prompts from production database
# Run this on the PRODUCTION server

echo "📥 Exporting ALL prompts from production database..."

# First check what tables contain prompts
echo "🔍 Checking for prompt tables in production:"
psql postgresql://review_user:review_password@localhost:5432/review-platform -c \
    "SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%prompt%' ORDER BY table_name;"

echo ""
echo "📋 Current pipeline_prompts content:"
psql postgresql://review_user:review_password@localhost:5432/review-platform -c \
    "SELECT stage_name, prompt_name, is_active, LENGTH(prompt_text) as length FROM pipeline_prompts ORDER BY stage_name;"

echo ""
echo "🔍 Checking if 'prompts' table exists:"
psql postgresql://review_user:review_password@localhost:5432/review-platform -c \
    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'prompts');"

# Check if prompts table exists and export it too
PROMPTS_TABLE_EXISTS=$(psql postgresql://review_user:review_password@localhost:5432/review-platform -t -c \
    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'prompts');")

echo ""
echo "📤 Exporting pipeline_prompts table..."
pg_dump postgresql://review_user:review_password@localhost:5432/review-platform \
    --table=pipeline_prompts \
    --data-only \
    --inserts \
    --no-owner \
    --no-privileges \
    > /mnt/CPU-GPU/temp/production_pipeline_prompts.sql

if echo "$PROMPTS_TABLE_EXISTS" | grep -q "t"; then
    echo "📤 Exporting prompts table..."
    pg_dump postgresql://review_user:review_password@localhost:5432/review-platform \
        --table=prompts \
        --data-only \
        --inserts \
        --no-owner \
        --no-privileges \
        > /mnt/CPU-GPU/temp/production_prompts_table.sql
        
    echo "📋 Prompts table content:"
    psql postgresql://review_user:review_password@localhost:5432/review-platform -c \
        "SELECT prompt_name, is_active, LENGTH(prompt_text) as length FROM prompts ORDER BY prompt_name;"
else
    echo "ℹ️  No 'prompts' table found - only pipeline_prompts exported"
fi

# Also check for any prompts with extraction in the name
echo ""
echo "🔍 Searching for extraction-related prompts:"
psql postgresql://review_user:review_password@localhost:5432/review-platform -c \
    "SELECT stage_name, prompt_name FROM pipeline_prompts WHERE stage_name ILIKE '%extraction%' OR prompt_name ILIKE '%extraction%';"

echo ""
echo "✅ Export completed!"
echo "📁 Files created:"
echo "   - /mnt/CPU-GPU/temp/production_pipeline_prompts.sql"
if echo "$PROMPTS_TABLE_EXISTS" | grep -q "t"; then
    echo "   - /mnt/CPU-GPU/temp/production_prompts_table.sql"
fi
echo ""
echo "📌 Next steps:"
echo "   1. Files are now available on shared filesystem"
echo "   2. Run import script on dev server to import into development database"