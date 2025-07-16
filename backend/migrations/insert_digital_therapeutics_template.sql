-- Digital Therapeutics Template - Detailed Example
-- Created: 2025-07-16

-- Insert chapters for Digital Therapeutics template
INSERT INTO template_chapters (template_id, chapter_id, name, description, weight, order_index, is_required, chapter_prompt_template, scoring_prompt_template) VALUES
(
    1, -- Digital Therapeutics template
    'clinical_problem',
    'Clinical Problem & Medical Need',
    'Analysis of the medical condition, patient population, and unmet clinical need being addressed',
    1.8,
    1,
    TRUE,
    'Analyze the clinical problem and medical need described in this pitch deck. Focus on the medical condition, patient population, clinical significance, and unmet need.',
    'Rate how well the pitch deck addresses the clinical problem and medical need. Consider clinical significance, patient population definition, and unmet need validation. Score 0-7 where 7 represents exceptional clinical problem definition with strong evidence of unmet need.'
),
(
    1,
    'therapeutic_approach',
    'Therapeutic Approach & Mechanism',
    'Analysis of the digital therapeutic intervention, clinical mechanism, and therapeutic rationale',
    2.0,
    2,
    TRUE,
    'Analyze the therapeutic approach and mechanism of action described in this pitch deck. Focus on the digital intervention, clinical mechanism, therapeutic rationale, and expected clinical outcomes.',
    'Rate how well the pitch deck describes the therapeutic approach and mechanism. Consider clarity of intervention, clinical rationale, mechanism of action, and expected outcomes. Score 0-7 where 7 represents clear, evidence-based therapeutic approach with strong clinical rationale.'
),
(
    1,
    'clinical_evidence',
    'Clinical Evidence & Validation',
    'Analysis of clinical studies, efficacy data, safety profile, and regulatory evidence',
    2.2,
    3,
    TRUE,
    'Analyze the clinical evidence and validation described in this pitch deck. Focus on clinical studies, efficacy data, safety profile, regulatory status, and evidence quality.',
    'Rate the quality and strength of clinical evidence presented. Consider study design, sample size, clinical endpoints, statistical significance, and regulatory validation. Score 0-7 where 7 represents robust clinical evidence with regulatory validation.'
),
(
    1,
    'regulatory_pathway',
    'Regulatory Strategy & Pathway',
    'Analysis of FDA/regulatory pathway, classification, timeline, and regulatory risks',
    1.9,
    4,
    TRUE,
    'Analyze the regulatory strategy and pathway described in this pitch deck. Focus on FDA classification, regulatory pathway, timeline, regulatory risks, and compliance strategy.',
    'Rate how well the pitch deck addresses regulatory strategy and pathway. Consider FDA classification understanding, regulatory timeline realism, risk assessment, and compliance planning. Score 0-7 where 7 represents comprehensive regulatory strategy with clear pathway and risk mitigation.'
),
(
    1,
    'patient_engagement',
    'Patient Engagement & Outcomes',
    'Analysis of patient engagement strategy, user experience, adherence, and clinical outcomes',
    1.7,
    5,
    TRUE,
    'Analyze the patient engagement strategy and outcomes described in this pitch deck. Focus on user experience, patient adherence, engagement metrics, and clinical outcomes.',
    'Rate how well the pitch deck addresses patient engagement and outcomes. Consider user experience design, engagement strategy, adherence metrics, and clinical outcome measurement. Score 0-7 where 7 represents excellent patient engagement with proven clinical outcomes.'
),
(
    1,
    'healthcare_integration',
    'Healthcare Integration & Workflow',
    'Analysis of integration with healthcare systems, provider workflow, and clinical adoption',
    1.6,
    6,
    TRUE,
    'Analyze the healthcare integration and workflow described in this pitch deck. Focus on EHR integration, provider workflow, clinical adoption, and healthcare system fit.',
    'Rate how well the pitch deck addresses healthcare integration and workflow. Consider EHR integration, provider adoption, workflow efficiency, and system compatibility. Score 0-7 where 7 represents seamless healthcare integration with strong provider adoption.'
),
(
    1,
    'reimbursement_strategy',
    'Reimbursement & Market Access',
    'Analysis of reimbursement strategy, payer engagement, health economics, and market access',
    1.8,
    7,
    TRUE,
    'Analyze the reimbursement strategy and market access described in this pitch deck. Focus on payer strategy, health economics, reimbursement pathway, and market access plan.',
    'Rate how well the pitch deck addresses reimbursement and market access. Consider payer engagement, health economics data, reimbursement strategy, and market access planning. Score 0-7 where 7 represents comprehensive reimbursement strategy with strong health economics.'
);

-- Insert questions for Clinical Problem & Medical Need chapter
INSERT INTO chapter_questions (chapter_id, question_id, question_text, weight, order_index, scoring_criteria, healthcare_focus) VALUES
(
    1, -- clinical_problem chapter
    'medical_condition',
    'What specific medical condition or clinical indication is being addressed?',
    2.0,
    1,
    'Clear identification of specific medical condition with clinical definition, prevalence data, and disease burden',
    'Medical condition specificity is crucial for regulatory approval, clinical trial design, and market positioning'
),
(
    1,
    'patient_population',
    'Who is the target patient population and how is it defined?',
    1.8,
    2,
    'Well-defined patient population with demographics, clinical characteristics, and inclusion/exclusion criteria',
    'Patient population definition drives clinical trial design, regulatory pathway, and commercial strategy'
),
(
    1,
    'unmet_need',
    'What is the unmet clinical need and current treatment gaps?',
    2.2,
    3,
    'Clear articulation of unmet need with evidence of treatment gaps, limitations of current therapies, and clinical impact',
    'Unmet clinical need justifies the therapeutic intervention and supports regulatory and payer value proposition'
),
(
    1,
    'clinical_significance',
    'What is the clinical significance and impact on patient outcomes?',
    1.9,
    4,
    'Demonstration of clinical significance with patient outcome impact, quality of life measures, and clinical endpoints',
    'Clinical significance drives regulatory approval criteria and reimbursement decisions'
),
(
    1,
    'disease_burden',
    'What is the disease burden and epidemiological data?',
    1.5,
    5,
    'Comprehensive disease burden analysis with epidemiological data, healthcare utilization, and economic impact',
    'Disease burden data supports market opportunity, health economics, and policy impact arguments'
);

-- Insert questions for Therapeutic Approach & Mechanism chapter
INSERT INTO chapter_questions (chapter_id, question_id, question_text, weight, order_index, scoring_criteria, healthcare_focus) VALUES
(
    2, -- therapeutic_approach chapter
    'digital_intervention',
    'What is the specific digital therapeutic intervention and how does it work?',
    2.2,
    1,
    'Clear description of digital intervention with mechanism of action, therapeutic components, and clinical rationale',
    'Digital intervention clarity is essential for regulatory classification, clinical validation, and provider adoption'
),
(
    2,
    'clinical_mechanism',
    'What is the clinical mechanism of action and therapeutic rationale?',
    2.0,
    2,
    'Well-articulated clinical mechanism with biological/psychological rationale, pathway analysis, and therapeutic hypothesis',
    'Clinical mechanism supports regulatory review, clinical trial design, and scientific credibility'
),
(
    2,
    'therapeutic_modality',
    'What therapeutic modality is used and what is the clinical approach?',
    1.8,
    3,
    'Clear therapeutic modality with evidence-based approach, clinical protocols, and treatment algorithms',
    'Therapeutic modality determines regulatory pathway, clinical validation requirements, and reimbursement strategy'
),
(
    2,
    'differentiation',
    'How does this approach differ from existing treatments and interventions?',
    1.9,
    4,
    'Clear differentiation with competitive analysis, clinical advantages, and unique therapeutic benefits',
    'Differentiation supports regulatory approval, clinical adoption, and commercial positioning'
),
(
    2,
    'clinical_endpoints',
    'What are the primary and secondary clinical endpoints?',
    1.7,
    5,
    'Well-defined clinical endpoints with primary/secondary measures, clinical significance, and regulatory alignment',
    'Clinical endpoints drive clinical trial design, regulatory approval, and reimbursement decisions'
);

-- Insert questions for Clinical Evidence & Validation chapter
INSERT INTO chapter_questions (chapter_id, question_id, question_text, weight, order_index, scoring_criteria, healthcare_focus) VALUES
(
    3, -- clinical_evidence chapter
    'clinical_studies',
    'What clinical studies have been conducted and what are the results?',
    2.5,
    1,
    'Comprehensive clinical studies with appropriate design, sample size, statistical analysis, and clinically meaningful results',
    'Clinical studies are the foundation for regulatory approval, clinical adoption, and reimbursement decisions'
),
(
    3,
    'efficacy_data',
    'What efficacy data exists and how strong is the clinical evidence?',
    2.3,
    2,
    'Robust efficacy data with statistical significance, clinical significance, and reproducible results',
    'Efficacy data drives regulatory approval, clinical guidelines, and payer coverage decisions'
),
(
    3,
    'safety_profile',
    'What is the safety profile and adverse event data?',
    2.0,
    3,
    'Comprehensive safety profile with adverse event monitoring, risk assessment, and safety management plan',
    'Safety profile is critical for regulatory approval, clinical adoption, and risk management'
),
(
    3,
    'regulatory_status',
    'What is the current regulatory status and FDA interactions?',
    2.2,
    4,
    'Clear regulatory status with FDA pathway, pre-submission meetings, regulatory feedback, and approval timeline',
    'Regulatory status determines market access timeline, investment risk, and commercial viability'
),
(
    3,
    'evidence_quality',
    'What is the quality and strength of the overall evidence package?',
    1.8,
    5,
    'High-quality evidence with peer-reviewed publications, regulatory alignment, and clinical validation',
    'Evidence quality determines regulatory success, clinical adoption, and market credibility'
);

-- Continue with remaining chapters and questions...
-- (This would continue for all 7 chapters with their respective questions)

-- Insert questions for Regulatory Strategy & Pathway chapter
INSERT INTO chapter_questions (chapter_id, question_id, question_text, weight, order_index, scoring_criteria, healthcare_focus) VALUES
(
    4, -- regulatory_pathway chapter
    'fda_classification',
    'What is the FDA classification and regulatory pathway?',
    2.3,
    1,
    'Clear FDA classification with appropriate regulatory pathway, device classification, and regulatory strategy',
    'FDA classification determines regulatory requirements, approval timeline, and commercial pathway'
),
(
    4,
    'regulatory_timeline',
    'What is the regulatory timeline and key milestones?',
    2.0,
    2,
    'Realistic regulatory timeline with key milestones, regulatory meetings, and approval projections',
    'Regulatory timeline drives investment planning, commercial strategy, and market access timing'
),
(
    4,
    'regulatory_risks',
    'What are the key regulatory risks and mitigation strategies?',
    1.9,
    3,
    'Comprehensive risk assessment with regulatory risks, mitigation strategies, and contingency planning',
    'Regulatory risk management is critical for investment decisions and commercial success'
),
(
    4,
    'compliance_strategy',
    'What is the regulatory compliance strategy and quality systems?',
    1.7,
    4,
    'Robust compliance strategy with quality systems, regulatory infrastructure, and compliance monitoring',
    'Compliance strategy ensures regulatory success and sustainable commercial operations'
),
(
    4,
    'international_strategy',
    'What is the international regulatory strategy and global pathway?',
    1.5,
    5,
    'Clear international strategy with global regulatory pathway, regional considerations, and market access plan',
    'International strategy expands market opportunity and provides regulatory pathway diversification'
);