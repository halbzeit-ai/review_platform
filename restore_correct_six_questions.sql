-- Restore the 6 missing questions for Seven-Chapter Review template
-- Mapping production chapter names to development chapter IDs

BEGIN;

-- Solution Approach (chapter 2 in prod) -> Market Analysis (id: 2) - Question 5
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
    2,  -- market_analysis
    'quantified_advantage',
    'Can the startup quantify their advantage?',
    1.0,
    5,
    true,
    'Quantitative metrics demonstrating competitive advantage',
    'Clinical efficacy data, cost savings, or improved health outcomes'
);

-- Product Market Fit (chapter 3 in prod) -> Technology & Product (id: 3) - Question 5
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
    3,  -- technology_product
    'churn_analysis',
    'What is the churn and the reasons for it?',
    1.0,
    5,
    true,
    'Churn metrics with root cause analysis and mitigation strategies',
    'Healthcare-specific retention challenges and solutions'
);

-- Monetization (chapter 4 in prod) -> Clinical Evidence & Regulatory (id: 4) - Questions 5 & 6
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
    4,  -- clinical_regulatory
    'pricing_strategy',
    'How did did the startup design their pricing and why?',
    1.0,
    5,
    true,
    'Pricing strategy with market research and value-based rationale',
    'Healthcare pricing models, reimbursement alignment, and value-based care'
);

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
    4,  -- clinical_regulatory
    'unit_economics',
    'What are the startup''s margins and unit economics?',
    1.0,
    6,
    true,
    'Clear unit economics with margin analysis and scalability',
    'Healthcare-specific cost structure and regulatory compliance costs'
);

-- Financials (chapter 5 in prod) -> Business Model & Commercialization (id: 5) - Question 5
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
    5,  -- business_model
    'funding_requirements',
    'How much funding is the startup looking for and why exactly this amount?',
    1.0,
    5,
    true,
    'Specific funding amount with detailed justification and milestones',
    'Healthcare-specific funding needs for clinical trials, regulatory approval, or market access'
);

-- Organization (chapter 7 in prod) -> Financial Projections & Investment (id: 7) - Question 5
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
    7,  -- financial_investment
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