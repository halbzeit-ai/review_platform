-- Add analysis_prompt field to analysis_templates table
-- This allows storing detailed analysis prompts for each template

ALTER TABLE analysis_templates 
ADD COLUMN analysis_prompt TEXT;

-- Update the Seven-Chapter Review template with the actual prompt from healthcare_templates
UPDATE analysis_templates 
SET analysis_prompt = 'Conduct a comprehensive seven-chapter analysis of this digital therapeutics or mental health startup: 1) Executive Summary, 2) Market Analysis, 3) Technology & Product, 4) Clinical Evidence & Regulatory, 5) Business Model & Commercialization, 6) Team & Operations, 7) Financial Projections & Investment. Focus on therapeutic outcomes, FDA/CE marking requirements, clinical validation, and reimbursement strategies.'
WHERE name = 'Standard Seven-Chapter Review (Digital Therapeutics & Mental Health)';

-- Add basic analysis prompts for other sector templates
UPDATE analysis_templates 
SET analysis_prompt = 'Analyze this healthcare startup pitch deck focusing on market opportunity, technology innovation, business model, competitive advantage, and regulatory considerations. Provide detailed insights into the company''s potential for success in the healthcare market.'
WHERE analysis_prompt IS NULL;