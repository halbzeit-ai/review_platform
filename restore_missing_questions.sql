-- Restore missing questions (5 & 6) for Seven-Chapter Review template
-- Expected: 6 missing questions (Solution:1, Product Market Fit:1, Monetization:2, Financials:1, Organization:1)
-- Total missing questions to restore: 30

BEGIN;

-- Solution Approach - Question 5
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
    'solution_description_5',
    'What exactly does the startup''s solution look like?',
    1.0,
    5,
    true,
    'Clear, detailed solution description with implementation approach',
    'Clinical mechanism, therapeutic approach, or healthcare delivery method'
);

-- Solution Approach - Question 6
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
    'differentiation_6',
    'What distinguishes it from existing solutions?',
    1.0,
    6,
    true,
    'Clear competitive differentiation with unique value proposition',
    'Clinical advantages, regulatory benefits, or improved patient outcomes'
);

-- Solution Approach - Question 7
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
    'current_solutions_7',
    'How does the customer solve the problem currently?',
    1.0,
    7,
    true,
    'Understanding of current alternatives and their limitations',
    'Current standard of care, existing treatments, or workflow solutions'
);

-- Solution Approach - Question 8
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
    'competitive_landscape_8',
    'Are there competitors and what does their solution & positioning look like?',
    1.0,
    8,
    true,
    'Comprehensive competitive analysis with positioning comparison',
    'Competitive healthcare solutions, regulatory status, and market positioning'
);

-- Solution Approach - Question 9
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
    'quantified_advantage_9',
    'Can the startup quantify their advantage?',
    1.0,
    9,
    true,
    'Quantitative metrics demonstrating competitive advantage',
    'Clinical efficacy data, cost savings, or improved health outcomes'
);

-- Product Market Fit - Question 10
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
    'paying_customers_10',
    'Does the startup have paying customers?',
    1.0,
    10,
    true,
    'Evidence of paying customers with revenue generation',
    'Healthcare providers, patients, or payers actually purchasing the solution'
);

-- Product Market Fit - Question 11
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
    'pilot_customers_11',
    'Does the startup have non-paying but convinced pilot customers?',
    1.0,
    11,
    true,
    'Pilot customers demonstrating product validation and commitment',
    'Healthcare institutions, clinicians, or patients engaged in pilots'
);

-- Product Market Fit - Question 12
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
    'customer_acquisition_12',
    'How did the startup find pilot customers?',
    1.0,
    12,
    true,
    'Clear customer acquisition strategy with repeatable process',
    'Healthcare-specific acquisition channels and relationship building'
);

-- Product Market Fit - Question 13
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
    'customer_satisfaction_13',
    'What do users & payers love about the startup''s solution?',
    1.0,
    13,
    true,
    'Specific customer feedback highlighting value proposition',
    'Clinical outcomes, workflow improvements, or patient satisfaction'
);

-- Product Market Fit - Question 14
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
    'churn_analysis_14',
    'What is the churn and the reasons for it?',
    1.0,
    14,
    true,
    'Churn metrics with root cause analysis and mitigation strategies',
    'Healthcare-specific retention challenges and solutions'
);

-- Monetization - Question 15
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
    'payer_identification_15',
    'Who will pay for it?',
    1.0,
    15,
    true,
    'Clear identification of paying customers and decision makers',
    'Healthcare payers, insurance, providers, or patients as payment sources'
);

-- Monetization - Question 16
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
    'payer_vs_user_16',
    'Are the users paying themselves or someone else?',
    1.0,
    16,
    true,
    'Clear distinction between users and payers with rationale',
    'Healthcare stakeholder payment dynamics and reimbursement models'
);

-- Monetization - Question 17
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
    'decision_making_17',
    'What does the buyer''s decision-making structure look like?',
    1.0,
    17,
    true,
    'Understanding of decision-making process and key stakeholders',
    'Healthcare procurement, clinical committees, or administrative approval processes'
);

-- Monetization - Question 18
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
    'sales_cycle_18',
    'How much time elapses between startup''s initial contact with the customer and payment?',
    1.0,
    18,
    true,
    'Clear sales cycle timeline with key milestones',
    'Healthcare-specific sales cycles including regulatory and compliance considerations'
);

-- Monetization - Question 19
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
    'pricing_strategy_19',
    'How did did the startup design their pricing and why?',
    1.0,
    19,
    true,
    'Pricing strategy with market research and value-based rationale',
    'Healthcare pricing models, reimbursement alignment, and value-based care'
);

-- Monetization - Question 20
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
    'unit_economics_20',
    'What are the startup''s margins and unit economics?',
    1.0,
    20,
    true,
    'Clear unit economics with margin analysis and scalability',
    'Healthcare-specific cost structure and regulatory compliance costs'
);

-- Financials - Question 21
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
    'monthly_burn_21',
    'What is the startup''s current monthly burn?',
    1.0,
    21,
    true,
    'Current burn rate with detailed breakdown',
    'Healthcare-specific operational costs and regulatory compliance expenses'
);

-- Financials - Question 22
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
    'monthly_sales_22',
    'What are the startup''s monthly sales?',
    1.0,
    22,
    true,
    'Monthly revenue with growth trends and predictability',
    'Healthcare revenue recognition and reimbursement timing'
);

-- Financials - Question 23
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
    'financial_fluctuations_23',
    'Are there major fluctuations in revenues and why?',
    1.0,
    23,
    true,
    'Understanding of financial volatility with explanations',
    'Healthcare-specific seasonality, reimbursement cycles, or regulatory impacts'
);

-- Financials - Question 24
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
    'annual_burn_24',
    'How much money did the startup burn last year?',
    1.0,
    24,
    true,
    'Historical burn rate with efficiency analysis',
    'Healthcare development costs, clinical trials, or regulatory expenses'
);

-- Financials - Question 25
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
    'funding_requirements_25',
    'How much funding is the startup looking for and why exactly this amount?',
    1.0,
    25,
    true,
    'Specific funding amount with detailed justification and milestones',
    'Healthcare-specific funding needs for clinical trials, regulatory approval, or market access'
);

-- Use of Funds - Question 26
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
     WHERE chapter_id = 'use_of_funds' 
     AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')),
    'fund_allocation_26',
    'What will the startup do with the money?',
    1.0,
    26,
    true,
    'Detailed fund allocation with specific use cases and timelines',
    'Healthcare-specific investments in clinical development, regulatory processes, or market access'
);

-- Use of Funds - Question 27
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
     WHERE chapter_id = 'use_of_funds' 
     AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')),
    'priority_deficits_27',
    'Is there a ranked list of deficits regarding the startup''s business setup to address?',
    1.0,
    27,
    true,
    'Prioritized list of organizational gaps with investment rationale',
    'Healthcare-specific capabilities like clinical expertise, regulatory affairs, or quality systems'
);

-- Use of Funds - Question 28
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
     WHERE chapter_id = 'use_of_funds' 
     AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')),
    'investment_strategy_28',
    'Can the startup explain its strategy how to invest the funds?',
    1.0,
    28,
    true,
    'Clear investment strategy with risk management and milestone planning',
    'Healthcare development strategy including clinical phases and regulatory pathways'
);

-- Use of Funds - Question 29
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
     WHERE chapter_id = 'use_of_funds' 
     AND analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')),
    'future_state_29',
    'What will the startup look like at the end of this investment period?',
    1.0,
    29,
    true,
    'Clear vision of future state with specific metrics and capabilities',
    'Healthcare milestones including clinical data, regulatory approvals, or market penetration'
);

-- Organization - Question 30
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
    'team_experience_30',
    'Who are the people behind the startup and what experience do they have?',
    1.0,
    30,
    true,
    'Team backgrounds with relevant experience and track record',
    'Healthcare industry experience, clinical expertise, or regulatory knowledge'
);

-- Organization - Question 31
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
    'organizational_maturity_31',
    'How can the startup''s organizational maturity be described and quantified?',
    1.0,
    31,
    true,
    'Organizational structure, processes, and governance maturity',
    'Healthcare-specific organizational requirements like quality systems or clinical governance'
);

-- Organization - Question 32
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
    'team_composition_32',
    'How many people are working in the startup and how are they allocated per unit?',
    1.0,
    32,
    true,
    'Team size and composition with functional distribution',
    'Healthcare-specific roles including clinical, regulatory, and quality assurance'
);

-- Organization - Question 33
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
    'skill_gaps_33',
    'What skills are missing in the startup''s management team?',
    1.0,
    33,
    true,
    'Identified skill gaps with plans for addressing them',
    'Healthcare-specific expertise gaps in clinical development, regulatory affairs, or commercial strategy'
);

-- Organization - Question 34
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
    'urgent_hiring_34',
    'What are the most urgent positions in the startup that need to be filled?',
    1.0,
    34,
    true,
    'Prioritized hiring needs with impact on business objectives',
    'Critical healthcare roles for clinical development, regulatory compliance, or market access'
);

COMMIT;
