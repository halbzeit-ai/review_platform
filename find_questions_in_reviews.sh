#!/bin/bash

# Find where the actual questions are stored in reviews

echo "🔍 Finding database..."
DB_NAME=$(sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE datname LIKE 'review%' OR datname LIKE 'platform%' LIMIT 1;" | tr -d ' ')
echo "✅ Using database: $DB_NAME"

echo -e "\n📊 Checking review-related tables:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND (table_name LIKE '%review%' OR table_name LIKE '%analysis%' OR table_name LIKE '%section%')
ORDER BY table_name;"

echo -e "\n🔍 Checking questions table structure:"
sudo -u postgres psql "$DB_NAME" -c "\d questions"

echo -e "\n🔍 Checking question_analysis_results structure:"
sudo -u postgres psql "$DB_NAME" -c "\d question_analysis_results"

echo -e "\n📋 Looking for reviews using template 9:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    r.id as review_id,
    r.deck_id,
    r.status,
    pd.analysis_template_id,
    LEFT(r.review_data::text, 100) as review_preview
FROM reviews r
JOIN pitch_decks pd ON r.deck_id = pd.id
WHERE pd.analysis_template_id = 9
LIMIT 3;"

echo -e "\n🔍 Checking healthcare_templates for Seven-Chapter questions:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    id,
    template_name,
    LENGTH(analysis_prompt) as prompt_length,
    LEFT(analysis_prompt, 200) as prompt_preview
FROM healthcare_templates
WHERE template_name ILIKE '%Seven%Chapter%';"

echo -e "\n💡 Let's extract a complete review to see the structure:"
sudo -u postgres psql "$DB_NAME" -t -c "
SELECT review_data::text
FROM reviews r
JOIN pitch_decks pd ON r.deck_id = pd.id
WHERE pd.analysis_template_id = 9
AND r.review_data IS NOT NULL
LIMIT 1;" > /tmp/sample_review.json

if [ -s /tmp/sample_review.json ]; then
    echo "📄 Sample review saved to /tmp/sample_review.json"
    echo "Checking for question patterns..."
    
    # Count questions per section
    echo -e "\n📊 Questions found in actual review:"
    for section in "Problem Analysis" "Solution Approach" "Product Market Fit" "Monetization" "Financials" "Use of Funds" "Organization"; do
        count=$(grep -o "\"section_name\":\"$section\"" /tmp/sample_review.json | wc -l)
        echo "$section: $count questions"
    done
fi

echo -e "\n🔍 Looking for the missing questions in healthcare_templates analysis_prompt:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    template_name,
    analysis_prompt
FROM healthcare_templates
WHERE id = 1 OR template_name ILIKE '%Seven%Chapter%';" > /tmp/template_prompts.txt

echo -e "\n📝 Checking if prompts contain all 34 questions..."
if [ -f /tmp/template_prompts.txt ]; then
    cat /tmp/template_prompts.txt
fi