-- URGENT FIX FOR PRODUCTION - Add pipeline_prompts table and extraction prompts

-- Create the pipeline_prompts table if it doesn't exist
CREATE TABLE IF NOT EXISTS pipeline_prompts (
    id SERIAL PRIMARY KEY,
    stage_name VARCHAR(255) NOT NULL,
    prompt_text TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR(255) DEFAULT 'system',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    prompt_type VARCHAR(50),
    prompt_name VARCHAR(255),
    is_enabled BOOLEAN DEFAULT true
);

-- Delete any existing prompts for these stages to avoid duplicates
DELETE FROM pipeline_prompts WHERE stage_name IN ('funding_amount_extraction', 'deck_date_extraction', 'offering_extraction');

-- Insert the critical prompts
INSERT INTO pipeline_prompts 
(stage_name, prompt_text, is_active, created_by, created_at, updated_at, prompt_type, prompt_name, is_enabled)
VALUES 
(
    'funding_amount_extraction',
    'Find the exact funding amount the startup is seeking or has raised from this pitch deck. Look for phrases like ''seeking $X'', ''raising $X'', ''funding round of $X'', or similar. Return only the numerical amount with currency symbol (e.g., ''$2.5M'', ''€500K'', ''$10 million''). If no specific amount is mentioned, return ''Not specified''.',
    true,
    'system',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'extraction',
    'Funding Amount Extraction', 
    true
),
(
    'deck_date_extraction',
    'Find the date when this pitch deck was created or last updated. Look for dates on slides, footers, headers, or any text mentioning when the deck was prepared. Common formats include ''March 2024'', ''2024-03-15'', ''Q1 2024'', ''Spring 2024'', etc. Return only the date in a clear format (e.g., ''March 2024'', ''2024-03-15'', ''Q1 2024''). If no date is found, return ''Date not specified''.',
    true,
    'system',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'extraction',
    'Deck Date Extraction', 
    true
),
(
    'offering_extraction',
    'Extract a comprehensive description of what the company offers, including their products, services, and value proposition. Focus on: 1) What the company does, 2) What products or services they offer, 3) What problems they solve, 4) Who their target customers are. Provide a detailed but concise summary.',
    true,
    'system',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'extraction',
    'Company Offering Extraction',
    true
);

-- Verify the prompts were added
SELECT stage_name, prompt_name, LENGTH(prompt_text) as prompt_length 
FROM pipeline_prompts 
WHERE stage_name IN ('funding_amount_extraction', 'deck_date_extraction', 'offering_extraction')
ORDER BY stage_name;