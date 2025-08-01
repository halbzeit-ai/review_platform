-- Create missing tables in production database
-- Based on development database schema

-- Pipeline prompts table with all columns
CREATE TABLE IF NOT EXISTS pipeline_prompts (
    id SERIAL PRIMARY KEY,
    stage_name TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    prompt_type VARCHAR(255),
    prompt_name VARCHAR(255),
    is_enabled BOOLEAN DEFAULT TRUE
);

-- Create indexes
CREATE INDEX IF NOT EXISTS ix_pipeline_prompts_stage_name ON pipeline_prompts(stage_name);
CREATE INDEX IF NOT EXISTS ix_pipeline_prompts_is_active ON pipeline_prompts(is_active);

-- Add unique constraint on stage_name for conflict resolution
ALTER TABLE pipeline_prompts ADD CONSTRAINT uq_pipeline_prompts_stage_name UNIQUE (stage_name);

-- Create any other missing tables that might be needed
-- (Add more CREATE TABLE statements here if other tables are missing)