-- Add the exact working prompts from pipeline.py fallbacks to production database
-- These are the prompts that were actually working in production via the API fallbacks

-- First check if they already exist and delete if present
DELETE FROM pipeline_prompts WHERE stage_name IN ('funding_amount_extraction', 'deck_date_extraction');

-- Insert the working prompts
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
    'Funding Amount Extraction (from pipeline.py)', 
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
    'Deck Date Extraction (from pipeline.py)', 
    true
);

-- Verify the prompts were added
SELECT stage_name, prompt_name, is_active, LENGTH(prompt_text) as prompt_length 
FROM pipeline_prompts 
WHERE stage_name IN ('funding_amount_extraction', 'deck_date_extraction')
ORDER BY stage_name;