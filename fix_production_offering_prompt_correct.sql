-- URGENT FIX: Update offering_extraction prompt to use the correct one-sentence version

-- First, check what prompts we have
SELECT stage_name, prompt_name, SUBSTRING(prompt_text, 1, 100) as prompt_preview
FROM pipeline_prompts 
WHERE stage_name IN ('offering_extraction', 'company_offering');

-- Update the offering_extraction prompt to use your one-sentence version
UPDATE pipeline_prompts 
SET prompt_text = 'You are an analyst working at a Venture Capital company. Here is the descriptions of a startup''s pitchdeck. Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company.',
    prompt_name = 'Company Offering Extraction (One Sentence)',
    updated_at = CURRENT_TIMESTAMP
WHERE stage_name = 'offering_extraction';

-- Verify the update
SELECT stage_name, prompt_name, prompt_text 
FROM pipeline_prompts 
WHERE stage_name = 'offering_extraction';