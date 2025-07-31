#!/bin/bash

# Simple export for Seven-Chapter Review template
# Focus on getting ALL questions (should be 34)

echo "🔍 Finding database..."
DB_NAME=$(sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE datname LIKE 'review%' OR datname LIKE 'platform%' LIMIT 1;" | tr -d ' ')
echo "✅ Using database: $DB_NAME"

EXPORT_DIR="seven_chapter_export_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$EXPORT_DIR"

# Get template info
echo "📋 Getting template ID..."
TEMPLATE_ID=$(sudo -u postgres psql "$DB_NAME" -t -c "
SELECT id FROM analysis_templates 
WHERE name ILIKE '%Seven-Chapter%' 
ORDER BY id DESC LIMIT 1;" | tr -d ' ')

echo "✅ Template ID: $TEMPLATE_ID"

# Export all chapters with count
echo "📚 Exporting chapters..."
sudo -u postgres psql "$DB_NAME" -A -F'|' -c "
SELECT 
    tc.id,
    tc.chapter_id,
    tc.name,
    tc.description,
    tc.weight,
    tc.order_index,
    tc.is_required,
    tc.enabled,
    COUNT(cq.id) as question_count
FROM template_chapters tc
LEFT JOIN chapter_questions cq ON cq.chapter_id = tc.id
WHERE tc.template_id = $TEMPLATE_ID OR tc.analysis_template_id = $TEMPLATE_ID
GROUP BY tc.id, tc.chapter_id, tc.name, tc.description, tc.weight, tc.order_index, tc.is_required, tc.enabled
ORDER BY tc.order_index;" > "$EXPORT_DIR/chapters_with_counts.txt"

echo "Chapter breakdown:"
cat "$EXPORT_DIR/chapters_with_counts.txt" | column -t -s'|'

# Export ALL questions
echo -e "\n❓ Exporting ALL questions..."
sudo -u postgres psql "$DB_NAME" -A -F'|' -c "
SELECT 
    tc.name as chapter_name,
    tc.order_index as chapter_order,
    cq.id,
    cq.question_id,
    LEFT(cq.question_text, 100) as question_preview,
    cq.order_index,
    cq.enabled
FROM chapter_questions cq
JOIN template_chapters tc ON cq.chapter_id = tc.id
WHERE tc.template_id = $TEMPLATE_ID OR tc.analysis_template_id = $TEMPLATE_ID
ORDER BY tc.order_index, cq.order_index;" > "$EXPORT_DIR/all_questions.txt"

TOTAL_QUESTIONS=$(wc -l < "$EXPORT_DIR/all_questions.txt")
echo "Total questions found: $((TOTAL_QUESTIONS - 1))"

# Create detailed JSON export
echo -e "\n💾 Creating detailed JSON export..."
cat > "$EXPORT_DIR/export_queries.sql" << EOF
-- Get complete chapter and question data
SELECT json_build_object(
    'template_id', $TEMPLATE_ID,
    'chapters', (
        SELECT json_agg(
            json_build_object(
                'id', tc.id,
                'chapter_id', tc.chapter_id,
                'name', tc.name,
                'description', tc.description,
                'weight', tc.weight,
                'order_index', tc.order_index,
                'is_required', tc.is_required,
                'enabled', tc.enabled,
                'questions', (
                    SELECT json_agg(
                        json_build_object(
                            'id', cq.id,
                            'question_id', cq.question_id,
                            'question_text', cq.question_text,
                            'weight', cq.weight,
                            'order_index', cq.order_index,
                            'enabled', cq.enabled,
                            'scoring_criteria', cq.scoring_criteria,
                            'healthcare_focus', cq.healthcare_focus
                        ) ORDER BY cq.order_index
                    )
                    FROM chapter_questions cq
                    WHERE cq.chapter_id = tc.id
                )
            ) ORDER BY tc.order_index
        )
        FROM template_chapters tc
        WHERE tc.template_id = $TEMPLATE_ID OR tc.analysis_template_id = $TEMPLATE_ID
    )
);
EOF

sudo -u postgres psql "$DB_NAME" -t -f "$EXPORT_DIR/export_queries.sql" > "$EXPORT_DIR/complete_structure.json"

# Create restore SQL
echo -e "\n📝 Creating restore SQL..."
cat > "$EXPORT_DIR/restore_complete.sql" << 'EOF'
-- Complete restore script for Seven-Chapter Review template
-- Expected: 7 chapters, 34 questions total

BEGIN;

-- Clear existing data
DELETE FROM chapter_questions 
WHERE chapter_id IN (
    SELECT id FROM template_chapters 
    WHERE analysis_template_id = (
        SELECT id FROM analysis_templates 
        WHERE name ILIKE '%Standard Seven-Chapter Review%'
    )
);

DELETE FROM template_chapters 
WHERE analysis_template_id = (
    SELECT id FROM analysis_templates 
    WHERE name ILIKE '%Standard Seven-Chapter Review%'
);

-- Data will be inserted below
EOF

# Generate insert statements from actual data
sudo -u postgres psql "$DB_NAME" -t >> "$EXPORT_DIR/restore_complete.sql" << EOF
-- Insert chapters
SELECT string_agg(
    'INSERT INTO template_chapters (template_id, chapter_id, name, description, weight, order_index, is_required, enabled, analysis_template_id) VALUES (' ||
    '(SELECT id FROM analysis_templates WHERE name ILIKE ''%Standard Seven-Chapter Review%''), ' ||
    '''' || chapter_id || ''', ' ||
    '''' || REPLACE(name, '''', '''''') || ''', ' ||
    '''' || REPLACE(description, '''', '''''') || ''', ' ||
    weight || ', ' ||
    order_index || ', ' ||
    is_required || ', ' ||
    enabled || ', ' ||
    '(SELECT id FROM analysis_templates WHERE name ILIKE ''%Standard Seven-Chapter Review%''));',
    E'\n'
)
FROM template_chapters
WHERE template_id = $TEMPLATE_ID OR analysis_template_id = $TEMPLATE_ID
ORDER BY order_index;

-- Insert questions
SELECT E'\n-- Insert questions (expecting 34 total)\n' || string_agg(
    'INSERT INTO chapter_questions (chapter_id, question_id, question_text, weight, order_index, enabled, scoring_criteria, healthcare_focus) VALUES (' ||
    '(SELECT id FROM template_chapters WHERE chapter_id = ''' || tc.chapter_id || ''' AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE ''%Standard Seven-Chapter Review%'')), ' ||
    '''' || cq.question_id || ''', ' ||
    '''' || REPLACE(cq.question_text, '''', '''''') || ''', ' ||
    cq.weight || ', ' ||
    cq.order_index || ', ' ||
    cq.enabled || ', ' ||
    '''' || COALESCE(REPLACE(cq.scoring_criteria, '''', ''''''), '') || ''', ' ||
    '''' || COALESCE(REPLACE(cq.healthcare_focus, '''', ''''''), '') || ''');',
    E'\n'
)
FROM chapter_questions cq
JOIN template_chapters tc ON cq.chapter_id = tc.id
WHERE tc.template_id = $TEMPLATE_ID OR tc.analysis_template_id = $TEMPLATE_ID
ORDER BY tc.order_index, cq.order_index;
EOF

echo "COMMIT;" >> "$EXPORT_DIR/restore_complete.sql"

# Summary
echo -e "\n✅ Export complete!"
echo "📁 Files in $EXPORT_DIR/:"
ls -la "$EXPORT_DIR/"

# Final count
FINAL_COUNT=$(grep -c "INSERT INTO chapter_questions" "$EXPORT_DIR/restore_complete.sql" || echo 0)
echo -e "\n📊 Final Summary:"
echo "   - Expected questions: 34"
echo "   - Found questions: $FINAL_COUNT"
if [ "$FINAL_COUNT" -ne "34" ]; then
    echo "   ⚠️  WARNING: Missing $((34 - FINAL_COUNT)) questions!"
fi