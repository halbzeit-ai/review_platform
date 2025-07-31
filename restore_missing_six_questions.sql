-- Restore the 6 missing questions for Seven-Chapter Review template
-- These are questions with order_index 5 and 6 that are missing from the database
-- Based on actual production data from job_249_1753945263_results.json

BEGIN;

-- Solution Approach - Question 5 (ID: 9)
INSERT INTO chapter_questions (
    chapter_id,
    question_id,
    question_text,
    weight,
    order_index,
    enabled,
    scoring_criteria,
    healthcare_focus
) VALUES (
    (SELECT id FROM template_chapters 
     WHERE chapter_id = 'solution_approach' 
     AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')),
    'quantified_advantage',
    'Can the startup quantify their advantage?',
    1.0,
    5,
    true,
    'Quantitative metrics demonstrating competitive advantage',
    'Clinical efficacy data, cost savings, or improved health outcomes'
);

-- Product Market Fit - Question 5 (ID: 14)
INSERT INTO chapter_questions (
    chapter_id,
    question_id,
    question_text,
    weight,
    order_index,
    enabled,
    scoring_criteria,
    healthcare_focus
) VALUES (
    (SELECT id FROM template_chapters 
     WHERE chapter_id = 'product_market_fit' 
     AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')),
    'churn_analysis',
    'What is the churn and the reasons for it?',
    1.0,
    5,
    true,
    'Churn metrics with root cause analysis and mitigation strategies',
    'Healthcare-specific retention challenges and solutions'
);

-- Monetization - Question 5 (ID: 19)
INSERT INTO chapter_questions (
    chapter_id,
    question_id,
    question_text,
    weight,
    order_index,
    enabled,
    scoring_criteria,
    healthcare_focus
) VALUES (
    (SELECT id FROM template_chapters 
     WHERE chapter_id = 'monetization' 
     AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')),
    'pricing_strategy',
    'How did did the startup design their pricing and why?',
    1.0,
    5,
    true,
    'Pricing strategy with market research and value-based rationale',
    'Healthcare pricing models, reimbursement alignment, and value-based care'
);

-- Monetization - Question 6 (ID: 20)
INSERT INTO chapter_questions (
    chapter_id,
    question_id,
    question_text,
    weight,
    order_index,
    enabled,
    scoring_criteria,
    healthcare_focus
) VALUES (
    (SELECT id FROM template_chapters 
     WHERE chapter_id = 'monetization' 
     AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')),
    'unit_economics',
    'What are the startup''s margins and unit economics?',
    1.0,
    6,
    true,
    'Clear unit economics with margin analysis and scalability',
    'Healthcare-specific cost structure and regulatory compliance costs'
);

-- Financials - Question 5 (ID: 25)
INSERT INTO chapter_questions (
    chapter_id,
    question_id,
    question_text,
    weight,
    order_index,
    enabled,
    scoring_criteria,
    healthcare_focus
) VALUES (
    (SELECT id FROM template_chapters 
     WHERE chapter_id = 'financials' 
     AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')),
    'funding_requirements',
    'How much funding is the startup looking for and why exactly this amount?',
    1.0,
    5,
    true,
    'Specific funding amount with detailed justification and milestones',
    'Healthcare-specific funding needs for clinical trials, regulatory approval, or market access'
);

-- Organization - Question 5 (ID: 34)
INSERT INTO chapter_questions (
    chapter_id,
    question_id,
    question_text,
    weight,
    order_index,
    enabled,
    scoring_criteria,
    healthcare_focus
) VALUES (
    (SELECT id FROM template_chapters 
     WHERE chapter_id = 'organization' 
     AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')),
    'urgent_hiring',
    'What are the most urgent positions in the startup that need to be filled?',
    1.0,
    5,
    true,
    'Prioritized hiring needs with impact on business objectives',
    'Critical healthcare roles for clinical development, regulatory compliance, or market access'
);

COMMIT;

-- Verify the restoration
SELECT tc.name as chapter, COUNT(cq.id) as question_count
FROM template_chapters tc
LEFT JOIN chapter_questions cq ON cq.chapter_id = tc.id
WHERE tc.analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')
GROUP BY tc.name, tc.order_index
ORDER BY tc.order_index;