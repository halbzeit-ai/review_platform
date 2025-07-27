-- Verification: Check Classifications Tab Compatibility After Migration
-- This shows how the classifications tab will work after template migration

-- Show current template-to-sector mappings (before migration simulation)
SELECT 
    s.id as sector_id,
    s.display_name as sector_name,
    t.id as template_id,
    t.name as template_name,
    t.is_default,
    ROW_NUMBER() OVER (PARTITION BY s.id ORDER BY t.is_default DESC, t.name) as selection_order
FROM healthcare_sectors s
LEFT JOIN analysis_templates t ON s.id = t.healthcare_sector_id AND t.is_active = TRUE
WHERE s.is_active = TRUE
ORDER BY s.display_name, selection_order;

-- Simulate post-migration state: Show which template would be selected per sector
-- (This simulates what templates.find() would return after migration)
WITH post_migration_simulation AS (
    SELECT 
        s.id as sector_id,
        s.display_name as sector_name,
        t.id as template_id,
        t.name as template_name,
        FALSE as is_default, -- Simulate all templates being regular
        ROW_NUMBER() OVER (PARTITION BY s.id ORDER BY t.name) as selection_order
    FROM healthcare_sectors s
    LEFT JOIN analysis_templates t ON s.id = t.healthcare_sector_id AND t.is_active = TRUE
    WHERE s.is_active = TRUE
)
SELECT 
    sector_id,
    sector_name,
    template_id,
    template_name,
    'SELECTED (first alphabetically)' as status
FROM post_migration_simulation 
WHERE selection_order = 1
ORDER BY sector_name;

-- Show all templates that would appear in the "Single Template" dropdown
-- (with simulated post-migration state)
SELECT 
    t.id,
    t.name,
    s.display_name as sector_name,
    t.is_default as current_default_status,
    FALSE as post_migration_default_status,
    CASE 
        WHEN t.is_default THEN 'Will lose "Default" chip'
        ELSE 'No change (already regular)'
    END as ui_change
FROM analysis_templates t
JOIN healthcare_sectors s ON t.healthcare_sector_id = s.id
WHERE t.is_active = TRUE AND s.is_active = TRUE
ORDER BY s.display_name, t.name;

-- Summary of changes
SELECT 
    'BEFORE MIGRATION' as status,
    COUNT(*) FILTER (WHERE is_default = TRUE) as default_templates,
    COUNT(*) FILTER (WHERE is_default = FALSE) as regular_templates,
    COUNT(*) as total
FROM analysis_templates 
WHERE is_active = TRUE

UNION ALL

SELECT 
    'AFTER MIGRATION' as status,
    0 as default_templates, -- All will be regular
    COUNT(*) as regular_templates,
    COUNT(*) as total
FROM analysis_templates 
WHERE is_active = TRUE;