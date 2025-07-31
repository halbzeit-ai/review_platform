-- Create the seven-chapter structure for the Standard Seven-Chapter Review template
-- Based on the analysis prompt: 1) Executive Summary, 2) Market Analysis, 3) Technology & Product, 
-- 4) Clinical Evidence & Regulatory, 5) Business Model & Commercialization, 6) Team & Operations, 
-- 7) Financial Projections & Investment

-- Get the template ID for the Seven-Chapter Review
DO $$
DECLARE
    template_id INTEGER;
BEGIN
    -- Find the Seven-Chapter Review template
    SELECT id INTO template_id 
    FROM analysis_templates 
    WHERE name ILIKE '%Standard Seven-Chapter Review%';
    
    IF template_id IS NOT NULL THEN
        -- Insert the 7 chapters
        
        -- Chapter 1: Executive Summary
        INSERT INTO template_chapters (
            template_id, chapter_id, name, description, weight, order_index, 
            is_required, enabled, analysis_template_id
        ) VALUES (
            template_id, 'executive_summary', 'Executive Summary', 
            'Comprehensive overview of the company, product, market opportunity, and key value propositions',
            1.0, 1, TRUE, TRUE, template_id
        );
        
        -- Chapter 2: Market Analysis
        INSERT INTO template_chapters (
            template_id, chapter_id, name, description, weight, order_index,
            is_required, enabled, analysis_template_id
        ) VALUES (
            template_id, 'market_analysis', 'Market Analysis',
            'Analysis of target market size, competitive landscape, and market dynamics',
            1.0, 2, TRUE, TRUE, template_id
        );
        
        -- Chapter 3: Technology & Product
        INSERT INTO template_chapters (
            template_id, chapter_id, name, description, weight, order_index,
            is_required, enabled, analysis_template_id
        ) VALUES (
            template_id, 'technology_product', 'Technology & Product',
            'Evaluation of the technology platform, product features, and technical differentiation',
            1.0, 3, TRUE, TRUE, template_id
        );
        
        -- Chapter 4: Clinical Evidence & Regulatory
        INSERT INTO template_chapters (
            template_id, chapter_id, name, description, weight, order_index,
            is_required, enabled, analysis_template_id
        ) VALUES (
            template_id, 'clinical_regulatory', 'Clinical Evidence & Regulatory',
            'Assessment of clinical validation, regulatory pathway, FDA/CE marking requirements',
            1.0, 4, TRUE, TRUE, template_id
        );
        
        -- Chapter 5: Business Model & Commercialization
        INSERT INTO template_chapters (
            template_id, chapter_id, name, description, weight, order_index,
            is_required, enabled, analysis_template_id
        ) VALUES (
            template_id, 'business_model', 'Business Model & Commercialization',
            'Analysis of revenue model, go-to-market strategy, and commercialization approach',
            1.0, 5, TRUE, TRUE, template_id
        );
        
        -- Chapter 6: Team & Operations
        INSERT INTO template_chapters (
            template_id, chapter_id, name, description, weight, order_index,
            is_required, enabled, analysis_template_id
        ) VALUES (
            template_id, 'team_operations', 'Team & Operations',
            'Evaluation of founding team, key personnel, and operational capabilities',
            1.0, 6, TRUE, TRUE, template_id
        );
        
        -- Chapter 7: Financial Projections & Investment
        INSERT INTO template_chapters (
            template_id, chapter_id, name, description, weight, order_index,
            is_required, enabled, analysis_template_id
        ) VALUES (
            template_id, 'financial_investment', 'Financial Projections & Investment',
            'Analysis of financial projections, funding requirements, and investment opportunity',
            1.0, 7, TRUE, TRUE, template_id
        );
        
        RAISE NOTICE 'Successfully created 7 chapters for template ID: %', template_id;
    ELSE
        RAISE EXCEPTION 'Seven-Chapter Review template not found';
    END IF;
END $$;