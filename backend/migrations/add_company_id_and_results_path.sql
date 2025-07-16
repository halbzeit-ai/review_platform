-- Add company_id and results_file_path columns to pitch_decks table
-- This migration adds project-based access control and results file tracking

-- Add company_id column for project-based access
ALTER TABLE pitch_decks ADD COLUMN company_id VARCHAR;

-- Add results_file_path column for analysis results tracking
ALTER TABLE pitch_decks ADD COLUMN results_file_path VARCHAR;

-- Create index on company_id for faster lookups
CREATE INDEX idx_pitch_decks_company_id ON pitch_decks(company_id);

-- Update existing records to set company_id based on user email
-- Extract company identifier from email (everything before @)
UPDATE pitch_decks 
SET company_id = (
    SELECT SUBSTR(u.email, 1, INSTR(u.email, '@') - 1)
    FROM users u 
    WHERE u.id = pitch_decks.user_id
);

-- Update existing records to set results_file_path based on processing_status
-- For completed decks, set the expected results file path
UPDATE pitch_decks 
SET results_file_path = '/mnt/shared/projects/' || company_id || '/analysis/' || file_name || '/results.json'
WHERE processing_status = 'completed' AND ai_analysis_results IS NOT NULL;