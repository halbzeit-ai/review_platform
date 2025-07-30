#!/bin/bash
# Export prompts from production database
# Run this on the PRODUCTION server

echo "📥 Exporting prompts from production database..."

# Export pipeline_prompts table to SQL file
pg_dump postgresql://review_user:review_password@localhost:5432/review-platform \
    --table=pipeline_prompts \
    --data-only \
    --inserts \
    --no-owner \
    --no-privileges \
    > /mnt/CPU-GPU/temp/production_prompts.sql

if [ $? -eq 0 ]; then
    echo "✅ Prompts exported to /mnt/CPU-GPU/temp/production_prompts.sql"
    echo ""
    echo "📋 Exported prompts:"
    psql postgresql://review_user:review_password@localhost:5432/review-platform -c \
        "SELECT stage_name, is_active, LENGTH(prompt_text) as length FROM pipeline_prompts ORDER BY stage_name" 
    echo ""
    echo "📌 Next steps:"
    echo "   1. File is now available on shared filesystem at /mnt/CPU-GPU/temp/production_prompts.sql"
    echo "   2. Run import script on dev server to import into development database"
else
    echo "❌ Export failed"
    exit 1
fi