-- Investigate specific project 1005 and its deck visual analysis issue
-- This will help understand why DeckViewer shows no visual analysis text

-- First, find the actual deck associated with project 1005
SELECT p.id as project_id,
       p.company_id, 
       p.project_name,
       pd.id as document_id,
       pd.file_name,
       pd.document_type,
       pd.file_path,
       CASE WHEN vac.pitch_deck_id IS NOT NULL THEN 'YES' ELSE 'NO' END as has_visual_cache
FROM projects p 
LEFT JOIN project_documents pd ON p.id = pd.project_id 
LEFT JOIN visual_analysis_cache vac ON pd.id = vac.pitch_deck_id
WHERE p.id = 1005 AND pd.document_type = 'pitch_deck' AND pd.is_active = TRUE;

-- Check if there are any deck IDs in that range that DO have visual analysis
SELECT pd.id as deck_id, 
       pd.file_name,
       vac.pitch_deck_id,
       SUBSTRING(vac.analysis_result_json, 1, 100) as sample_analysis
FROM pitch_decks pd 
INNER JOIN visual_analysis_cache vac ON pd.id = vac.pitch_deck_id 
WHERE pd.data_source = 'dojo'
ORDER BY pd.id DESC 
LIMIT 10;

-- Check recent project documents that might not have visual analysis
SELECT pd.id as document_id,
       pd.file_name, 
       pd.created_at,
       p.id as project_id,
       p.company_id,
       CASE WHEN vac.pitch_deck_id IS NOT NULL THEN 'YES' ELSE 'NO' END as has_visual_cache
FROM project_documents pd
JOIN projects p ON pd.project_id = p.id
LEFT JOIN visual_analysis_cache vac ON pd.id = vac.pitch_deck_id
WHERE pd.document_type = 'pitch_deck' 
  AND pd.is_active = TRUE 
  AND p.company_id LIKE '%dojo%'
ORDER BY pd.created_at DESC 
LIMIT 10;