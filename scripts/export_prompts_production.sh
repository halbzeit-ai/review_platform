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
    > /tmp/production_prompts.sql

if [ $? -eq 0 ]; then
    echo "✅ Prompts exported to /tmp/production_prompts.sql"
    echo ""
    echo "📋 Exported prompts:"
    psql postgresql://review_user:review_password@localhost:5432/review-platform -c \
        "SELECT stage_name, is_active, LENGTH(prompt_text) as length FROM pipeline_prompts ORDER BY stage_name" 
    echo ""
    echo "📌 Next steps:"
    echo "   1. Copy this file to dev server: scp /tmp/production_prompts.sql root@65.108.32.143:/tmp/"
    echo "   2. Run import script on dev server"
else
    echo "❌ Export failed"
    exit 1
fi