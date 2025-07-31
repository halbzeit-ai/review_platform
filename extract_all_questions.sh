#!/bin/bash

# Extract all 34 questions from production database

echo "🔍 Finding database..."
DB_NAME=$(sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE datname LIKE 'review%' OR datname LIKE 'platform%' LIMIT 1;" | tr -d ' ')
echo "✅ Using database: $DB_NAME"

# First, let's check pitch_decks columns
echo -e "\n📋 Pitch decks columns:"
sudo -u postgres psql "$DB_NAME" -c "\d pitch_decks" | grep -E "^\s+\w+" | head -10

echo -e "\n📋 Finding decks with template 9:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    id,
    analysis_template_id,
    created_at
FROM pitch_decks
WHERE analysis_template_id = 9
LIMIT 5;"

echo -e "\n📊 Checking question_analysis_results data:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    qar.pitch_deck_id,
    qar.question_id,
    cq.question_id as question_code,
    tc.name as chapter_name,
    cq.order_index as question_number,
    LEFT(cq.question_text, 60) as question
FROM question_analysis_results qar
JOIN chapter_questions cq ON cq.id = qar.question_id
JOIN template_chapters tc ON tc.id = cq.chapter_id
JOIN pitch_decks pd ON pd.id = qar.pitch_deck_id
WHERE pd.analysis_template_id = 9
ORDER BY qar.pitch_deck_id, tc.order_index, cq.order_index
LIMIT 50;"

echo -e "\n📊 Count questions per chapter:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    tc.name as chapter_name,
    COUNT(DISTINCT cq.id) as total_questions,
    array_agg(DISTINCT cq.order_index ORDER BY cq.order_index) as question_indices
FROM question_analysis_results qar
JOIN chapter_questions cq ON cq.id = qar.question_id  
JOIN template_chapters tc ON tc.id = cq.chapter_id
JOIN pitch_decks pd ON pd.id = qar.pitch_deck_id
WHERE pd.analysis_template_id = 9
GROUP BY tc.name, tc.order_index
ORDER BY tc.order_index;"

echo -e "\n🔍 Looking for reviews with JSON data:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    r.id,
    r.pitch_deck_id,
    r.status,
    LENGTH(r.review_data) as data_length
FROM reviews r
JOIN pitch_decks pd ON pd.id = r.pitch_deck_id
WHERE pd.analysis_template_id = 9
AND r.review_data IS NOT NULL
LIMIT 5;"

# Extract a review JSON to see all questions
REVIEW_ID=$(sudo -u postgres psql "$DB_NAME" -t -c "
SELECT r.id
FROM reviews r
JOIN pitch_decks pd ON pd.id = r.pitch_deck_id
WHERE pd.analysis_template_id = 9
AND r.review_data IS NOT NULL
LIMIT 1;" | tr -d ' ')

if [ ! -z "$REVIEW_ID" ]; then
    echo -e "\n💾 Extracting review JSON (ID: $REVIEW_ID)..."
    sudo -u postgres psql "$DB_NAME" -t -c "
    SELECT review_data
    FROM reviews
    WHERE id = $REVIEW_ID;" > /tmp/review_$REVIEW_ID.json
    
    echo "Review saved to /tmp/review_$REVIEW_ID.json"
    
    # Parse JSON to find all questions
    python3 -c "
import json
import re

with open('/tmp/review_$REVIEW_ID.json', 'r') as f:
    content = f.read()
    
# Find all questions in the JSON
questions = re.findall(r'\"question\":\s*\"([^\"]+)\"', content)
print(f'\\nFound {len(questions)} questions in review JSON')

# Try to parse as JSON and show structure
try:
    data = json.loads(content)
    if 'sections' in data:
        print('\\nQuestions per section:')
        for section in data['sections']:
            name = section.get('section_name', 'Unknown')
            q_count = len(section.get('questions', []))
            print(f'{name}: {q_count}')
            
            # Show questions 5 and 6 if they exist
            questions = section.get('questions', [])
            for i, q in enumerate(questions):
                if i >= 4:  # Questions 5 and 6 (0-indexed)
                    print(f'  Q{i+1}: {q.get(\"question\", \"?\")[:70]}...')
except:
    print('Could not parse as JSON')
"
fi

echo -e "\n📄 Creating export file with all questions..."
sudo -u postgres psql "$DB_NAME" -A -F'|' -c "
SELECT DISTINCT
    tc.order_index as chapter_order,
    tc.name as chapter_name,
    cq.order_index as q_num,
    cq.question_id,
    cq.question_text
FROM chapter_questions cq
JOIN template_chapters tc ON tc.id = cq.chapter_id
WHERE tc.analysis_template_id = 9
ORDER BY tc.order_index, cq.order_index;" > all_questions_export.txt

echo -e "\n✅ Questions exported to all_questions_export.txt"
wc -l all_questions_export.txt