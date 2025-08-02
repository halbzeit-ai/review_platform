-- Clean up dojo entries from database for fresh upload
-- This will remove all dojo pitch decks and related data

-- First, check what we're about to delete
SELECT COUNT(*) as dojo_deck_count FROM pitch_decks WHERE data_source = 'dojo';

-- Delete any visual analysis cache entries for dojo decks
DELETE FROM visual_analysis_cache 
WHERE pitch_deck_id IN (SELECT id FROM pitch_decks WHERE data_source = 'dojo');

-- Delete any reviews for dojo decks
DELETE FROM reviews 
WHERE pitch_deck_id IN (SELECT id FROM pitch_decks WHERE data_source = 'dojo');

-- Delete any chapter analysis results for dojo decks
DELETE FROM chapter_analysis_results
WHERE pitch_deck_id IN (SELECT id FROM pitch_decks WHERE data_source = 'dojo');

-- Delete any question analysis results for dojo decks
DELETE FROM question_analysis_results
WHERE pitch_deck_id IN (SELECT id FROM pitch_decks WHERE data_source = 'dojo');

-- Finally, delete the dojo pitch decks themselves
DELETE FROM pitch_decks WHERE data_source = 'dojo';

-- Verify cleanup
SELECT COUNT(*) as remaining_dojo_decks FROM pitch_decks WHERE data_source = 'dojo';