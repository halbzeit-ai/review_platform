-- Migrate existing pitch_decks data to new project structure (Fixed version)
-- This migration extracts project metadata from analysis results and creates project records

-- Step 1: Create projects from existing pitch_decks grouped by company_id
-- Use a two-step approach to handle the JSON extraction properly
WITH project_base AS (
    SELECT DISTINCT
        pd.company_id,
        u.company_name,
        pd.data_source,
        pd.ai_extracted_startup_name,
        -- Get first non-null ai_analysis_results for JSON extraction
        (array_agg(pd.ai_analysis_results ORDER BY pd.created_at) FILTER (WHERE pd.ai_analysis_results IS NOT NULL AND pd.ai_analysis_results != ''))[1] as sample_analysis_results,
        MIN(pd.created_at) as created_at,
        MAX(pd.created_at) as updated_at
    FROM pitch_decks pd
    JOIN users u ON pd.user_id = u.id
    WHERE pd.company_id IS NOT NULL
    GROUP BY pd.company_id, u.company_name, pd.data_source, pd.ai_extracted_startup_name
)
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
SELECT 
    pb.company_id,
    COALESCE(pb.company_name || ' - Initial Round', 'Initial Funding Round') as project_name,
    'initial' as funding_round,
    
    -- Extract funding_sought from ai_analysis_results JSON if available
    CASE 
        WHEN pb.sample_analysis_results IS NOT NULL THEN
            CASE 
                WHEN pb.sample_analysis_results::text ~ '^{.*}$' THEN 
                    (pb.sample_analysis_results::jsonb)->>'funding_sought'
                ELSE NULL
            END
        ELSE NULL
    END as funding_sought,
    
    -- Healthcare sector will be populated later when we have classification data
    NULL::INTEGER as healthcare_sector_id,
    
    -- Extract company_offering from ai_analysis_results JSON if available  
    CASE 
        WHEN pb.sample_analysis_results IS NOT NULL THEN
            CASE 
                WHEN pb.sample_analysis_results::text ~ '^{.*}$' THEN 
                    (pb.sample_analysis_results::jsonb)->>'company_offering'
                ELSE NULL
            END
        ELSE NULL
    END as company_offering,
    
    -- Store any additional metadata from analysis results
    jsonb_build_object(
        'migrated_from_pitch_deck', true,
        'original_data_source', pb.data_source,
        'ai_extracted_startup_name', pb.ai_extracted_startup_name
    ) as project_metadata,
    
    pb.created_at,
    pb.updated_at
FROM project_base pb
ON CONFLICT DO NOTHING;

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
    
    -- File size will be populated later
    NULL as file_size,
    
    pd.processing_status,
    
    -- Store extracted data from ai_analysis_results (safely)
    CASE 
        WHEN pd.ai_analysis_results IS NOT NULL AND pd.ai_analysis_results != '' THEN
            CASE 
                WHEN pd.ai_analysis_results::text ~ '^{.*}$' THEN pd.ai_analysis_results::jsonb
                ELSE NULL
            END
        ELSE NULL
    END as extracted_data,
    
    pd.results_file_path as analysis_results_path,
    pd.user_id as uploaded_by,
    pd.created_at as upload_date,
    true as is_active
    
FROM pitch_decks pd
JOIN users u ON pd.user_id = u.id
JOIN projects p ON p.company_id = pd.company_id
WHERE pd.company_id IS NOT NULL
ON CONFLICT DO NOTHING;

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
    
    -- For now, set created_by to the document uploader
    doc.uploaded_by as created_by,
    
    CASE r.status
        WHEN 'completed' THEN 'active'
        WHEN 'pending' THEN 'active'
        WHEN 'in_review' THEN 'active'
        ELSE 'active'
    END as status,
    
    jsonb_build_object(
        'migrated_from_review', true,
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
WHERE r.review_data IS NOT NULL
ON CONFLICT DO NOTHING;

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
    
    jsonb_build_object(
        'migrated_from_question', true,
        'answers', COALESCE(
            (SELECT jsonb_agg(
                jsonb_build_object(
                    'answer_text', a.answer_text,
                    'answered_by', a.answered_by,
                    'created_at', a.created_at
                )
            )
            FROM answers a WHERE a.question_id = q.id),
            '[]'::jsonb
        )
    ) as interaction_metadata,
    
    q.created_at,
    q.created_at as updated_at
    
FROM questions q
JOIN reviews r ON q.review_id = r.id
JOIN pitch_decks pd ON r.pitch_deck_id = pd.id
JOIN users u ON pd.user_id = u.id
JOIN projects p ON p.company_id = pd.company_id
JOIN project_documents doc ON doc.project_id = p.id AND doc.file_path = pd.file_path
ON CONFLICT DO NOTHING;