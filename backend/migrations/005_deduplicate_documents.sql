-- Deduplicate project_documents that were created by Cartesian product in migration
-- Keep only one document per unique file_path, preferring the earliest project

-- Step 1: Identify duplicates and which ones to keep
WITH document_dedup AS (
    SELECT 
        file_path,
        MIN(id) as keep_document_id,
        COUNT(*) as duplicate_count,
        array_agg(id ORDER BY id) as all_document_ids
    FROM project_documents
    WHERE document_type = 'pitch_deck'
    GROUP BY file_path
    HAVING COUNT(*) > 1
),
documents_to_delete AS (
    SELECT 
        unnest(array_remove(all_document_ids, keep_document_id)) as delete_document_id,
        duplicate_count
    FROM document_dedup
)

-- Step 2: Delete duplicate documents
DELETE FROM project_documents 
WHERE id IN (SELECT delete_document_id FROM documents_to_delete);

-- Step 3: Show cleanup results
WITH cleanup_summary AS (
    SELECT 
        'Before cleanup' as status,
        5643 as document_count  -- Known count from investigation
    
    UNION ALL
    
    SELECT 
        'After cleanup' as status,
        COUNT(*) as document_count
    FROM project_documents
    WHERE document_type = 'pitch_deck'
    
    UNION ALL
    
    SELECT 
        'Unique file paths' as status,
        COUNT(DISTINCT file_path) as document_count
    FROM project_documents
    WHERE document_type = 'pitch_deck'
)
SELECT * FROM cleanup_summary;

-- Step 4: Verify no duplicates remain
SELECT 
    'Remaining duplicates' as check_type,
    COUNT(*) as count
FROM (
    SELECT file_path
    FROM project_documents
    WHERE document_type = 'pitch_deck'
    GROUP BY file_path
    HAVING COUNT(*) > 1
) duplicates_check;