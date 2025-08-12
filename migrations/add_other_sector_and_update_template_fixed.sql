-- Migration: Add 'other' healthcare sector and reassign Standard Seven-Chapter Review template
-- This changes the Standard Seven-Chapter Review from being healthcare-specific to being the fallback for non-healthcare startups

-- First, check if 'other' sector already exists
DO $$
BEGIN
    -- Insert the 'other' sector if it doesn't exist
    IF NOT EXISTS (SELECT 1 FROM healthcare_sectors WHERE name = 'other') THEN
        INSERT INTO healthcare_sectors (name, display_name, description, keywords, subcategories, is_active)
        VALUES (
            'other',
            'Other (Non-Healthcare)',
            'For startups that do not fit into any of the defined healthcare categories. This includes general technology, fintech, edtech, and other non-healthcare sectors.',
            '["general", "technology", "non-healthcare", "other", "fintech", "edtech", "saas", "marketplace", "e-commerce"]',
            '["General Technology", "Financial Services", "Education Technology", "E-commerce", "SaaS Platforms", "Other"]',
            true
        );
        RAISE NOTICE 'Added "other" sector';
    ELSE
        RAISE NOTICE '"other" sector already exists';
    END IF;
END $$;

-- Update the Standard Seven-Chapter Review template (template ID 9) to be associated with 'other' sector
UPDATE analysis_templates 
SET healthcare_sector_id = (SELECT id FROM healthcare_sectors WHERE name = 'other')
WHERE id = 9;

-- Verify the change
SELECT 
    at.id,
    at.name as template_name,
    hs.name as sector_name,
    hs.display_name as sector_display_name
FROM analysis_templates at
JOIN healthcare_sectors hs ON at.healthcare_sector_id = hs.id
WHERE at.id = 9;