#!/bin/bash

# Export Seven-Chapter Review template from production database
# This script extracts the template structure using psql

# First, find the correct database name
echo "🔍 Finding database..."
DB_NAME=$(sudo -u postgres psql -t -c "SELECT datname FROM pg_database WHERE datname LIKE 'review%' OR datname LIKE 'platform%' LIMIT 1;" | tr -d ' ')

if [ -z "$DB_NAME" ]; then
    echo "❌ No review/platform database found. Available databases:"
    sudo -u postgres psql -l
    exit 1
fi

echo "✅ Using database: $DB_NAME"
echo "🔍 Exporting Seven-Chapter Review template structure..."

# Create export directory
EXPORT_DIR="seven_chapter_export_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$EXPORT_DIR"

# Export template data
echo "📋 Exporting template information..."
sudo -u postgres psql "$DB_NAME" -t -c "
SELECT row_to_json(t) FROM (
    SELECT id, name, description, template_version, healthcare_sector_id, 
           analysis_prompt, specialized_analysis, is_active, is_default
    FROM analysis_templates
    WHERE name ILIKE '%Seven-Chapter Review%'
    ORDER BY id DESC
    LIMIT 1
) t;" > "$EXPORT_DIR/template.json"

# Get template ID
TEMPLATE_ID=$(sudo -u postgres psql "$DB_NAME" -t -c "
SELECT id FROM analysis_templates 
WHERE name ILIKE '%Seven-Chapter Review%' 
ORDER BY id DESC LIMIT 1;" | tr -d ' ')

echo "✅ Found template ID: $TEMPLATE_ID"

# Export chapters
echo "📚 Exporting chapters..."
sudo -u postgres psql "$DB_NAME" -t -c "
SELECT json_agg(row_to_json(t)) FROM (
    SELECT id, chapter_id, name, description, weight, order_index, 
           is_required, enabled
    FROM template_chapters
    WHERE template_id = $TEMPLATE_ID OR analysis_template_id = $TEMPLATE_ID
    ORDER BY order_index
) t;" > "$EXPORT_DIR/chapters.json"

# Export questions for each chapter
echo "❓ Exporting questions..."
sudo -u postgres psql "$DB_NAME" -t -c "
SELECT json_agg(row_to_json(t)) FROM (
    SELECT cq.*, tc.chapter_id as parent_chapter_id
    FROM chapter_questions cq
    JOIN template_chapters tc ON cq.chapter_id = tc.id
    WHERE (tc.template_id = $TEMPLATE_ID OR tc.analysis_template_id = $TEMPLATE_ID)
    ORDER BY tc.order_index, cq.order_index
) t;" > "$EXPORT_DIR/questions.json"

# Create SQL restore script
echo "💾 Creating SQL restore script..."
cat > "$EXPORT_DIR/restore_seven_chapter.sql" << 'EOF'
-- Restore Seven-Chapter Review template structure
-- First, clear existing data to avoid conflicts

DO $$
DECLARE
    template_id INTEGER;
BEGIN
    -- Get the template ID
    SELECT id INTO template_id 
    FROM analysis_templates 
    WHERE name ILIKE '%Standard Seven-Chapter Review%';
    
    IF template_id IS NOT NULL THEN
        -- Delete existing questions and chapters
        DELETE FROM chapter_questions 
        WHERE chapter_id IN (
            SELECT id FROM template_chapters 
            WHERE template_id = template_id OR analysis_template_id = template_id
        );
        
        DELETE FROM template_chapters 
        WHERE template_id = template_id OR analysis_template_id = template_id;
        
        RAISE NOTICE 'Cleared existing data for template ID: %', template_id;
    END IF;
END $$;

-- Restore will be appended below
EOF

# Get the full structure and create inserts
echo "📝 Generating restore SQL..."
sudo -u postgres psql "$DB_NAME" -t >> "$EXPORT_DIR/restore_seven_chapter.sql" << EOF
-- Restore chapters
SELECT string_agg(
    format(
        E'INSERT INTO template_chapters (template_id, chapter_id, name, description, weight, order_index, is_required, enabled, analysis_template_id)\nVALUES ((SELECT id FROM analysis_templates WHERE name ILIKE ''%%Standard Seven-Chapter Review%%''), %L, %L, %L, %s, %s, %s, %s, (SELECT id FROM analysis_templates WHERE name ILIKE ''%%Standard Seven-Chapter Review%%''));',
        chapter_id, name, description, weight, order_index, is_required, enabled
    ), E'\n'
)
FROM template_chapters
WHERE template_id = $TEMPLATE_ID OR analysis_template_id = $TEMPLATE_ID
ORDER BY order_index;

-- Restore questions  
SELECT E'\n-- Restore questions\n' || string_agg(
    format(
        E'INSERT INTO chapter_questions (chapter_id, question_id, question_text, weight, order_index, enabled, scoring_criteria, healthcare_focus, question_prompt_template)\nVALUES ((SELECT id FROM template_chapters WHERE chapter_id = %L AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE ''%%Standard Seven-Chapter Review%%'')), %L, %L, %s, %s, %s, %L, %L, %L);',
        tc.chapter_id, cq.question_id, cq.question_text, cq.weight, cq.order_index, cq.enabled, 
        COALESCE(cq.scoring_criteria, ''), COALESCE(cq.healthcare_focus, ''), COALESCE(cq.question_prompt_template, '')
    ), E'\n'
)
FROM chapter_questions cq
JOIN template_chapters tc ON cq.chapter_id = tc.id
WHERE tc.template_id = $TEMPLATE_ID OR tc.analysis_template_id = $TEMPLATE_ID
ORDER BY tc.order_index, cq.order_index;
EOF

# Summary
echo ""
echo "✅ Export complete!"
echo "📁 Files saved in: $EXPORT_DIR/"
echo "   - template.json: Template metadata"
echo "   - chapters.json: All chapters"
echo "   - questions.json: All questions"
echo "   - restore_seven_chapter.sql: SQL script to restore the structure"

# Show counts
CHAPTER_COUNT=$(sudo -u postgres psql "$DB_NAME" -t -c "SELECT COUNT(*) FROM template_chapters WHERE template_id = $TEMPLATE_ID OR analysis_template_id = $TEMPLATE_ID;")
QUESTION_COUNT=$(sudo -u postgres psql "$DB_NAME" -t -c "SELECT COUNT(*) FROM chapter_questions cq JOIN template_chapters tc ON cq.chapter_id = tc.id WHERE tc.template_id = $TEMPLATE_ID OR tc.analysis_template_id = $TEMPLATE_ID;")

echo ""
echo "📊 Summary:"
echo "   - Chapters: $CHAPTER_COUNT"
echo "   - Questions: $QUESTION_COUNT"