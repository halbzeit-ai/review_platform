#!/bin/bash

# Find startup review results to see all 34 questions

echo "🔍 Finding database..."
DB_NAME=$(sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE datname LIKE 'review%' OR datname LIKE 'platform%' LIMIT 1;" | tr -d ' ')
echo "✅ Using database: $DB_NAME"

echo -e "\n📋 Finding a startup with Seven-Chapter Review (template 9):"
sudo -u postgres psql "$DB_NAME" -c "
SELECT 
    pd.id as deck_id,
    pd.company_name,
    pd.analysis_template_id,
    r.id as review_id,
    r.status as review_status,
    LENGTH(r.review_data::text) as review_data_size
FROM pitch_decks pd
LEFT JOIN reviews r ON r.deck_id = pd.id
WHERE pd.analysis_template_id = 9
AND r.review_data IS NOT NULL
ORDER BY pd.id DESC
LIMIT 5;"

echo -e "\n🔍 Extracting review data for the first startup:"
DECK_ID=$(sudo -u postgres psql "$DB_NAME" -t -c "
SELECT pd.id
FROM pitch_decks pd
JOIN reviews r ON r.deck_id = pd.id
WHERE pd.analysis_template_id = 9
AND r.review_data IS NOT NULL
ORDER BY pd.id DESC
LIMIT 1;" | tr -d ' ')

if [ ! -z "$DECK_ID" ]; then
    echo "Found deck ID: $DECK_ID"
    
    # Extract the review JSON
    sudo -u postgres psql "$DB_NAME" -t -c "
    SELECT review_data::text
    FROM reviews
    WHERE deck_id = $DECK_ID;" > /tmp/seven_chapter_review.json
    
    echo -e "\n📊 Analyzing review structure:"
    
    # Parse JSON to count questions per section
    echo "Questions per section:"
    python3 -c "
import json
import sys

try:
    with open('/tmp/seven_chapter_review.json', 'r') as f:
        data = json.load(f)
    
    # Count questions per section
    section_counts = {}
    
    if 'sections' in data:
        for section in data['sections']:
            section_name = section.get('section_name', 'Unknown')
            questions = section.get('questions', [])
            section_counts[section_name] = len(questions)
            
            # Show question numbers for sections with >4 questions
            if len(questions) > 4:
                print(f'\\n{section_name}: {len(questions)} questions')
                for i, q in enumerate(questions, 1):
                    if i > 4:  # Show questions 5 and 6
                        print(f'  Question {i}: {q.get(\"question\", \"No question text\")[:80]}...')
    
    print('\\nTotal questions per section:')
    total = 0
    for section, count in section_counts.items():
        print(f'{section}: {count}')
        total += count
    print(f'\\nTOTAL: {total} questions')
    
except Exception as e:
    print(f'Error parsing JSON: {e}')
    # Try to find question patterns manually
    print('\\nSearching for question patterns in raw JSON...')
    with open('/tmp/seven_chapter_review.json', 'r') as f:
        content = f.read()
        import re
        questions = re.findall(r'\"question\":\s*\"([^\"]+)\"', content)
        print(f'Found {len(questions)} total questions in JSON')
"
    
    echo -e "\n💾 Review JSON saved to /tmp/seven_chapter_review.json"
    echo "You can examine it for the complete question structure"
    
else
    echo "❌ No reviews found with template 9"
fi

echo -e "\n🔍 Also checking if reviews are stored in separate tables:"
sudo -u postgres psql "$DB_NAME" -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE '%question%'
ORDER BY table_name;"