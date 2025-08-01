-- Pipeline prompts for production database
-- Generated from development database

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by, prompt_type, prompt_name, is_enabled) VALUES
('deck_date_extraction', 'Please identify when this pitch deck was created or last updated. Look for dates in headers, footers, slide timestamps, version information, or any date references that indicate when the deck was prepared. Focus on the most recent date that reflects when the current version was created. Provide the date in a clear format (e.g., ''March 2024'', ''2024-03-15'', ''Q1 2024''). If no date information is available, respond with ''Date not found''.', True, 'system', 'extraction', 'Deck Date Extraction', True)
ON CONFLICT (stage_name) DO UPDATE SET
prompt_text = EXCLUDED.prompt_text, is_active = EXCLUDED.is_active, prompt_type = EXCLUDED.prompt_type, prompt_name = EXCLUDED.prompt_name, is_enabled = EXCLUDED.is_enabled;

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by, prompt_type, prompt_name, is_enabled) VALUES
('funding_amount_extraction', 'Please extract the specific funding amount the startup is seeking from the pitch deck. Look for phrases like ''seeking €X'', ''raising $X'', ''funding requirement of X'', or similar. If you find multiple amounts (seed, Series A, total, etc.), focus on the primary funding amount being sought in this round. Provide only the amount (e.g., ''€2.5M'', ''$500K'', ''£1M'') without additional explanation. If no specific amount is mentioned, respond with ''Not specified''.', True, 'system', 'extraction', 'Funding Amount Extraction', True)
ON CONFLICT (stage_name) DO UPDATE SET
prompt_text = EXCLUDED.prompt_text, is_active = EXCLUDED.is_active, prompt_type = EXCLUDED.prompt_type, prompt_name = EXCLUDED.prompt_name, is_enabled = EXCLUDED.is_enabled;

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by, prompt_type, prompt_name, is_enabled) VALUES
('image_analysis', 'Describe this slide from a pitchdeck from a perspective of an investor, but do not interpret the content. Make sure to include anything notable about it, include text you see in the image, if you see any charts or graphs, describe them in a way that a person that doesn''t see them would understand the content. Your style should be rather formal, not colloquial. Do not include any conversational text such as "Okay, here''s a detailed description of the image, focusing on the requested aspects:"', True, 'system', 'extraction', 'Default Prompt', True)
ON CONFLICT (stage_name) DO UPDATE SET
prompt_text = EXCLUDED.prompt_text, is_active = EXCLUDED.is_active, prompt_type = EXCLUDED.prompt_type, prompt_name = EXCLUDED.prompt_name, is_enabled = EXCLUDED.is_enabled;

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by, prompt_type, prompt_name, is_enabled) VALUES
('offering_extraction', 'Your task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company. Please do not write any introductory sentences and do not repeat the instruction, just provide what you are asked for.', True, 'system', 'extraction', 'Default Prompt', True)
ON CONFLICT (stage_name) DO UPDATE SET
prompt_text = EXCLUDED.prompt_text, is_active = EXCLUDED.is_active, prompt_type = EXCLUDED.prompt_type, prompt_name = EXCLUDED.prompt_name, is_enabled = EXCLUDED.is_enabled;

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by, prompt_type, prompt_name, is_enabled) VALUES
('question_analysis', 'Your task is to find answers to the following questions: ', True, 'system', 'extraction', 'Default Prompt', True)
ON CONFLICT (stage_name) DO UPDATE SET
prompt_text = EXCLUDED.prompt_text, is_active = EXCLUDED.is_active, prompt_type = EXCLUDED.prompt_type, prompt_name = EXCLUDED.prompt_name, is_enabled = EXCLUDED.is_enabled;

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by, prompt_type, prompt_name, is_enabled) VALUES
('role_definition', 'You are an analyst working at a Venture Capital company. Here is the descriptions of a startup''s pitchdeck.', True, 'system', 'extraction', 'Default Prompt', True)
ON CONFLICT (stage_name) DO UPDATE SET
prompt_text = EXCLUDED.prompt_text, is_active = EXCLUDED.is_active, prompt_type = EXCLUDED.prompt_type, prompt_name = EXCLUDED.prompt_name, is_enabled = EXCLUDED.is_enabled;

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by, prompt_type, prompt_name, is_enabled) VALUES
('scientific_hypothesis', 'You are a medical doctor reviewing a pitchdeck of a health startup. Provide a numbered list of core scientific, health related or medical hypothesis that are addressed by the startup. Do not report market size or any other economic hypotheses. Do not mention the name of the product or the company.', True, 'system', 'extraction', 'Default Prompt', True)
ON CONFLICT (stage_name) DO UPDATE SET
prompt_text = EXCLUDED.prompt_text, is_active = EXCLUDED.is_active, prompt_type = EXCLUDED.prompt_type, prompt_name = EXCLUDED.prompt_name, is_enabled = EXCLUDED.is_enabled;

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by, prompt_type, prompt_name, is_enabled) VALUES
('scoring_analysis', 'Your task is to give a score between 0 and 7 based on how much information is provided for the following questions. Just give a number, no explanations.', True, 'system', 'extraction', 'Default Prompt', True)
ON CONFLICT (stage_name) DO UPDATE SET
prompt_text = EXCLUDED.prompt_text, is_active = EXCLUDED.is_active, prompt_type = EXCLUDED.prompt_type, prompt_name = EXCLUDED.prompt_name, is_enabled = EXCLUDED.is_enabled;

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by, prompt_type, prompt_name, is_enabled) VALUES
('startup_name_extraction', 'Please find the name of the startup in the pitchdeck. Deliver only the name, no conversational text around it.', True, 'system', 'extraction', 'Default Prompt', True)
ON CONFLICT (stage_name) DO UPDATE SET
prompt_text = EXCLUDED.prompt_text, is_active = EXCLUDED.is_active, prompt_type = EXCLUDED.prompt_type, prompt_name = EXCLUDED.prompt_name, is_enabled = EXCLUDED.is_enabled;

