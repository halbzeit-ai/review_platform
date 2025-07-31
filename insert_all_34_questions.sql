-- Insert all 34 questions for Seven-Chapter Review template
-- Based on production data from job_249_1753945263_results.json

BEGIN;

-- Problem Analysis (4 questions)
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
    8,
    'target_problem',
    'Who has the problem?',
    1.0,
    1,
    true,
    'Clear identification of target audience with specific demographics and characteristics',
    'Understanding the patient population and healthcare stakeholders affected'
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
    8,
    'problem_nature',
    'What exactly is the nature of the problem?',
    1.0,
    2,
    true,
    'Detailed problem description with root cause analysis',
    'Medical or healthcare-specific problem definition with clinical significance'
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
    8,
    'pain_points',
    'What are the pain points?',
    1.0,
    3,
    true,
    'Specific pain points with impact assessment',
    'Clinical pain points affecting patient outcomes or healthcare delivery'
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
    8,
    'problem_quantification',
    'Can the problem be quantified?',
    1.0,
    4,
    true,
    'Quantitative data supporting problem scope and impact',
    'Clinical metrics, patient numbers, or healthcare cost implications'
);

-- Solution Approach (5 questions)
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
    9,
    'solution_description',
    'What exactly does the startup''s solution look like?',
    1.0,
    1,
    true,
    'Clear, detailed solution description with implementation approach',
    'Clinical mechanism, therapeutic approach, or healthcare delivery method'
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
    9,
    'differentiation',
    'What distinguishes it from existing solutions?',
    1.0,
    2,
    true,
    'Clear competitive differentiation with unique value proposition',
    'Clinical advantages, regulatory benefits, or improved patient outcomes'
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
    9,
    'current_solutions',
    'How does the customer solve the problem currently?',
    1.0,
    3,
    true,
    'Understanding of current alternatives and their limitations',
    'Current standard of care, existing treatments, or workflow solutions'
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
    9,
    'competitive_landscape',
    'Are there competitors and what does their solution & positioning look like?',
    1.0,
    4,
    true,
    'Comprehensive competitive analysis with positioning comparison',
    'Competitive healthcare solutions, regulatory status, and market positioning'
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
    9,
    'quantified_advantage',
    'Can the startup quantify their advantage?',
    1.0,
    5,
    true,
    'Quantitative metrics demonstrating competitive advantage',
    'Clinical efficacy data, cost savings, or improved health outcomes'
);

-- Product Market Fit (5 questions)
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
    10,
    'paying_customers',
    'Does the startup have paying customers?',
    1.0,
    1,
    true,
    'Evidence of paying customers with revenue generation',
    'Healthcare providers, patients, or payers actually purchasing the solution'
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
    10,
    'pilot_customers',
    'Does the startup have non-paying but convinced pilot customers?',
    1.0,
    2,
    true,
    'Pilot customers demonstrating product validation and commitment',
    'Healthcare institutions, clinicians, or patients engaged in pilots'
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
    10,
    'customer_acquisition',
    'How did the startup find pilot customers?',
    1.0,
    3,
    true,
    'Clear customer acquisition strategy with repeatable process',
    'Healthcare-specific acquisition channels and relationship building'
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
    10,
    'customer_satisfaction',
    'What do users & payers love about the startup''s solution?',
    1.0,
    4,
    true,
    'Specific customer feedback highlighting value proposition',
    'Clinical outcomes, workflow improvements, or patient satisfaction'
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
    10,
    'churn_analysis',
    'What is the churn and the reasons for it?',
    1.0,
    5,
    true,
    'Churn metrics with root cause analysis and mitigation strategies',
    'Healthcare-specific retention challenges and solutions'
);

-- Monetization (6 questions)
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
    11,
    'payer_identification',
    'Who will pay for it?',
    1.0,
    1,
    true,
    'Clear identification of paying customers and decision makers',
    'Healthcare payers, insurance, providers, or patients as payment sources'
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
    11,
    'payer_vs_user',
    'Are the users paying themselves or someone else?',
    1.0,
    2,
    true,
    'Clear distinction between users and payers with rationale',
    'Healthcare stakeholder payment dynamics and reimbursement models'
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
    11,
    'decision_making',
    'What does the buyer''s decision-making structure look like?',
    1.0,
    3,
    true,
    'Understanding of decision-making process and key stakeholders',
    'Healthcare procurement, clinical committees, or administrative approval processes'
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
    11,
    'sales_cycle',
    'How much time elapses between startup''s initial contact with the customer and payment?',
    1.0,
    4,
    true,
    'Clear sales cycle timeline with key milestones',
    'Healthcare-specific sales cycles including regulatory and compliance considerations'
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
    11,
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
    11,
    'unit_economics',
    'What are the startup''s margins and unit economics?',
    1.0,
    6,
    true,
    'Clear unit economics with margin analysis and scalability',
    'Healthcare-specific cost structure and regulatory compliance costs'
);

-- Financials (5 questions)
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
    12,
    'monthly_burn',
    'What is the startup''s current monthly burn?',
    1.0,
    1,
    true,
    'Current burn rate with detailed breakdown',
    'Healthcare-specific operational costs and regulatory compliance expenses'
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
    12,
    'monthly_sales',
    'What are the startup''s monthly sales?',
    1.0,
    2,
    true,
    'Monthly revenue with growth trends and predictability',
    'Healthcare revenue recognition and reimbursement timing'
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
    12,
    'financial_fluctuations',
    'Are there major fluctuations in revenues and why?',
    1.0,
    3,
    true,
    'Understanding of financial volatility with explanations',
    'Healthcare-specific seasonality, reimbursement cycles, or regulatory impacts'
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
    12,
    'annual_burn',
    'How much money did the startup burn last year?',
    1.0,
    4,
    true,
    'Historical burn rate with efficiency analysis',
    'Healthcare development costs, clinical trials, or regulatory expenses'
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
    12,
    'funding_requirements',
    'How much funding is the startup looking for and why exactly this amount?',
    1.0,
    5,
    true,
    'Specific funding amount with detailed justification and milestones',
    'Healthcare-specific funding needs for clinical trials, regulatory approval, or market access'
);

-- Use of Funds (4 questions)
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
    13,
    'fund_allocation',
    'What will the startup do with the money?',
    1.0,
    1,
    true,
    'Detailed fund allocation with specific use cases and timelines',
    'Healthcare-specific investments in clinical development, regulatory processes, or market access'
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
    13,
    'priority_deficits',
    'Is there a ranked list of deficits regarding the startup''s business setup to address?',
    1.0,
    2,
    true,
    'Prioritized list of organizational gaps with investment rationale',
    'Healthcare-specific capabilities like clinical expertise, regulatory affairs, or quality systems'
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
    13,
    'investment_strategy',
    'Can the startup explain its strategy how to invest the funds?',
    1.0,
    3,
    true,
    'Clear investment strategy with risk management and milestone planning',
    'Healthcare development strategy including clinical phases and regulatory pathways'
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
    13,
    'future_state',
    'What will the startup look like at the end of this investment period?',
    1.0,
    4,
    true,
    'Clear vision of future state with specific metrics and capabilities',
    'Healthcare milestones including clinical data, regulatory approvals, or market penetration'
);

-- Organization (5 questions)
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
    14,
    'team_experience',
    'Who are the people behind the startup and what experience do they have?',
    1.0,
    1,
    true,
    'Team backgrounds with relevant experience and track record',
    'Healthcare industry experience, clinical expertise, or regulatory knowledge'
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
    14,
    'organizational_maturity',
    'How can the startup''s organizational maturity be described and quantified?',
    1.0,
    2,
    true,
    'Organizational structure, processes, and governance maturity',
    'Healthcare-specific organizational requirements like quality systems or clinical governance'
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
    14,
    'team_composition',
    'How many people are working in the startup and how are they allocated per unit?',
    1.0,
    3,
    true,
    'Team size and composition with functional distribution',
    'Healthcare-specific roles including clinical, regulatory, and quality assurance'
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
    14,
    'skill_gaps',
    'What skills are missing in the startup''s management team?',
    1.0,
    4,
    true,
    'Identified skill gaps with plans for addressing them',
    'Healthcare-specific expertise gaps in clinical development, regulatory affairs, or commercial strategy'
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
    14,
    'urgent_hiring',
    'What are the most urgent positions in the startup that need to be filled?',
    1.0,
    5,
    true,
    'Prioritized hiring needs with impact on business objectives',
    'Critical healthcare roles for clinical development, regulatory compliance, or market access'
);

COMMIT;

-- Verify all questions were inserted
SELECT 
    tc.name as chapter,
    tc.order_index,
    COUNT(cq.id) as question_count,
    array_agg(cq.order_index ORDER BY cq.order_index) as question_indices
FROM template_chapters tc
LEFT JOIN chapter_questions cq ON cq.chapter_id = tc.id
WHERE tc.analysis_template_id = (SELECT id FROM analysis_templates WHERE name ILIKE '%Standard Seven-Chapter Review%')
GROUP BY tc.name, tc.order_index
ORDER BY tc.order_index;