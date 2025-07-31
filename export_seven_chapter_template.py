#!/usr/bin/env python3
"""
Export Seven-Chapter Review template structure from production database
This script extracts the template, its chapters, and all questions
Run with: sudo -u postgres python3 export_seven_chapter_template.py
"""

import psycopg2
import json
from datetime import datetime
import sys
import os

# Production database connection
DB_CONFIG = {
    'dbname': 'review_platform',
    'user': 'postgres',
    'host': 'localhost',
    'port': 5432
}

def export_seven_chapter_template():
    """Export the Seven-Chapter Review template with all its structure"""
    
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        print("🔍 Searching for Seven-Chapter Review template...")
        
        # Find the template
        cur.execute("""
            SELECT id, name, description, template_version, healthcare_sector_id, 
                   analysis_prompt, specialized_analysis, is_active, is_default
            FROM analysis_templates
            WHERE name ILIKE '%Seven-Chapter Review%'
            ORDER BY id DESC
            LIMIT 1
        """)
        
        template = cur.fetchone()
        if not template:
            print("❌ Seven-Chapter Review template not found!")
            return
        
        template_id = template[0]
        print(f"✅ Found template: {template[1]} (ID: {template_id})")
        
        # Get chapters
        cur.execute("""
            SELECT id, chapter_id, name, description, weight, order_index, 
                   is_required, enabled
            FROM template_chapters
            WHERE template_id = %s OR analysis_template_id = %s
            ORDER BY order_index
        """, (template_id, template_id))
        
        chapters = cur.fetchall()
        print(f"📚 Found {len(chapters)} chapters")
        
        # Get questions for each chapter
        all_questions = []
        for chapter in chapters:
            chapter_id = chapter[0]
            cur.execute("""
                SELECT id, question_id, question_text, weight, order_index, 
                       enabled, scoring_criteria, healthcare_focus, question_prompt_template
                FROM chapter_questions
                WHERE chapter_id = %s
                ORDER BY order_index
            """, (chapter_id,))
            
            questions = cur.fetchall()
            print(f"  └─ Chapter '{chapter[2]}': {len(questions)} questions")
            all_questions.append((chapter_id, questions))
        
        # Create export structure
        export_data = {
            'export_date': datetime.now().isoformat(),
            'template': {
                'id': template[0],
                'name': template[1],
                'description': template[2],
                'template_version': template[3],
                'healthcare_sector_id': template[4],
                'analysis_prompt': template[5],
                'specialized_analysis': json.loads(template[6]) if template[6] else None,
                'is_active': template[7],
                'is_default': template[8]
            },
            'chapters': [],
            'total_questions': 0
        }
        
        # Add chapters and questions
        for i, chapter in enumerate(chapters):
            chapter_id = chapter[0]
            questions_for_chapter = []
            
            # Find questions for this chapter
            for ch_id, questions in all_questions:
                if ch_id == chapter_id:
                    for q in questions:
                        questions_for_chapter.append({
                            'id': q[0],
                            'question_id': q[1],
                            'question_text': q[2],
                            'weight': float(q[3]) if q[3] else 1.0,
                            'order_index': q[4],
                            'enabled': q[5],
                            'scoring_criteria': q[6],
                            'healthcare_focus': q[7],
                            'question_prompt_template': q[8]
                        })
                    break
            
            export_data['chapters'].append({
                'id': chapter[0],
                'chapter_id': chapter[1],
                'name': chapter[2],
                'description': chapter[3],
                'weight': float(chapter[4]) if chapter[4] else 1.0,
                'order_index': chapter[5],
                'is_required': chapter[6],
                'enabled': chapter[7],
                'questions': questions_for_chapter
            })
            
            export_data['total_questions'] += len(questions_for_chapter)
        
        # Save to file
        filename = f"seven_chapter_template_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        print(f"\n✅ Export complete!")
        print(f"📄 Saved to: {filename}")
        print(f"📊 Summary:")
        print(f"   - Template: {export_data['template']['name']}")
        print(f"   - Chapters: {len(export_data['chapters'])}")
        print(f"   - Total Questions: {export_data['total_questions']}")
        
        # Also create SQL insert statements
        sql_filename = f"seven_chapter_template_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
        with open(sql_filename, 'w') as f:
            f.write("-- Restore Seven-Chapter Review template structure\n")
            f.write("-- Generated from production export\n\n")
            
            # Write chapter inserts
            f.write("-- Insert chapters\n")
            for chapter in export_data['chapters']:
                f.write(f"""
INSERT INTO template_chapters (
    template_id, chapter_id, name, description, weight, order_index, 
    is_required, enabled, analysis_template_id
) VALUES (
    (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%'),
    '{chapter['chapter_id']}', 
    '{chapter['name'].replace("'", "''")}', 
    '{chapter['description'].replace("'", "''")}',
    {chapter['weight']}, {chapter['order_index']}, 
    {chapter['is_required']}, {chapter['enabled']},
    (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')
) ON CONFLICT DO NOTHING;
""")
            
            # Write question inserts
            f.write("\n-- Insert questions\n")
            for chapter in export_data['chapters']:
                for question in chapter['questions']:
                    scoring_criteria = question['scoring_criteria'].replace("'", "''") if question['scoring_criteria'] else ''
                    healthcare_focus = question['healthcare_focus'].replace("'", "''") if question['healthcare_focus'] else ''
                    prompt_template = question['question_prompt_template'].replace("'", "''") if question['question_prompt_template'] else ''
                    
                    f.write(f"""
INSERT INTO chapter_questions (
    chapter_id, question_id, question_text, weight, order_index, 
    enabled, scoring_criteria, healthcare_focus, question_prompt_template
) VALUES (
    (SELECT id FROM template_chapters WHERE chapter_id = '{chapter['chapter_id']}' 
     AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')),
    '{question['question_id']}',
    '{question['question_text'].replace("'", "''")}',
    {question['weight']}, {question['order_index']},
    {question['enabled']}, 
    '{scoring_criteria}',
    '{healthcare_focus}',
    '{prompt_template}'
) ON CONFLICT DO NOTHING;
""")
        
        print(f"📄 SQL restore script saved to: {sql_filename}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    export_seven_chapter_template()