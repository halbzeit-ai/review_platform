#!/usr/bin/env python3
"""
Insert all 34 questions into the development database
"""
import json

# Load the extracted questions
with open('seven_chapter_34_questions.json', 'r') as f:
    data = json.load(f)

# Create SQL for all questions
sql_statements = []

chapter_id_map = {
    'Problem Analysis': 8,
    'Solution Approach': 9,
    'Product Market Fit': 10,
    'Monetization': 11,
    'Financials': 12,
    'Use of Funds': 13,
    'Organization': 14
}

questions_by_chapter = {}
for q in data['questions']:
    chapter_name = q['chapter_name']
    if chapter_name not in questions_by_chapter:
        questions_by_chapter[chapter_name] = []
    questions_by_chapter[chapter_name].append(q)

sql_file = "insert_all_34_questions.sql"

with open(sql_file, 'w') as f:
    f.write("-- Insert all 34 questions for Seven-Chapter Review template\n")
    f.write("-- Based on production data from job_249_1753945263_results.json\n\n")
    f.write("BEGIN;\n\n")
    
    for chapter_name in ['Problem Analysis', 'Solution Approach', 'Product Market Fit', 
                        'Monetization', 'Financials', 'Use of Funds', 'Organization']:
        
        chapter_db_id = chapter_id_map[chapter_name]
        questions = sorted(questions_by_chapter[chapter_name], key=lambda x: x['question_id'])
        
        f.write(f"-- {chapter_name} ({len(questions)} questions)\n")
        
        for i, q in enumerate(questions, 1):
            question_text = q['question_text'].replace("'", "''")
            scoring = q['scoring_criteria'].replace("'", "''")
            healthcare_focus = q['healthcare_focus'].replace("'", "''")
            
            sql = f"""INSERT INTO chapter_questions (
    chapter_id,
    question_id,
    question_text,
    weight,
    order_index,
    enabled,
    scoring_criteria,
    healthcare_focus
) VALUES (
    {chapter_db_id},
    '{q['question_code']}',
    '{question_text}',
    1.0,
    {i},
    true,
    '{scoring}',
    '{healthcare_focus}'
);\n\n"""
            f.write(sql)
    
    f.write("COMMIT;\n\n")
    f.write("-- Verify all questions were inserted\n")
    f.write("""SELECT 
    tc.name as chapter,
    tc.order_index,
    COUNT(cq.id) as question_count,
    array_agg(cq.order_index ORDER BY cq.order_index) as question_indices
FROM template_chapters tc
LEFT JOIN chapter_questions cq ON cq.chapter_id = tc.id
WHERE tc.analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')
GROUP BY tc.name, tc.order_index
ORDER BY tc.order_index;""")

print(f"✅ Created {sql_file} with all 34 questions")

# Count questions per chapter
total = 0
for chapter_name, questions in questions_by_chapter.items():
    count = len(questions)
    total += count
    print(f"{chapter_name}: {count} questions")

print(f"\nTotal: {total} questions")