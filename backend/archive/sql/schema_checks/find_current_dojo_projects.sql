-- Find current dojo projects and their deck relationships
-- This will show what project IDs actually exist after the fresh processing

-- Find all dojo-related projects 
SELECT p.id as project_id,
       p.company_id,
       p.project_name,
       p.is_test,
       COUNT(pd.id) as deck_count
FROM projects p 
LEFT JOIN project_documents pd ON p.id = pd.project_id 
  AND pd.document_type = 'pitch_deck' 
  AND pd.is_active = TRUE
WHERE (p.company_id LIKE '%dojo%' OR p.is_test = TRUE)
GROUP BY p.id, p.company_id, p.project_name, p.is_test
ORDER BY p.id DESC;

-- Find the mapping between recent project_documents and pitch_decks with visual analysis
SELECT p.id as project_id,
       p.company_id,
       pd.id as document_id,
       pd.file_name,
       -- Try to find matching pitch_deck by file_name similarity
       (SELECT pitch_deck.id FROM pitch_decks pitch_deck 
        WHERE pitch_deck.file_name = pd.file_name 
          AND pitch_deck.data_source = 'dojo' 
        LIMIT 1) as matching_pitch_deck_id,
       -- Check if that pitch_deck has visual analysis
       (SELECT CASE WHEN COUNT(*) > 0 THEN 'YES' ELSE 'NO' END 
        FROM visual_analysis_cache vac 
        JOIN pitch_decks pitch_deck ON vac.pitch_deck_id = pitch_deck.id
        WHERE pitch_deck.file_name = pd.file_name 
          AND pitch_deck.data_source = 'dojo') as has_visual_analysis
FROM projects p 
JOIN project_documents pd ON p.id = pd.project_id
WHERE (p.company_id LIKE '%dojo%' OR p.is_test = TRUE)
  AND pd.document_type = 'pitch_deck' 
  AND pd.is_active = TRUE
ORDER BY p.id DESC
LIMIT 10;