-- Deprecate healthcare_templates table
-- Rename to indicate it's deprecated and no longer used
-- Content has been migrated to analysis_templates table

-- Rename the table to mark as deprecated
ALTER TABLE healthcare_templates RENAME TO healthcare_templates_deprecated;

-- Add a comment to explain the deprecation
COMMENT ON TABLE healthcare_templates_deprecated IS 'DEPRECATED: This table has been replaced by analysis_templates. Content was migrated on ' || CURRENT_DATE || '. Safe to drop after verification.';

-- Create a view with the old name that redirects to analysis_templates (optional fallback)
-- This ensures any remaining code references will still work
CREATE OR REPLACE VIEW healthcare_templates AS 
SELECT 
    id,
    name as template_name,
    analysis_prompt,
    description,
    healthcare_sector_id,
    is_active,
    is_default,
    created_at,
    modified_at as updated_at
FROM analysis_templates
WHERE analysis_prompt IS NOT NULL;

COMMENT ON VIEW healthcare_templates IS 'DEPRECATED VIEW: Redirects to analysis_templates for backward compatibility. Remove after all code updated.';