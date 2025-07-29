-- Investigate visual analysis data format for 4-digit deck IDs
-- This will help understand why DeckViewer shows no visual analysis text

-- First, check what 4-digit decks exist and if they have cached visual analysis
SELECT pd.id as deck_id, 
       pd.file_name, 
       pd.data_source,
       CASE WHEN vac.pitch_deck_id IS NOT NULL THEN 'YES' ELSE 'NO' END as has_cache
FROM pitch_decks pd 
LEFT JOIN visual_analysis_cache vac ON pd.id = vac.pitch_deck_id 
WHERE pd.id > 1000 
ORDER BY pd.id DESC 
LIMIT 5;

-- Now look at the actual cached analysis data format for 4-digit decks
SELECT pd.id as deck_id,
       pd.file_name,
       vac.vision_model_used,
       vac.created_at,
       -- Show first 300 characters of the analysis JSON to understand format
       SUBSTRING(vac.analysis_result_json, 1, 300) as analysis_sample,
       -- Check if it's a JSON array or object
       CASE 
         WHEN vac.analysis_result_json LIKE '[%' THEN 'JSON_ARRAY'
         WHEN vac.analysis_result_json LIKE '{%' THEN 'JSON_OBJECT'
         ELSE 'OTHER'
       END as json_type
FROM pitch_decks pd 
INNER JOIN visual_analysis_cache vac ON pd.id = vac.pitch_deck_id 
WHERE pd.id > 1000 
ORDER BY pd.id DESC 
LIMIT 3;

-- Compare with 3-digit decks that work (if any exist)
SELECT pd.id as deck_id,
       pd.file_name,
       vac.vision_model_used,
       -- Show first 300 characters to compare format
       SUBSTRING(vac.analysis_result_json, 1, 300) as analysis_sample,
       CASE 
         WHEN vac.analysis_result_json LIKE '[%' THEN 'JSON_ARRAY'
         WHEN vac.analysis_result_json LIKE '{%' THEN 'JSON_OBJECT'
         ELSE 'OTHER'
       END as json_type
FROM pitch_decks pd 
INNER JOIN visual_analysis_cache vac ON pd.id = vac.pitch_deck_id 
WHERE pd.id < 1000 AND pd.id > 100
ORDER BY pd.id DESC 
LIMIT 3;