-- URGENT FIX: Update offering_extraction prompt to one-sentence version

-- Update the offering extraction prompt to the one-sentence version
UPDATE pipeline_prompts 
SET prompt_text = 'Based on the pitch deck visual analysis, describe in exactly one sentence what the company offers, including their main product or service.',
    updated_at = CURRENT_TIMESTAMP
WHERE stage_name = 'offering_extraction';

-- Verify the update
SELECT stage_name, prompt_name, prompt_text 
FROM pipeline_prompts 
WHERE stage_name = 'offering_extraction';