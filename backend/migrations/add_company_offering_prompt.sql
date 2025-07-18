-- Add company_offering stage to pipeline_prompts table
-- This provides the complete prompt including role context for better UI integration

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by) VALUES (
    'company_offering',
    'You are an analyst working at a Venture Capital company. Here is the descriptions of a startup''s pitchdeck. Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company.',
    TRUE,
    'system'
);