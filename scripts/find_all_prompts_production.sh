#!/bin/bash
# Comprehensive script to find ALL prompts in production database
# Run this on the PRODUCTION server

echo "🔍 COMPREHENSIVE PROMPT SEARCH IN PRODUCTION DATABASE"
echo "=" * 60

echo ""
echo "1️⃣ SEARCHING ALL TABLES FOR PROMPT-RELATED CONTENT..."
psql postgresql://review_user:review_password@localhost:5432/review-platform -c "
SELECT table_name, column_name, data_type 
FROM information_schema.columns 
WHERE column_name ILIKE '%prompt%' 
   OR table_name ILIKE '%prompt%'
ORDER BY table_name, column_name;
"

echo ""
echo "2️⃣ PIPELINE_PROMPTS TABLE - ALL RECORDS..."
psql postgresql://review_user:review_password@localhost:5432/review-platform -c "
SELECT id, stage_name, prompt_type, prompt_name, is_active, is_enabled,
       LEFT(prompt_text, 100) || '...' as prompt_preview,
       LENGTH(prompt_text) as prompt_length,
       created_at, updated_at
FROM pipeline_prompts 
ORDER BY id;
"

echo ""
echo "3️⃣ SEARCH FOR FUNDING-RELATED PROMPTS..."
psql postgresql://review_user:review_password@localhost:5432/review-platform -c "
SELECT id, stage_name, prompt_name, is_active,
       prompt_text
FROM pipeline_prompts 
WHERE stage_name ILIKE '%funding%' 
   OR prompt_name ILIKE '%funding%'
   OR prompt_text ILIKE '%funding%'
   OR stage_name ILIKE '%amount%'
   OR prompt_text ILIKE '%amount%'
ORDER BY id;
"

echo ""
echo "4️⃣ SEARCH FOR DATE-RELATED PROMPTS..."
psql postgresql://review_user:review_password@localhost:5432/review-platform -c "
SELECT id, stage_name, prompt_name, is_active,
       prompt_text
FROM pipeline_prompts 
WHERE stage_name ILIKE '%date%' 
   OR prompt_name ILIKE '%date%'
   OR prompt_text ILIKE '%date%'
   OR stage_name ILIKE '%deck%'
   OR prompt_text ILIKE '%deck%'
ORDER BY id;
"

echo ""
echo "5️⃣ SEARCH FOR EXTRACTION-RELATED PROMPTS..."
psql postgresql://review_user:review_password@localhost:5032/review-platform -c "
SELECT id, stage_name, prompt_name, is_active,
       LEFT(prompt_text, 200) || '...' as prompt_preview
FROM pipeline_prompts 
WHERE stage_name ILIKE '%extraction%' 
   OR prompt_name ILIKE '%extraction%'
   OR prompt_text ILIKE '%extraction%'
ORDER BY id;
"

echo ""
echo "6️⃣ CHECK FOR ANY INACTIVE OR DISABLED PROMPTS..."
psql postgresql://review_user:review_password@localhost:5432/review-platform -c "
SELECT id, stage_name, prompt_name, is_active, is_enabled,
       LEFT(prompt_text, 100) || '...' as prompt_preview
FROM pipeline_prompts 
WHERE is_active = false OR is_enabled = false
ORDER BY id;
"

echo ""
echo "7️⃣ FULL COUNT AND STATISTICS..."
psql postgresql://review_user:review_password@localhost:5432/review-platform -c "
SELECT 
    COUNT(*) as total_prompts,
    COUNT(CASE WHEN is_active = true THEN 1 END) as active_prompts,
    COUNT(CASE WHEN is_enabled = true THEN 1 END) as enabled_prompts,
    COUNT(CASE WHEN stage_name ILIKE '%extraction%' THEN 1 END) as extraction_prompts,
    COUNT(CASE WHEN prompt_text ILIKE '%funding%' THEN 1 END) as funding_related_prompts,
    COUNT(CASE WHEN prompt_text ILIKE '%date%' THEN 1 END) as date_related_prompts
FROM pipeline_prompts;
"

echo ""
echo "8️⃣ CHECK IF THERE ARE OTHER PROMPT TABLES..."
psql postgresql://review_user:review_password@localhost:5432/review-platform -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_name ILIKE '%prompt%' 
   OR table_name ILIKE '%template%'
   OR table_name ILIKE '%text%'
ORDER BY table_name;
"

echo ""
echo "✅ COMPREHENSIVE SEARCH COMPLETED!"
echo ""
echo "📌 This should show us:"
echo "   - All prompt-related tables and columns"
echo "   - All records in pipeline_prompts (even inactive ones)"
echo "   - Any prompts containing 'funding', 'amount', 'date', 'deck', 'extraction'"
echo "   - Statistics about prompt counts"
echo ""
echo "🔍 If the funding/date extraction prompts exist, they WILL show up in this output!"