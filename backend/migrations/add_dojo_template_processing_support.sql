-- Migration: Add complete dojo template processing support
-- Date: 2025-07-29
-- Purpose: Enable dojo template processing results display in frontend

-- Add data_source column to pitch_decks if it doesn't exist
ALTER TABLE pitch_decks ADD COLUMN data_source VARCHAR(50) DEFAULT 'startup';

-- Create visual analysis cache table if it doesn't exist
CREATE TABLE IF NOT EXISTS visual_analysis_cache (
    id SERIAL PRIMARY KEY,
    pitch_deck_id INTEGER NOT NULL REFERENCES pitch_decks(id) ON DELETE CASCADE,
    analysis_result_json TEXT NOT NULL,
    vision_model_used VARCHAR(255) NOT NULL,
    prompt_used TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure unique cache per deck/model/prompt combination
    UNIQUE(pitch_deck_id, vision_model_used, prompt_used)
);

-- Create extraction experiments tracking table if it doesn't exist
CREATE TABLE IF NOT EXISTS extraction_experiments (
    id SERIAL PRIMARY KEY,
    experiment_name VARCHAR(255) NOT NULL,
    pitch_deck_ids INTEGER[] NOT NULL,
    extraction_type VARCHAR(50) NOT NULL DEFAULT 'company_offering',
    text_model_used VARCHAR(255) NOT NULL,
    extraction_prompt TEXT NOT NULL,
    results_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Add template processing columns
    template_processing_results_json TEXT,
    template_processing_completed_at TIMESTAMP,
    
    -- Add classification and enrichment columns
    classification_enabled BOOLEAN DEFAULT FALSE,
    classification_results_json TEXT,
    classification_completed_at TIMESTAMP,
    company_name_results_json TEXT,
    company_name_completed_at TIMESTAMP,
    funding_amount_results_json TEXT,
    funding_amount_completed_at TIMESTAMP,
    deck_date_results_json TEXT,
    deck_date_completed_at TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_visual_analysis_cache_pitch_deck_id 
ON visual_analysis_cache(pitch_deck_id);

CREATE INDEX IF NOT EXISTS idx_visual_analysis_cache_created_at 
ON visual_analysis_cache(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_extraction_experiments_created_at 
ON extraction_experiments(created_at DESC);

CREATE INDEX IF NOT EXISTS idx_extraction_experiments_name 
ON extraction_experiments(experiment_name);

CREATE INDEX IF NOT EXISTS idx_extraction_experiments_template_completed 
ON extraction_experiments(template_processing_completed_at);

-- Add comments for documentation
COMMENT ON TABLE visual_analysis_cache IS 'Caches visual analysis results to avoid re-processing during extraction testing';
COMMENT ON TABLE extraction_experiments IS 'Tracks extraction experiments for comparing different models and prompts';

COMMENT ON COLUMN visual_analysis_cache.analysis_result_json IS 'Full JSON result from visual analysis pipeline';
COMMENT ON COLUMN visual_analysis_cache.vision_model_used IS 'Name of vision model used for analysis';
COMMENT ON COLUMN visual_analysis_cache.prompt_used IS 'Prompt template used for visual analysis';

COMMENT ON COLUMN extraction_experiments.pitch_deck_ids IS 'Array of pitch_deck IDs included in this experiment';
COMMENT ON COLUMN extraction_experiments.extraction_type IS 'Type of extraction being tested (company_offering, etc.)';
COMMENT ON COLUMN extraction_experiments.results_json IS 'JSON object containing extraction results for each deck in sample';
COMMENT ON COLUMN extraction_experiments.template_processing_results_json IS 'JSON object containing template processing results for each deck';