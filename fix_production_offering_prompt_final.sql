-- URGENT FIX: Update offering_extraction prompt to use the correct one-sentence version

-- Update the offering_extraction prompt to use your exact one-sentence version
UPDATE pipeline_prompts 
SET prompt_text = 'You are an analyst working at a Venture Capital company. Here is the descriptions of a startup''s pitchdeck. Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company.',
    prompt_name = 'Company Offering Extraction (One Sentence)',
    updated_at = CURRENT_TIMESTAMP
WHERE stage_name = 'offering_extraction';

-- Verify the update
SELECT stage_name, prompt_name, prompt_text 
FROM pipeline_prompts 
WHERE stage_name = 'offering_extraction';