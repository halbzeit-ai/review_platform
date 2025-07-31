#!/bin/bash

# Check the actual schema to understand review storage

echo "🔍 Finding database..."
DB_NAME=$(sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE datname LIKE 'review%' OR datname LIKE 'platform%' LIMIT 1;" | tr -d ' ')
echo "✅ Using database: $DB_NAME"

echo -e "\n📋 Checking reviews table structure:"
sudo -u postgres psql "$DB_NAME" -c "\d reviews"

echo -e "\n📋 Checking pitch_decks table structure:"
sudo -u postgres psql "$DB_NAME" -c "\d pitch_decks" 

echo -e "\n📋 Finding startups with analysis_template_id = 9:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    id,
    company_name,
    analysis_template_id,
    created_at
FROM pitch_decks
WHERE analysis_template_id = 9
LIMIT 5;"

echo -e "\n🔍 Checking question_analysis_results table:"
sudo -u postgres psql "$DB_NAME" -c "\d question_analysis_results"

echo -e "\n📊 Getting sample data from question_analysis_results:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    qar.deck_id,
    pd.company_name,
    qar.chapter_name,
    qar.question_number,
    LEFT(qar.question_text, 60) as question,
    qar.score
FROM question_analysis_results qar
JOIN pitch_decks pd ON pd.id = qar.deck_id
WHERE pd.analysis_template_id = 9
ORDER BY qar.deck_id, qar.chapter_name, qar.question_number
LIMIT 40;"

echo -e "\n📊 Count questions per chapter from actual results:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    chapter_name,
    COUNT(DISTINCT question_number) as question_count,
    array_agg(DISTINCT question_number ORDER BY question_number) as question_numbers
FROM question_analysis_results qar
JOIN pitch_decks pd ON pd.id = qar.deck_id
WHERE pd.analysis_template_id = 9
GROUP BY chapter_name
ORDER BY 
    CASE chapter_name
        WHEN 'Problem Analysis' THEN 1
        WHEN 'Solution Approach' THEN 2
        WHEN 'Product Market Fit' THEN 3
        WHEN 'Monetization' THEN 4
        WHEN 'Financials' THEN 5
        WHEN 'Use of Funds' THEN 6
        WHEN 'Organization' THEN 7
    END;"