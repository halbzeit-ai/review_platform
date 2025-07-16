-- Create pipeline_prompts table for configurable processing prompts
CREATE TABLE IF NOT EXISTS pipeline_prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stage_name TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create index for fast lookup by stage_name
CREATE INDEX IF NOT EXISTS idx_pipeline_prompts_stage ON pipeline_prompts(stage_name, is_active);

-- Insert default image analysis prompt from existing code
INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by) VALUES (
    'image_analysis',
    'Describe this image and make sure to include anything notable about it (include text you see in the image):',
    TRUE,
    'system'
);

-- Insert other default prompts from existing code for future use
INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by) VALUES (
    'role_definition',
    'You are an analyst working at a Venture Capital company. Here is the descriptions of a startup''s pitchdeck.',
    TRUE,
    'system'
);

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by) VALUES (
    'offering_extraction',
    'Your Task is to explain in one single short sentence the service or product the startup provides. Do not mention the name of the product or the company.',
    TRUE,
    'system'
);

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by) VALUES (
    'question_analysis',
    'Your task is to find answers to the following questions: ',
    TRUE,
    'system'
);

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by) VALUES (
    'scoring_analysis',
    'Your task is to give a score between 0 and 7 based on how much information is provided for the following questions. Just give a number, no explanations.',
    TRUE,
    'system'
);

INSERT INTO pipeline_prompts (stage_name, prompt_text, is_active, created_by) VALUES (
    'scientific_hypothesis',
    'You are a medical doctor reviewing a pitchdeck of a health startup. Provide a numbered list of core scientific, health related or medical hypothesis that are addressed by the startup. Do not report market size or any other economic hypotheses. Do not mention the name of the product or the company.',
    TRUE,
    'system'
);