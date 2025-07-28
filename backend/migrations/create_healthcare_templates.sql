-- Create healthcare_templates table for template processing
CREATE TABLE IF NOT EXISTS healthcare_templates (
    id SERIAL PRIMARY KEY,
    template_name VARCHAR(255) NOT NULL,
    analysis_prompt TEXT NOT NULL,
    description TEXT,
    healthcare_sector_id INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert a default "Standard Analysis" template
INSERT INTO healthcare_templates (template_name, analysis_prompt, description, is_default)
VALUES (
    'Standard Analysis',
    'Analyze this healthcare startup pitch deck focusing on market opportunity, technology innovation, business model, competitive advantage, and regulatory considerations. Provide detailed insights into the company''s potential for success in the healthcare market.',
    'Standard healthcare startup analysis template covering key areas: market, technology, business model, competition, and regulatory aspects.',
    TRUE
) ON CONFLICT DO NOTHING;

-- Insert a "Standard Seven-Chapter Review" template
INSERT INTO healthcare_templates (template_name, analysis_prompt, description, is_default)
VALUES (
    'Standard Seven-Chapter Review (Digital Therapeutics & Mental Health)',
    'Conduct a comprehensive seven-chapter analysis of this digital therapeutics or mental health startup: 1) Executive Summary, 2) Market Analysis, 3) Technology & Product, 4) Clinical Evidence & Regulatory, 5) Business Model & Commercialization, 6) Team & Operations, 7) Financial Projections & Investment. Focus on therapeutic outcomes, FDA/CE marking requirements, clinical validation, and reimbursement strategies.',
    'Comprehensive seven-chapter review template specifically designed for digital therapeutics and mental health startups.',
    FALSE
) ON CONFLICT DO NOTHING;

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_healthcare_templates_active ON healthcare_templates(is_active);
CREATE INDEX IF NOT EXISTS idx_healthcare_templates_default ON healthcare_templates(is_default);