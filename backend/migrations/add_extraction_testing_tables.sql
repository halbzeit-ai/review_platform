-- Migration: Add tables for dojo extraction testing functionality
-- Date: 2025-07-20
-- Purpose: Enable visual analysis caching and extraction experiment tracking

-- Create visual analysis cache table
CREATE TABLE IF NOT EXISTS visual_analysis_cache (
    id SERIAL PRIMARY KEY,
    pitch_deck_id INTEGER NOT NULL REFERENCES pitch_decks(id) ON DELETE CASCADE,
    analysis_result_json TEXT NOT NULL, -- Store full visual analysis JSON
    vision_model_used VARCHAR(255) NOT NULL, -- e.g., "gemma3:12b"
    prompt_used TEXT NOT NULL, -- Store the prompt used for visual analysis
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure unique cache per deck/model/prompt combination
    UNIQUE(pitch_deck_id, vision_model_used, prompt_used)
);

-- Create extraction experiments tracking table
CREATE TABLE IF NOT EXISTS extraction_experiments (
    id SERIAL PRIMARY KEY,
    experiment_name VARCHAR(255) NOT NULL, -- e.g., "offering_test_improved_prompt"
    pitch_deck_ids INTEGER[] NOT NULL, -- Array of deck IDs in sample
    extraction_type VARCHAR(50) NOT NULL DEFAULT 'company_offering',
    text_model_used VARCHAR(255) NOT NULL, -- Model used for extraction
    extraction_prompt TEXT NOT NULL, -- Custom prompt for extraction
    results_json TEXT NOT NULL, -- Store all extraction results
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

-- Add comments for documentation
COMMENT ON TABLE visual_analysis_cache IS 'Caches visual analysis results to avoid re-processing during extraction testing';
COMMENT ON TABLE extraction_experiments IS 'Tracks extraction experiments for comparing different models and prompts';

COMMENT ON COLUMN visual_analysis_cache.analysis_result_json IS 'Full JSON result from visual analysis pipeline';
COMMENT ON COLUMN visual_analysis_cache.vision_model_used IS 'Name of vision model used for analysis';
COMMENT ON COLUMN visual_analysis_cache.prompt_used IS 'Prompt template used for visual analysis';

COMMENT ON COLUMN extraction_experiments.pitch_deck_ids IS 'Array of pitch_deck IDs included in this experiment';
COMMENT ON COLUMN extraction_experiments.extraction_type IS 'Type of extraction being tested (company_offering, etc.)';
COMMENT ON COLUMN extraction_experiments.results_json IS 'JSON object containing extraction results for each deck in sample';