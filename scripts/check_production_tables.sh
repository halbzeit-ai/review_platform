#!/bin/bash
# Check what tables exist in production database
# Run this on the PRODUCTION server

echo "🔍 Checking tables in production database..."

echo "📋 All tables:"
psql postgresql://review_user:review_password@localhost:5432/review-platform -c "\dt"

echo ""
echo "🔍 Looking for prompt-related tables:"
psql postgresql://review_user:review_password@localhost:5432/review-platform -c \
    "SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%prompt%' OR table_name LIKE '%template%'"

echo ""
echo "🔍 Checking for any tables with 'content' or 'text' columns (might contain prompts):"
psql postgresql://review_user:review_password@localhost:5432/review-platform -c \
    "SELECT table_name, column_name FROM information_schema.columns 
     WHERE column_name IN ('content', 'prompt', 'template', 'text') 
     AND table_schema = 'public'"