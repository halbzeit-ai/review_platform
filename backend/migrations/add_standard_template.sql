-- Add Standard Seven-Chapter Template
-- This template reflects the default review structure used in the pitch deck analyzer

-- First, let's create a general "Standard Review" sector if it doesn't exist
-- Using ON CONFLICT to handle if the sector already exists

INSERT INTO healthcare_sectors (name, display_name, description, keywords, subcategories, confidence_threshold, regulatory_requirements, is_active)
VALUES (
    'standard_review',
    'Standard Review',
    'General startup review template suitable for all sectors',
    '["startup", "review", "analysis", "general", "standard"]',
    '["general", "cross-sector", "standard"]',
    0.7,
    '{"requirements": [], "notes": "General template with no specific regulatory requirements"}',
    TRUE
) ON CONFLICT (name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    description = EXCLUDED.description,
    is_active = EXCLUDED.is_active;

-- Get the sector ID (this will work in PostgreSQL)
DO $$
DECLARE
    sector_id INTEGER;
    template_id INTEGER;
    chapter_id INTEGER;
BEGIN
    -- Get or create the standard review sector
    SELECT id INTO sector_id FROM healthcare_sectors WHERE name = 'standard_review';
    
    -- Check if template already exists
    SELECT id INTO template_id FROM analysis_templates 
    WHERE healthcare_sector_id = sector_id AND name = 'Standard Seven-Chapter Review';
    
    -- Only insert if template doesn't exist
    IF template_id IS NULL THEN
        -- Insert the standard template
        INSERT INTO analysis_templates (
            healthcare_sector_id,
            name,
            description,
            template_version,
            specialized_analysis,
            is_active,
            is_default,
            usage_count
        ) VALUES (
            sector_id,
            'Standard Seven-Chapter Review',
            'The standard seven-chapter review template used for comprehensive startup analysis',
            '1.0',
            '["problem_analysis", "solution_approach", "product_market_fit", "monetization", "financials", "use_of_funds", "organization"]',
            TRUE,
            TRUE,
            0
        ) RETURNING id INTO template_id;
        
        RAISE NOTICE 'Created new template with ID: %', template_id;

    -- Chapter 1: Problem Analysis
    INSERT INTO template_chapters (
        template_id, chapter_id, name, description, weight, order_index, is_required, enabled
    ) VALUES (
        template_id, 'problem_analysis', 'Problem Analysis', 
        'Analysis of the problem being addressed by the startup', 
        1.0, 1, TRUE, TRUE
    ) RETURNING id INTO chapter_id;

    INSERT INTO chapter_questions (
        chapter_id, question_id, question_text, weight, order_index, enabled, scoring_criteria, healthcare_focus
    ) VALUES 
    (chapter_id, 'problem_who', 'Who has the problem?', 1.0, 1, TRUE, 
     'Score based on clarity of target audience identification (1-5 scale)', 'general'),
    (chapter_id, 'problem_nature', 'What exactly is the nature of the problem?', 1.0, 2, TRUE,
     'Score based on problem definition clarity and specificity (1-5 scale)', 'general'),
    (chapter_id, 'problem_pain_points', 'What are the pain points?', 1.0, 3, TRUE,
     'Score based on depth of pain point analysis (1-5 scale)', 'general'),
    (chapter_id, 'problem_quantification', 'Can the problem be quantified?', 1.0, 4, TRUE,
     'Score based on data-driven problem validation (1-5 scale)', 'general');

    -- Chapter 2: Solution Approach
    INSERT INTO template_chapters (
        template_id, chapter_id, name, description, weight, order_index, is_required, enabled
    ) VALUES (
        template_id, 'solution_approach', 'Solution Approach', 
        'Analysis of the proposed solution and competitive differentiation', 
        1.0, 2, TRUE, TRUE
    ) RETURNING id INTO chapter_id;

    INSERT INTO chapter_questions (
        chapter_id, question_id, question_text, weight, order_index, enabled, scoring_criteria, healthcare_focus
    ) VALUES 
    (chapter_id, 'solution_description', 'What exactly does your solution look like?', 1.0, 1, TRUE,
     'Score based on solution clarity and innovation (1-5 scale)', 'general'),
    (chapter_id, 'solution_differentiation', 'What distinguishes it from existing solutions?', 1.0, 2, TRUE,
     'Score based on competitive differentiation strength (1-5 scale)', 'general'),
    (chapter_id, 'solution_competitors', 'Are there competitors and what does their solution look like?', 1.0, 3, TRUE,
     'Score based on competitive landscape understanding (1-5 scale)', 'general'),
    (chapter_id, 'solution_advantage', 'Can you quantify your advantage?', 1.0, 4, TRUE,
     'Score based on measurable competitive advantages (1-5 scale)', 'general');

    -- Chapter 3: Product Market Fit
    INSERT INTO template_chapters (
        template_id, chapter_id, name, description, weight, order_index, is_required, enabled
    ) VALUES (
        template_id, 'product_market_fit', 'Product Market Fit', 
        'Customer validation and market adoption analysis', 
        1.0, 3, TRUE, TRUE
    ) RETURNING id INTO chapter_id;

    INSERT INTO chapter_questions (
        chapter_id, question_id, question_text, weight, order_index, enabled, scoring_criteria, healthcare_focus
    ) VALUES 
    (chapter_id, 'pmf_customers', 'Do you have paying customers or convinced pilot customers?', 1.0, 1, TRUE,
     'Score based on customer traction evidence (1-5 scale)', 'general'),
    (chapter_id, 'pmf_discovery', 'How did you find them?', 1.0, 2, TRUE,
     'Score based on customer acquisition strategy (1-5 scale)', 'general'),
    (chapter_id, 'pmf_satisfaction', 'What do users & payers love about your solution?', 1.0, 3, TRUE,
     'Score based on customer satisfaction evidence (1-5 scale)', 'general'),
    (chapter_id, 'pmf_churn', 'What is the churn and the reasons for it?', 1.0, 4, TRUE,
     'Score based on retention metrics and analysis (1-5 scale)', 'general');

    -- Chapter 4: Monetization
    INSERT INTO template_chapters (
        template_id, chapter_id, name, description, weight, order_index, is_required, enabled
    ) VALUES (
        template_id, 'monetization', 'Monetization', 
        'Revenue model and pricing strategy analysis', 
        1.0, 4, TRUE, TRUE
    ) RETURNING id INTO chapter_id;

    INSERT INTO chapter_questions (
        chapter_id, question_id, question_text, weight, order_index, enabled, scoring_criteria, healthcare_focus
    ) VALUES 
    (chapter_id, 'monetization_payer', 'Who will pay for it?', 1.0, 1, TRUE,
     'Score based on payer identification clarity (1-5 scale)', 'general'),
    (chapter_id, 'monetization_decision', 'What does the buyer\'s decision-making structure look like?', 1.0, 2, TRUE,
     'Score based on sales process understanding (1-5 scale)', 'general'),
    (chapter_id, 'monetization_pricing', 'How did you design the pricing and why exactly like this?', 1.0, 3, TRUE,
     'Score based on pricing strategy rationale (1-5 scale)', 'general'),
    (chapter_id, 'monetization_economics', 'What are your margins, what are the unit economics?', 1.0, 4, TRUE,
     'Score based on unit economics clarity (1-5 scale)', 'general');

    -- Chapter 5: Financials
    INSERT INTO template_chapters (
        template_id, chapter_id, name, description, weight, order_index, is_required, enabled
    ) VALUES (
        template_id, 'financials', 'Financials', 
        'Financial metrics and funding requirements analysis', 
        1.0, 5, TRUE, TRUE
    ) RETURNING id INTO chapter_id;

    INSERT INTO chapter_questions (
        chapter_id, question_id, question_text, weight, order_index, enabled, scoring_criteria, healthcare_focus
    ) VALUES 
    (chapter_id, 'financials_burn', 'What is your current monthly burn?', 1.0, 1, TRUE,
     'Score based on financial transparency and planning (1-5 scale)', 'general'),
    (chapter_id, 'financials_sales', 'What are your monthly sales?', 1.0, 2, TRUE,
     'Score based on revenue visibility and growth (1-5 scale)', 'general'),
    (chapter_id, 'financials_fluctuations', 'Are there any major fluctuations? If so, why?', 1.0, 3, TRUE,
     'Score based on financial stability understanding (1-5 scale)', 'general'),
    (chapter_id, 'financials_funding', 'How much funding are you looking for, why exactly this amount?', 1.0, 4, TRUE,
     'Score based on funding requirement justification (1-5 scale)', 'general');

    -- Chapter 6: Use of Funds
    INSERT INTO template_chapters (
        template_id, chapter_id, name, description, weight, order_index, is_required, enabled
    ) VALUES (
        template_id, 'use_of_funds', 'Use of Funds', 
        'Investment strategy and future plans analysis', 
        1.0, 6, TRUE, TRUE
    ) RETURNING id INTO chapter_id;

    INSERT INTO chapter_questions (
        chapter_id, question_id, question_text, weight, order_index, enabled, scoring_criteria, healthcare_focus
    ) VALUES 
    (chapter_id, 'funds_allocation', 'What will you do with the money?', 1.0, 1, TRUE,
     'Score based on fund allocation clarity (1-5 scale)', 'general'),
    (chapter_id, 'funds_priorities', 'Is there a ranked list of deficits that you want to address?', 1.0, 2, TRUE,
     'Score based on strategic prioritization (1-5 scale)', 'general'),
    (chapter_id, 'funds_strategy', 'Can you tell us about your investment strategy?', 1.0, 3, TRUE,
     'Score based on strategic thinking depth (1-5 scale)', 'general'),
    (chapter_id, 'funds_future', 'What will your company look like at the end of this investment period?', 1.0, 4, TRUE,
     'Score based on future vision clarity (1-5 scale)', 'general');

    -- Chapter 7: Organization
    INSERT INTO template_chapters (
        template_id, chapter_id, name, description, weight, order_index, is_required, enabled
    ) VALUES (
        template_id, 'organization', 'Organization', 
        'Team, experience, and organizational maturity analysis', 
        1.0, 7, TRUE, TRUE
    ) RETURNING id INTO chapter_id;

    INSERT INTO chapter_questions (
        chapter_id, question_id, question_text, weight, order_index, enabled, scoring_criteria, healthcare_focus
    ) VALUES 
    (chapter_id, 'org_team', 'Who are you, what experience do you have?', 1.0, 1, TRUE,
     'Score based on team experience relevance (1-5 scale)', 'general'),
    (chapter_id, 'org_maturity', 'How can your organizational maturity be described?', 1.0, 2, TRUE,
     'Score based on organizational development level (1-5 scale)', 'general'),
    (chapter_id, 'org_structure', 'How many people are you / pie chart of people per unit?', 1.0, 3, TRUE,
     'Score based on team structure appropriateness (1-5 scale)', 'general'),
    (chapter_id, 'org_gaps', 'What skills are missing in the management team?', 1.0, 4, TRUE,
     'Score based on skill gap awareness and planning (1-5 scale)', 'general');

    ELSE
        RAISE NOTICE 'Template already exists with ID: %', template_id;
    END IF;

END $$;