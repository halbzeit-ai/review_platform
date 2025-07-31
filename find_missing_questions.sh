#!/bin/bash

# Find the missing questions (order_index 5 and 6) for Seven-Chapter Review
# Based on actual deck analysis: problems:4, solution:5, product_market_fit:5, monetization:6, financials:5, use_of_funds:4, organization:5

echo "🔍 Finding database..."
DB_NAME=$(sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE datname LIKE 'review%' OR datname LIKE 'platform%' LIMIT 1;" | tr -d ' ')
echo "✅ Using database: $DB_NAME"

echo -e "\n📊 Expected vs Actual question counts:"
echo "Chapter              | Expected | Found | Missing"
echo "---------------------|----------|-------|--------"
echo "Problem Analysis     |    4     |   4   |    0"
echo "Solution Approach    |    5     |   4   |    1"  
echo "Product Market Fit   |    5     |   4   |    1"
echo "Monetization         |    6     |   4   |    2"
echo "Financials           |    5     |   4   |    1"
echo "Use of Funds         |    4     |   4   |    0"
echo "Organization         |    5     |   4   |    1"
echo "---------------------|----------|-------|--------"
echo "TOTAL                |   34     |  28   |    6"

echo -e "\n🔍 Checking if questions were soft-deleted (enabled=false):"
sudo -u postgres psql "$DB_NAME" -c "
SELECT COUNT(*) as total_questions_in_table
FROM chapter_questions cq
JOIN template_chapters tc ON cq.chapter_id = tc.id
WHERE tc.template_id = 9 OR tc.analysis_template_id = 9;"

echo -e "\n🔍 Looking in review_sections table (from actual deck analysis):"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    section_name,
    COUNT(DISTINCT question_number) as unique_questions,
    array_agg(DISTINCT question_number ORDER BY question_number) as question_numbers
FROM review_sections
WHERE deck_id IN (
    SELECT id FROM pitch_decks 
    WHERE analysis_template_id = 9
    LIMIT 5
)
GROUP BY section_name
ORDER BY 
    CASE section_name
        WHEN 'Problem Analysis' THEN 1
        WHEN 'Solution Approach' THEN 2
        WHEN 'Product Market Fit' THEN 3
        WHEN 'Monetization' THEN 4
        WHEN 'Financials' THEN 5
        WHEN 'Use of Funds' THEN 6
        WHEN 'Organization' THEN 7
    END;"

echo -e "\n🔍 Sample of actual questions from review_sections (showing question 5 & 6):"
sudo -u postgres psql "$DB_NAME" -c "
SELECT DISTINCT
    section_name,
    question_number,
    LEFT(question, 80) as question_text
FROM review_sections
WHERE question_number > 4
AND deck_id IN (
    SELECT id FROM pitch_decks 
    WHERE analysis_template_id = 9
    LIMIT 1
)
ORDER BY section_name, question_number;"

echo -e "\n💡 Checking template configuration in other tables:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND (table_name LIKE '%template%' OR table_name LIKE '%question%')
ORDER BY table_name;"

echo -e "\n🔍 Looking for the original healthcare_templates table:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT COUNT(*) FROM healthcare_templates
WHERE template_name ILIKE '%Seven-Chapter%';"