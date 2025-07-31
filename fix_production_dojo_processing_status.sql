-- Fix processing status for dojo decks that have template processing results
-- These decks should show "completed" status so the "View Results" button works

-- Update all dojo pitch_decks that have results_file_path starting with 'dojo_experiment:'
-- This indicates they have completed template processing
UPDATE pitch_decks 
SET processing_status = 'completed'
WHERE data_source = 'dojo' 
  AND results_file_path LIKE 'dojo_experiment:%'
  AND processing_status != 'completed';

-- Verify the update
SELECT COUNT(*) as updated_decks
FROM pitch_decks 
WHERE data_source = 'dojo' 
  AND results_file_path LIKE 'dojo_experiment:%'
  AND processing_status = 'completed';

-- Show the status distribution for dojo decks
SELECT processing_status, COUNT(*) as count
FROM pitch_decks 
WHERE data_source = 'dojo'
GROUP BY processing_status
ORDER BY processing_status;