#!/bin/bash

# Diagnostic script to find ALL Seven-Chapter Review questions
# Including disabled, orphaned, or hidden questions

echo "🔍 Finding database..."
DB_NAME=$(sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE datname LIKE 'review%' OR datname LIKE 'platform%' LIMIT 1;" | tr -d ' ')
echo "✅ Using database: $DB_NAME"

# Get template info
echo -e "\n📋 Template information:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT id, name, healthcare_sector_id, is_active, is_default
FROM analysis_templates 
WHERE name ILIKE '%Seven-Chapter%';"

TEMPLATE_ID=9

echo -e "\n📚 Checking ALL questions (including disabled):"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    tc.name as chapter,
    tc.order_index as ch_order,
    COUNT(*) as total_questions,
    SUM(CASE WHEN cq.enabled = true THEN 1 ELSE 0 END) as enabled_questions,
    SUM(CASE WHEN cq.enabled = false THEN 1 ELSE 0 END) as disabled_questions
FROM template_chapters tc
LEFT JOIN chapter_questions cq ON cq.chapter_id = tc.id
WHERE tc.template_id = $TEMPLATE_ID OR tc.analysis_template_id = $TEMPLATE_ID
GROUP BY tc.name, tc.order_index
ORDER BY tc.order_index;"

echo -e "\n❓ Looking for questions with order_index > 4:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    tc.name as chapter,
    cq.order_index,
    cq.enabled,
    LEFT(cq.question_text, 80) as question_preview
FROM chapter_questions cq
JOIN template_chapters tc ON cq.chapter_id = tc.id
WHERE (tc.template_id = $TEMPLATE_ID OR tc.analysis_template_id = $TEMPLATE_ID)
AND cq.order_index > 4
ORDER BY tc.order_index, cq.order_index;"

echo -e "\n🔍 Checking for duplicate question_ids:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    tc.name as chapter,
    cq.question_id,
    COUNT(*) as count
FROM chapter_questions cq
JOIN template_chapters tc ON cq.chapter_id = tc.id
WHERE tc.template_id = $TEMPLATE_ID OR tc.analysis_template_id = $TEMPLATE_ID
GROUP BY tc.name, cq.question_id
HAVING COUNT(*) > 1;"

echo -e "\n📊 All questions with their status:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    tc.name as chapter,
    cq.order_index,
    cq.question_id,
    cq.enabled,
    LEFT(cq.question_text, 60) as question
FROM chapter_questions cq
JOIN template_chapters tc ON cq.chapter_id = tc.id
WHERE tc.template_id = $TEMPLATE_ID OR tc.analysis_template_id = $TEMPLATE_ID
ORDER BY tc.order_index, cq.order_index;"

echo -e "\n💡 Checking if there's a question limit in the query:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    tc.id,
    tc.name,
    COUNT(cq.id) as actual_count,
    array_agg(cq.order_index ORDER BY cq.order_index) as question_indices
FROM template_chapters tc
LEFT JOIN chapter_questions cq ON cq.chapter_id = tc.id
WHERE tc.template_id = $TEMPLATE_ID OR tc.analysis_template_id = $TEMPLATE_ID
GROUP BY tc.id, tc.name
ORDER BY tc.order_index;"