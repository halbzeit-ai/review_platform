-- Insert Healthcare Sectors Data
-- Created: 2025-07-16

-- Insert the 8 healthcare sectors
INSERT INTO healthcare_sectors (name, display_name, description, keywords, subcategories, confidence_threshold, regulatory_requirements) VALUES
(
    'digital_therapeutics',
    'Digital Therapeutics & Mental Health',
    'Software-based interventions, mental health platforms, addiction treatment apps, and prescription digital therapeutics that deliver clinical outcomes.',
    '["digital therapeutics", "mental health", "DTx", "prescription app", "behavioral intervention", "cognitive therapy", "addiction treatment", "mindfulness", "depression", "anxiety", "PTSD", "therapeutic app", "clinically validated", "FDA cleared", "digital medicine", "behavioral health", "mental wellness", "cognitive behavioral therapy", "CBT", "digital pill", "therapeutic software"]',
    '["Prescription Digital Therapeutics", "Mental Health Platforms", "Addiction Treatment Apps", "Behavioral Intervention Tools", "Cognitive Training Applications"]',
    0.75,
    '{"fda_required": true, "hipaa_compliance": true, "clinical_validation": true, "evidence_based": true, "patient_outcomes": true}'
),
(
    'healthcare_infrastructure',
    'Healthcare Infrastructure & Workflow',
    'EHR systems, practice management software, revenue cycle management, clinical decision support tools, and administrative automation platforms.',
    '["EHR", "electronic health records", "practice management", "revenue cycle management", "RCM", "clinical decision support", "CDSS", "workflow automation", "administrative automation", "hospital software", "clinic management", "scheduling", "billing", "health information system", "HIS", "practice automation", "medical records", "clinical workflow", "healthcare IT", "health IT"]',
    '["Electronic Health Records", "Practice Management Software", "Revenue Cycle Management", "Clinical Decision Support", "Administrative Automation"]',
    0.70,
    '{"hipaa_compliance": true, "interoperability": true, "security_compliance": true, "clinical_workflow": true}'
),
(
    'telemedicine',
    'Telemedicine & Remote Care',
    'Virtual consultations, remote monitoring platforms, hospital-at-home solutions, and telehealth infrastructure enabling care delivery outside traditional settings.',
    '["telemedicine", "telehealth", "virtual consultations", "remote monitoring", "RPM", "hospital at home", "virtual care", "remote patient monitoring", "teleconsultation", "digital health platform", "virtual visits", "remote care", "virtual health", "telemonitoring", "remote diagnostics", "virtual clinic", "online consultation", "digital care delivery"]',
    '["Virtual Consultation Platforms", "Remote Patient Monitoring", "Hospital-at-Home Solutions", "Telehealth Infrastructure", "Virtual Care Delivery"]',
    0.72,
    '{"telehealth_regulations": true, "cross_state_licensing": true, "hipaa_compliance": true, "quality_standards": true}'
),
(
    'diagnostics_devices',
    'Diagnostics & Medical Devices',
    'Point-of-care testing, wearable health monitors, AI-powered diagnostic tools, medical imaging solutions, and next-generation diagnostic technologies.',
    '["diagnostics", "medical device", "point of care", "POC", "wearable", "health monitor", "AI diagnostics", "medical imaging", "diagnostic tools", "biomarker", "lab on chip", "diagnostic platform", "medical technology", "in vitro diagnostics", "IVD", "medical sensor", "health monitoring", "diagnostic testing", "clinical diagnostics", "pathology", "radiology"]',
    '["Point-of-Care Testing", "Wearable Health Monitors", "AI-Powered Diagnostic Tools", "Medical Imaging Solutions", "Next-Generation Diagnostics"]',
    0.78,
    '{"fda_clearance": true, "ce_marking": true, "clinical_validation": true, "quality_systems": true, "iso_13485": true}'
),
(
    'biotech_pharma',
    'Biotech & Pharmaceuticals',
    'Drug discovery platforms, novel therapeutics, biomarker development, precision medicine tools, and pharmaceutical manufacturing technologies.',
    '["biotech", "pharmaceutical", "drug discovery", "therapeutics", "biomarker", "precision medicine", "pharmaceutical manufacturing", "clinical trials", "molecular diagnostics", "gene therapy", "cell therapy", "biologics", "drug development", "pharmaceutical research", "biomarker discovery", "personalized medicine", "pharmacogenomics", "immunotherapy", "oncology", "rare disease", "orphan drug"]',
    '["Drug Discovery Platforms", "Novel Therapeutics", "Biomarker Development", "Precision Medicine Tools", "Pharmaceutical Manufacturing"]',
    0.80,
    '{"fda_approval": true, "clinical_trials": true, "gmp_compliance": true, "pharmacovigilance": true, "regulatory_strategy": true}'
),
(
    'health_data_ai',
    'Health Data & AI',
    'Healthcare analytics platforms, AI/ML for clinical applications, population health management, predictive modeling, and clinical research technologies.',
    '["healthcare analytics", "health AI", "machine learning", "clinical AI", "population health", "predictive modeling", "clinical research", "health data platform", "medical AI", "healthcare ML", "clinical decision support", "artificial intelligence", "deep learning", "natural language processing", "NLP", "computer vision", "predictive analytics", "real world evidence", "RWE", "clinical data", "health informatics"]',
    '["Healthcare Analytics Platforms", "AI/ML for Clinical Applications", "Population Health Management", "Predictive Modeling", "Clinical Research Technologies"]',
    0.75,
    '{"data_privacy": true, "ai_validation": true, "clinical_evidence": true, "algorithmic_transparency": true, "hipaa_compliance": true}'
),
(
    'consumer_health',
    'Consumer Health & Wellness',
    'Direct-to-consumer health services, fitness and nutrition apps, preventive care platforms, and wellness monitoring solutions for healthy populations.',
    '["consumer health", "wellness", "fitness app", "nutrition", "preventive care", "wellness monitoring", "direct to consumer", "DTC", "health tracking", "lifestyle", "wellness platform", "health optimization", "fitness tracking", "nutrition tracking", "wellness coaching", "preventive health", "health and wellness", "lifestyle medicine", "wellness technology", "consumer wellness"]',
    '["Direct-to-Consumer Health Services", "Fitness and Nutrition Apps", "Preventive Care Platforms", "Wellness Monitoring Solutions", "Health Optimization Tools"]',
    0.65,
    '{"consumer_protection": true, "data_privacy": true, "health_claims": true, "wellness_standards": true}'
),
(
    'healthcare_marketplaces',
    'Healthcare Marketplaces & Access',
    'Provider discovery platforms, healthcare financing solutions, insurance technology, care coordination platforms, and tools improving healthcare accessibility and affordability.',
    '["healthcare marketplace", "provider discovery", "healthcare financing", "insurance technology", "care coordination", "healthcare access", "affordability", "health insurance", "provider network", "healthcare navigation", "health plan", "insurance tech", "insurtech", "healthcare payments", "medical financing", "healthcare affordability", "provider matching", "care navigation", "health benefits", "healthcare commerce"]',
    '["Provider Discovery Platforms", "Healthcare Financing Solutions", "Insurance Technology", "Care Coordination Platforms", "Healthcare Access Tools"]',
    0.70,
    '{"insurance_regulations": true, "healthcare_compliance": true, "financial_regulations": true, "privacy_protection": true}'
);

-- Insert default analysis templates for each sector
INSERT INTO analysis_templates (healthcare_sector_id, name, description, specialized_analysis, is_default) VALUES
(
    1, -- digital_therapeutics
    'Digital Therapeutics Standard Analysis',
    'Comprehensive analysis template for digital therapeutics and mental health startups',
    '["clinical_validation", "regulatory_pathway", "patient_outcomes", "engagement_metrics"]',
    TRUE
),
(
    2, -- healthcare_infrastructure
    'Healthcare Infrastructure Standard Analysis',
    'Analysis template for healthcare IT infrastructure and workflow solutions',
    '["integration_analysis", "workflow_impact", "roi_calculation", "adoption_barriers"]',
    TRUE
),
(
    3, -- telemedicine
    'Telemedicine Standard Analysis',
    'Analysis template for telemedicine and remote care platforms',
    '["care_quality", "patient_satisfaction", "provider_workflow", "technology_infrastructure"]',
    TRUE
),
(
    4, -- diagnostics_devices
    'Diagnostics & Devices Standard Analysis',
    'Analysis template for diagnostic tools and medical devices',
    '["clinical_accuracy", "regulatory_pathway", "manufacturing_quality", "market_access"]',
    TRUE
),
(
    5, -- biotech_pharma
    'Biotech & Pharma Standard Analysis',
    'Analysis template for biotech and pharmaceutical companies',
    '["scientific_hypothesis", "clinical_strategy", "regulatory_timeline", "ip_position"]',
    TRUE
),
(
    6, -- health_data_ai
    'Health Data & AI Standard Analysis',
    'Analysis template for health data and AI companies',
    '["ai_validation", "data_quality", "clinical_integration", "algorithm_performance"]',
    TRUE
),
(
    7, -- consumer_health
    'Consumer Health Standard Analysis',
    'Analysis template for consumer health and wellness companies',
    '["user_engagement", "behavior_change", "monetization_strategy", "market_differentiation"]',
    TRUE
),
(
    8, -- healthcare_marketplaces
    'Healthcare Marketplaces Standard Analysis',
    'Analysis template for healthcare marketplaces and access platforms',
    '["network_effects", "market_dynamics", "regulatory_compliance", "scalability_analysis"]',
    TRUE
);