-- Fix template editability
-- Only Seven-Chapter Review should be immutable (is_default = true)
-- All 8 healthcare sector templates should be editable (is_default = false)

BEGIN;

-- Make all healthcare sector templates editable
UPDATE analysis_templates 
SET is_default = false
WHERE name NOT ILIKE '%Seven-Chapter Review%';

-- Ensure Seven-Chapter Review remains immutable
UPDATE analysis_templates 
SET is_default = true
WHERE name ILIKE '%Seven-Chapter Review%';

COMMIT;

-- Verify the changes
SELECT 
    id,
    name,
    is_default,
    CASE 
        WHEN is_default THEN 'IMMUTABLE (read-only)'
        ELSE 'EDITABLE'
    END as status
FROM analysis_templates 
ORDER BY is_default DESC, id;