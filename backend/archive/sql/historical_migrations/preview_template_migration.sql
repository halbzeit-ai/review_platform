-- Preview: Template Migration - Check what will be changed
-- This script shows what the migration will do WITHOUT making any changes
-- Date: 2025-07-27
-- Description: Preview of template default status migration

-- Display current state
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
    
    RAISE NOTICE '=== CURRENT TEMPLATE STATUS ===';
    RAISE NOTICE 'Current state:';
    RAISE NOTICE '  Default templates: %', default_count;
    RAISE NOTICE '  Regular templates: %', regular_count;
    RAISE NOTICE '  Total active templates: %', total_count;
    RAISE NOTICE '';
END $$;

-- Show all current templates
DO $$
DECLARE 
    template_record RECORD;
BEGIN
    RAISE NOTICE 'DEFAULT TEMPLATES (is_default = TRUE):';
    
    FOR template_record IN 
        SELECT id, name, healthcare_sector_id 
        FROM analysis_templates 
        WHERE is_active = TRUE AND is_default = TRUE
        ORDER BY name
    LOOP
        RAISE NOTICE '  🔒 ID %: % (Sector: %)', template_record.id, template_record.name, template_record.healthcare_sector_id;
    END LOOP;
    
    RAISE NOTICE '';
    RAISE NOTICE 'REGULAR TEMPLATES (is_default = FALSE):';
    
    FOR template_record IN 
        SELECT id, name, healthcare_sector_id 
        FROM analysis_templates 
        WHERE is_active = TRUE AND is_default = FALSE
        ORDER BY name
    LOOP
        RAISE NOTICE '  📝 ID %: % (Sector: %)', template_record.id, template_record.name, template_record.healthcare_sector_id;
    END LOOP;
    
    RAISE NOTICE '';
END $$;

-- Show Standard Seven-Chapter Review status
DO $$
DECLARE 
    template_record RECORD;
    found BOOLEAN := FALSE;
BEGIN
    RAISE NOTICE '=== STANDARD SEVEN-CHAPTER REVIEW STATUS ===';
    
    FOR template_record IN 
        SELECT id, name, is_default, healthcare_sector_id 
        FROM analysis_templates 
        WHERE is_active = TRUE AND LOWER(name) LIKE '%standard seven-chapter review%'
    LOOP
        found := TRUE;
        RAISE NOTICE '🎯 Found: % (ID: %)', template_record.name, template_record.id;
        RAISE NOTICE '   Current status: %', CASE WHEN template_record.is_default THEN 'DEFAULT' ELSE 'REGULAR' END;
        RAISE NOTICE '   Sector: %', template_record.healthcare_sector_id;
    END LOOP;
    
    IF NOT found THEN
        RAISE NOTICE '⚠️  Standard Seven-Chapter Review template not found!';
    END IF;
    
    RAISE NOTICE '';
END $$;

-- Show migration preview
DO $$
DECLARE 
    templates_to_convert INTEGER;
    template_record RECORD;
BEGIN
    SELECT COUNT(*) 
    INTO templates_to_convert
    FROM analysis_templates 
    WHERE is_active = TRUE AND is_default = TRUE;
    
    RAISE NOTICE '=== MIGRATION PREVIEW ===';
    RAISE NOTICE 'Templates that WILL BE CONVERTED from DEFAULT to REGULAR:';
    
    IF templates_to_convert = 0 THEN
        RAISE NOTICE '  ✅ No templates need to be converted (all are already regular)';
    ELSE
        FOR template_record IN 
            SELECT id, name, healthcare_sector_id 
            FROM analysis_templates 
            WHERE is_active = TRUE AND is_default = TRUE
            ORDER BY name
        LOOP
            RAISE NOTICE '  🔄 ID %: % (Sector: %)', template_record.id, template_record.name, template_record.healthcare_sector_id;
        END LOOP;
        
        RAISE NOTICE '';
        RAISE NOTICE 'After migration:';
        RAISE NOTICE '  - % templates will become REGULAR (editable/deletable)', templates_to_convert;
        RAISE NOTICE '  - 0 templates will remain DEFAULT';
        RAISE NOTICE '  - All templates can be edited and deleted by GPs';
        RAISE NOTICE '  - Startup classifier will use fallback logic';
    END IF;
    
    RAISE NOTICE '';
END $$;

-- Show sector coverage
DO $$
DECLARE 
    sector_record RECORD;
BEGIN
    RAISE NOTICE '=== SECTOR TEMPLATE COVERAGE ===';
    RAISE NOTICE 'Templates per healthcare sector:';
    
    FOR sector_record IN 
        SELECT healthcare_sector_id, COUNT(*) as template_count
        FROM analysis_templates 
        WHERE is_active = TRUE
        GROUP BY healthcare_sector_id
        ORDER BY healthcare_sector_id
    LOOP
        RAISE NOTICE '  Sector %: % templates', sector_record.healthcare_sector_id, sector_record.template_count;
    END LOOP;
    
    RAISE NOTICE '';
END $$;

-- Final instructions
DO $$
BEGIN
    RAISE NOTICE '=== NEXT STEPS ===';
    RAISE NOTICE '1. Review the preview above';
    RAISE NOTICE '2. If everything looks correct, run the actual migration:';
    RAISE NOTICE '   python run_migration.py migrations/convert_templates_to_regular.sql';
    RAISE NOTICE '3. Make sure the updated startup classifier is deployed';
    RAISE NOTICE '';
    RAISE NOTICE '⚠️  This preview made NO CHANGES to the database';
END $$;