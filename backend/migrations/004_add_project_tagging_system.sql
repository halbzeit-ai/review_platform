-- Add tagging system for projects to handle dojo/test data
-- This allows filtering real vs test/experimental data

-- Step 1: Add tags field to projects table
ALTER TABLE projects ADD COLUMN IF NOT EXISTS tags JSONB DEFAULT '[]'::jsonb;

-- Step 2: Add is_test flag for easy filtering
ALTER TABLE projects ADD COLUMN IF NOT EXISTS is_test BOOLEAN DEFAULT FALSE;

-- Step 3: Tag all existing dojo projects as test data
UPDATE projects 
SET 
    tags = '["dojo", "internal", "testing"]'::jsonb,
    is_test = TRUE
WHERE company_id = 'dojo';

-- Step 4: Ensure real company projects are marked as non-test
UPDATE projects 
SET 
    tags = '["production"]'::jsonb,
    is_test = FALSE
WHERE company_id != 'dojo' AND is_test IS NULL;

-- Step 5: Create index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_projects_is_test ON projects(is_test);
CREATE INDEX IF NOT EXISTS idx_projects_tags_gin ON projects USING GIN(tags);

-- Step 6: Add metadata to distinguish data sources
UPDATE projects 
SET project_metadata = project_metadata || jsonb_build_object(
    'data_source_type', CASE 
        WHEN company_id = 'dojo' THEN 'internal_testing'
        ELSE 'production'
    END,
    'tagged_at', CURRENT_TIMESTAMP
)
WHERE project_metadata IS NOT NULL;

-- Step 7: Create a view for production-only projects
CREATE OR REPLACE VIEW production_projects AS
SELECT * FROM projects 
WHERE is_test = FALSE OR is_test IS NULL;

-- Step 8: Create a view for test/dojo projects  
CREATE OR REPLACE VIEW test_projects AS
SELECT * FROM projects 
WHERE is_test = TRUE;

-- Verification query
SELECT 
    CASE 
        WHEN is_test THEN 'Test/Dojo Projects'
        ELSE 'Production Projects'
    END as project_type,
    COUNT(*) as count,
    array_agg(DISTINCT company_id) as company_ids
FROM projects
GROUP BY is_test
ORDER BY is_test;