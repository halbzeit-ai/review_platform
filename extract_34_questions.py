#!/usr/bin/env python3
"""
Extract all 34 questions from the Seven-Chapter Review results.json
"""

import json
import os
import sys

# Get input file from command line or use default
if len(sys.argv) > 1:
    results_file = sys.argv[1]
else:
    # Use environment-aware default path
    shared_mount = os.getenv('SHARED_FILESYSTEM_MOUNT_PATH', '/mnt/CPU-GPU')
    results_file = os.path.join(shared_mount, 'results', 'job_249_1753945263_results.json')

print(f"Loading results from: {results_file}")

if not os.path.exists(results_file):
    print(f"❌ Results file not found: {results_file}")
    print("Usage: python extract_34_questions.py [path_to_results.json]")
    sys.exit(1)

# Load the results file
with open(results_file, 'r') as f:
    data = json.load(f)

# Extract all questions from chapter_analysis
all_questions = []
chapter_order = {
    'problem_analysis': 1,
    'solution_approach': 2,
    'product_market_fit': 3,
    'monetization': 4,
    'financials': 5,
    'use_of_funds': 6,
    'organization': 7
}

print("=== EXTRACTING ALL 34 QUESTIONS ===\n")

total_count = 0
for chapter_key, chapter_data in sorted(data['chapter_analysis'].items(), key=lambda x: chapter_order.get(x[0], 999)):
    chapter_name = chapter_data['name']
    questions = chapter_data.get('questions', [])
    
    print(f"\n{chapter_name} ({len(questions)} questions):")
    print("-" * 80)
    
    for q in questions:
        q_id = q.get('id', 0)
        q_code = q.get('question_id', '')
        q_text = q.get('question_text', '')
        scoring = q.get('scoring_criteria', '')
        healthcare_focus = q.get('healthcare_focus', '')
        
        total_count += 1
        
        print(f"\nQuestion {q_id} ({q_code}):")
        print(f"Text: {q_text}")
        print(f"Scoring: {scoring}")
        print(f"Healthcare Focus: {healthcare_focus}")
        
        all_questions.append({
            'chapter_key': chapter_key,
            'chapter_name': chapter_name,
            'question_id': q_id,
            'question_code': q_code,
            'question_text': q_text,
            'scoring_criteria': scoring,
            'healthcare_focus': healthcare_focus
        })

print(f"\n\nTOTAL QUESTIONS FOUND: {total_count}")

# Save to JSON for import
with open('seven_chapter_34_questions.json', 'w') as f:
    json.dump({
        'total_questions': total_count,
        'questions': all_questions
    }, f, indent=2)

print("\n✅ Saved all questions to seven_chapter_34_questions.json")

# Create SQL restore script for missing questions
print("\n=== CREATING SQL FOR MISSING QUESTIONS (5 & 6) ===")

# Map chapter keys to expected question counts
expected_questions = {
    'problem_analysis': 4,
    'solution_approach': 5,
    'product_market_fit': 5,
    'monetization': 6,
    'financials': 5,
    'use_of_funds': 4,
    'organization': 5
}

sql_statements = []
missing_count = 0

for q in all_questions:
    # Only generate SQL for questions that are missing (currently DB has max 4 per chapter)
    chapter_key = q['chapter_key']
    q_num = q['question_id']
    
    # Questions 1-4 already exist in DB, only add 5 and 6
    if q_num > 4:
        sql = f"""
-- {q['chapter_name']} - Question {q_num}
INSERT INTO chapter_questions (
    chapter_id,
    question_id,
    question_text,
    weight,
    order_index,
    enabled,
    scoring_criteria,
    healthcare_focus
) VALUES (
    (SELECT id FROM template_chapters 
     WHERE chapter_id = '{chapter_key}' 
     AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')),
    '{q['question_code']}_{q_num}',
    '{q['question_text'].replace("'", "''")}',
    1.0,
    {q_num},
    true,
    '{q['scoring_criteria'].replace("'", "''")}',
    '{q['healthcare_focus'].replace("'", "''")}'
);"""
        sql_statements.append(sql)
        missing_count += 1
        print(f"\n{q['chapter_name']} - Question {q_num}: {q['question_text'][:60]}...")

# Save SQL restore script
with open('restore_missing_questions.sql', 'w') as f:
    f.write("-- Restore missing questions (5 & 6) for Seven-Chapter Review template\n")
    f.write("-- Expected: 6 missing questions (Solution:1, Product Market Fit:1, Monetization:2, Financials:1, Organization:1)\n")
    f.write("-- Total missing questions to restore: {}\n\n".format(len(sql_statements)))
    f.write("BEGIN;\n")
    f.write("\n".join(sql_statements))
    f.write("\n\nCOMMIT;\n")

print(f"\n✅ Created restore_missing_questions.sql with {missing_count} missing questions")
print("\nExpected missing questions by chapter:")
for chapter, expected in expected_questions.items():
    if expected > 4:
        print(f"  {chapter}: question(s) {', '.join(str(i) for i in range(5, expected + 1))}")