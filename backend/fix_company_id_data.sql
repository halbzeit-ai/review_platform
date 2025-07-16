-- Fix company_id data migration
-- Update existing records to set company_id based on user email

UPDATE pitch_decks 
SET company_id = (
    SELECT SUBSTR(u.email, 1, INSTR(u.email, '@') - 1)
    FROM users u 
    WHERE u.id = pitch_decks.user_id
)
WHERE company_id IS NULL OR company_id = '';

-- Update existing records to set results_file_path based on processing_status
-- For completed decks, set the expected results file path
UPDATE pitch_decks 
SET results_file_path = '/mnt/shared/projects/' || company_id || '/analysis/' || 
    SUBSTR(file_name, 1, LENGTH(file_name) - 4) || '/results.json'
WHERE processing_status = 'completed' 
  AND ai_analysis_results IS NOT NULL 
  AND (results_file_path IS NULL OR results_file_path = '');