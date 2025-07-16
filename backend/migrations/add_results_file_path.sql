-- Add results_file_path column to pitch_decks table
-- This column will store the path to the analysis results file

ALTER TABLE pitch_decks ADD COLUMN results_file_path VARCHAR;

-- Update existing records to set results_file_path based on processing_status
-- For completed decks, we'll need to set this manually or through a separate process
UPDATE pitch_decks 
SET results_file_path = '/mnt/shared/results/' || file_name || '_analysis.json'
WHERE processing_status = 'completed' AND ai_analysis_results IS NOT NULL;