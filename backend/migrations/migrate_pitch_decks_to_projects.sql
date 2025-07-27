-- Migrate existing pitch_decks data to new project structure
-- This migration extracts project metadata from analysis results and creates project records

-- Step 1: Create projects from existing pitch_decks grouped by company_id
INSERT INTO projects (
    company_id, 
    project_name, 
    funding_round, 
    funding_sought, 
    healthcare_sector_id, 
    company_offering, 
    project_metadata,
    created_at, 
    updated_at
)
SELECT DISTINCT
    pd.company_id,
    COALESCE(u.company_name, 'Initial Funding Round') as project_name,
    'initial' as funding_round, -- Default for existing data
    
    -- Extract funding_sought from ai_analysis_results JSON if available
    json_extract(pd.ai_analysis_results, '$.funding_sought') as funding_sought,
    
    -- Healthcare sector will be populated later when we have classification data
    NULL as healthcare_sector_id,
    
    -- Extract company_offering from ai_analysis_results JSON if available  
    json_extract(pd.ai_analysis_results, '$.company_offering') as company_offering,
    
    -- Store any additional metadata from analysis results
    json_object(
        'migrated_from_pitch_deck', 1,
        'original_data_source', pd.data_source,
        'ai_extracted_startup_name', pd.ai_extracted_startup_name
    ) as project_metadata,
    
    MIN(pd.created_at) as created_at,
    MAX(pd.created_at) as updated_at
    
FROM pitch_decks pd
JOIN users u ON pd.user_id = u.id
WHERE pd.company_id IS NOT NULL
GROUP BY pd.company_id, u.company_name;

-- Step 2: Migrate pitch_decks to project_documents
INSERT INTO project_documents (
    project_id,
    document_type,
    file_name,
    file_path,
    original_filename,
    file_size,
    processing_status,
    extracted_data,
    analysis_results_path,
    uploaded_by,
    upload_date,
    is_active
)
SELECT 
    p.id as project_id,
    'pitch_deck' as document_type,
    pd.file_name,
    pd.file_path,
    pd.file_name as original_filename,
    
    -- Try to get file size (will be NULL if file doesn't exist)
    NULL as file_size, -- Will be populated by file system check later
    
    pd.processing_status,
    
    -- Store extracted data from ai_analysis_results
    pd.ai_analysis_results as extracted_data,
    
    pd.results_file_path as analysis_results_path,
    pd.user_id as uploaded_by,
    pd.created_at as upload_date,
    1 as is_active
    
FROM pitch_decks pd
JOIN users u ON pd.user_id = u.id
JOIN projects p ON p.company_id = pd.company_id
WHERE pd.company_id IS NOT NULL;

-- Step 3: Migrate existing reviews to project_interactions
INSERT INTO project_interactions (
    project_id,
    interaction_type,
    title,
    content,
    document_id,
    created_by,
    status,
    interaction_metadata,
    created_at,
    updated_at
)
SELECT 
    p.id as project_id,
    'review' as interaction_type,
    'Initial Pitch Deck Review' as title,
    r.review_data as content,
    doc.id as document_id,
    
    -- For now, set created_by to the document uploader (we can adjust this later)
    doc.uploaded_by as created_by,
    
    CASE r.status
        WHEN 'completed' THEN 'active'
        WHEN 'pending' THEN 'active'
        WHEN 'in_review' THEN 'active'
        ELSE 'active'
    END as status,
    
    json_object(
        'migrated_from_review', 1,
        'original_status', r.status,
        's3_review_url', r.s3_review_url
    ) as interaction_metadata,
    
    r.created_at,
    r.created_at as updated_at
    
FROM reviews r
JOIN pitch_decks pd ON r.pitch_deck_id = pd.id
JOIN users u ON pd.user_id = u.id
JOIN projects p ON p.company_id = pd.company_id
JOIN project_documents doc ON doc.project_id = p.id AND doc.file_path = pd.file_path
WHERE r.review_data IS NOT NULL;

-- Step 4: Migrate existing questions to project_interactions
INSERT INTO project_interactions (
    project_id,
    interaction_type,
    title,
    content,
    document_id,
    created_by,
    status,
    interaction_metadata,
    created_at,
    updated_at
)
SELECT 
    p.id as project_id,
    'question' as interaction_type,
    'Question about pitch deck' as title,
    q.question_text as content,
    doc.id as document_id,
    q.asked_by as created_by,
    'active' as status,
    
    json_object(
        'migrated_from_question', 1,
        'answers', (
            SELECT json_group_array(
                json_object(
                    'answer_text', a.answer_text,
                    'answered_by', a.answered_by,
                    'created_at', a.created_at
                )
            )
            FROM answers a WHERE a.question_id = q.id
        )
    ) as interaction_metadata,
    
    q.created_at,
    q.created_at as updated_at
    
FROM questions q
JOIN reviews r ON q.review_id = r.id
JOIN pitch_decks pd ON r.pitch_deck_id = pd.id
JOIN users u ON pd.user_id = u.id
JOIN projects p ON p.company_id = pd.company_id
JOIN project_documents doc ON doc.project_id = p.id AND doc.file_path = pd.file_path;

-- Step 5: Create a summary view for verification
CREATE VIEW IF NOT EXISTS migration_summary AS
SELECT 
    'Projects Created' as item,
    COUNT(*) as count
FROM projects
WHERE json_extract(project_metadata, '$.migrated_from_pitch_deck') = 1

UNION ALL

SELECT 
    'Documents Migrated' as item,
    COUNT(*) as count
FROM project_documents
WHERE document_type = 'pitch_deck'

UNION ALL

SELECT 
    'Reviews Migrated' as item,
    COUNT(*) as count
FROM project_interactions
WHERE interaction_type = 'review' 
AND json_extract(interaction_metadata, '$.migrated_from_review') = 1

UNION ALL

SELECT 
    'Questions Migrated' as item,
    COUNT(*) as count
FROM project_interactions
WHERE interaction_type = 'question'
AND json_extract(interaction_metadata, '$.migrated_from_question') = 1;

-- Display migration summary
SELECT * FROM migration_summary;