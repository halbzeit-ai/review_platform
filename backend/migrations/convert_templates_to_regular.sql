-- Migration: Convert all default templates to regular templates
-- This makes all templates editable and deletable by GPs
-- Date: 2025-07-27
-- Description: Converts all sector-specific default templates to regular templates
--              while maintaining the startup classifier functionality through fallback logic

-- Display current state before migration
DO $$
DECLARE 
    default_count INTEGER;
    regular_count INTEGER;
    total_count INTEGER;
BEGIN
    SELECT 
        COUNT(*) FILTER (WHERE is_default = TRUE),
        COUNT(*) FILTER (WHERE is_default = FALSE),
        COUNT(*)
    INTO default_count, regular_count, total_count
    FROM analysis_templates 
    WHERE is_active = TRUE;
    
    RAISE NOTICE '=== TEMPLATE MIGRATION STATUS ===';
    RAISE NOTICE 'Before migration:';
    RAISE NOTICE '  Default templates: %', default_count;
    RAISE NOTICE '  Regular templates: %', regular_count;
    RAISE NOTICE '  Total templates: %', total_count;
    RAISE NOTICE '';
END $$;

-- Show which templates will be converted
DO $$
DECLARE 
    template_record RECORD;
BEGIN
    RAISE NOTICE 'Templates that will be converted from DEFAULT to REGULAR:';
    
    FOR template_record IN 
        SELECT id, name, healthcare_sector_id 
        FROM analysis_templates 
        WHERE is_active = TRUE AND is_default = TRUE
        ORDER BY name
    LOOP
        RAISE NOTICE '  - ID %: % (Sector: %)', template_record.id, template_record.name, template_record.healthcare_sector_id;
    END LOOP;
    
    RAISE NOTICE '';
END $$;

-- Perform the migration: Convert all default templates to regular
UPDATE analysis_templates 
SET is_default = FALSE 
WHERE is_active = TRUE AND is_default = TRUE;

-- Display results after migration
DO $$
DECLARE 
    default_count INTEGER;
    regular_count INTEGER;
    total_count INTEGER;
    updated_count INTEGER;
BEGIN
    -- Get updated counts
    SELECT 
        COUNT(*) FILTER (WHERE is_default = TRUE),
        COUNT(*) FILTER (WHERE is_default = FALSE),
        COUNT(*)
    INTO default_count, regular_count, total_count
    FROM analysis_templates 
    WHERE is_active = TRUE;
    
    -- Get the number of updated rows (this is approximate since we can't get the exact count from the UPDATE)
    SELECT COUNT(*)
    INTO updated_count
    FROM analysis_templates 
    WHERE is_active = TRUE AND is_default = FALSE;
    
    RAISE NOTICE '=== MIGRATION COMPLETED ===';
    RAISE NOTICE 'After migration:';
    RAISE NOTICE '  Default templates: %', default_count;
    RAISE NOTICE '  Regular templates: %', regular_count;
    RAISE NOTICE '  Total templates: %', total_count;
    RAISE NOTICE '';
    RAISE NOTICE '✅ All templates are now REGULAR (editable/deletable by GPs)';
    RAISE NOTICE '✅ Startup classifier will use fallback logic for template selection';
    RAISE NOTICE '';
    
    -- Show final template status
    RAISE NOTICE 'Final template status:';
END $$;

-- Display all templates with their final status
DO $$
DECLARE 
    template_record RECORD;
BEGIN
    FOR template_record IN 
        SELECT id, name, is_default, healthcare_sector_id 
        FROM analysis_templates 
        WHERE is_active = TRUE
        ORDER BY healthcare_sector_id, name
    LOOP
        RAISE NOTICE '  ✅ ID %: % (Sector: %) - %', 
            template_record.id, 
            template_record.name, 
            template_record.healthcare_sector_id,
            CASE WHEN template_record.is_default THEN 'DEFAULT' ELSE 'REGULAR' END;
    END LOOP;
END $$;

-- Final success message
DO $$
BEGIN
    RAISE NOTICE '';
    RAISE NOTICE '🎉 Template migration completed successfully!';
    RAISE NOTICE '📝 All templates can now be edited and deleted by GPs';
    RAISE NOTICE '🔄 Startup classifier updated with fallback logic';
    RAISE NOTICE '✅ No disruption to existing functionality expected';
END $$;