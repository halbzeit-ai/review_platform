-- Verify Project Migration Results
-- Check that data was migrated correctly from pitch_decks to project structure

-- 1. Show migration summary
SELECT 
    'Original pitch_decks' as table_name,
    COUNT(*) as count
FROM pitch_decks
WHERE company_id IS NOT NULL

UNION ALL

SELECT 
    'Created projects' as table_name,
    COUNT(*) as count
FROM projects

UNION ALL

SELECT 
    'Migrated documents' as table_name,
    COUNT(*) as count
FROM project_documents
WHERE document_type = 'pitch_deck'

UNION ALL

SELECT 
    'Migrated reviews' as table_name,
    COUNT(*) as count
FROM project_interactions
WHERE interaction_type = 'review'

UNION ALL

SELECT 
    'Migrated questions' as table_name,
    COUNT(*) as count
FROM project_interactions
WHERE interaction_type = 'question';

-- 2. Show project breakdown by company
SELECT 
    p.company_id,
    p.project_name,
    p.funding_round,
    COUNT(pd.id) as document_count,
    COUNT(pi.id) as interaction_count,
    p.created_at
FROM projects p
LEFT JOIN project_documents pd ON p.id = pd.project_id
LEFT JOIN project_interactions pi ON p.id = pi.project_id
GROUP BY p.id, p.company_id, p.project_name, p.funding_round, p.created_at
ORDER BY p.company_id;

-- 3. Show sample of extracted project metadata
SELECT 
    p.company_id,
    p.project_name,
    p.funding_sought,
    p.company_offering,
    p.project_metadata
FROM projects p
LIMIT 5;