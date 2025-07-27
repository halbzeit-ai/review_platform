-- Clean up duplicate projects created during migration
-- Keep one project per company_id and reassign all documents to it

-- Step 1: Identify duplicate projects and keep the earliest one per company
WITH project_dedup AS (
    SELECT 
        company_id,
        MIN(id) as keep_project_id,
        array_agg(id ORDER BY id) as all_project_ids
    FROM projects
    WHERE project_metadata->>'migrated_from_pitch_deck' = 'true'
    GROUP BY company_id
    HAVING COUNT(*) > 1
),
projects_to_delete AS (
    SELECT 
        unnest(array_remove(all_project_ids, keep_project_id)) as delete_project_id,
        keep_project_id
    FROM project_dedup
)
-- Step 2: Reassign all documents from duplicate projects to the kept project
UPDATE project_documents 
SET project_id = ptd.keep_project_id
FROM projects_to_delete ptd
WHERE project_documents.project_id = ptd.delete_project_id;

-- Step 3: Reassign all interactions from duplicate projects to the kept project
WITH project_dedup AS (
    SELECT 
        company_id,
        MIN(id) as keep_project_id,
        array_agg(id ORDER BY id) as all_project_ids
    FROM projects
    WHERE project_metadata->>'migrated_from_pitch_deck' = 'true'
    GROUP BY company_id
    HAVING COUNT(*) > 1
),
projects_to_delete AS (
    SELECT 
        unnest(array_remove(all_project_ids, keep_project_id)) as delete_project_id,
        keep_project_id
    FROM project_dedup
)
UPDATE project_interactions 
SET project_id = ptd.keep_project_id
FROM projects_to_delete ptd
WHERE project_interactions.project_id = ptd.delete_project_id;

-- Step 4: Delete the duplicate projects
WITH project_dedup AS (
    SELECT 
        company_id,
        MIN(id) as keep_project_id,
        array_agg(id ORDER BY id) as all_project_ids
    FROM projects
    WHERE project_metadata->>'migrated_from_pitch_deck' = 'true'
    GROUP BY company_id
    HAVING COUNT(*) > 1
),
projects_to_delete AS (
    SELECT 
        unnest(array_remove(all_project_ids, keep_project_id)) as delete_project_id
    FROM project_dedup
)
DELETE FROM projects 
WHERE id IN (SELECT delete_project_id FROM projects_to_delete);

-- Step 5: Show cleanup results
SELECT 
    'Projects after cleanup' as status,
    COUNT(*) as count
FROM projects
WHERE project_metadata->>'migrated_from_pitch_deck' = 'true'

UNION ALL

SELECT 
    'Documents reassigned' as status,
    COUNT(*) as count
FROM project_documents pd
JOIN projects p ON pd.project_id = p.id
WHERE p.project_metadata->>'migrated_from_pitch_deck' = 'true';