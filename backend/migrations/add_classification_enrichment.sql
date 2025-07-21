-- Migration: Add classification enrichment to extraction experiments
-- Date: 2025-07-21
-- Purpose: Enable classification testing as incremental enrichment of extraction experiments

-- Add classification columns to extraction_experiments table
ALTER TABLE extraction_experiments 
ADD COLUMN classification_enabled BOOLEAN DEFAULT FALSE,
ADD COLUMN classification_results_json TEXT DEFAULT NULL,
ADD COLUMN classification_model_used VARCHAR(255) DEFAULT NULL,
ADD COLUMN classification_prompt_used TEXT DEFAULT NULL,
ADD COLUMN classification_completed_at TIMESTAMP DEFAULT NULL;

-- Add indexes for classification queries
CREATE INDEX IF NOT EXISTS idx_extraction_experiments_classification_enabled 
ON extraction_experiments(classification_enabled);

CREATE INDEX IF NOT EXISTS idx_extraction_experiments_classification_completed_at 
ON extraction_experiments(classification_completed_at DESC);

-- Add comments for documentation
COMMENT ON COLUMN extraction_experiments.classification_enabled IS 'Whether classification enrichment has been requested for this experiment';
COMMENT ON COLUMN extraction_experiments.classification_results_json IS 'JSON object containing classification results for each deck in the experiment';
COMMENT ON COLUMN extraction_experiments.classification_model_used IS 'Model used for classification (if different from text model)';
COMMENT ON COLUMN extraction_experiments.classification_prompt_used IS 'Prompt used for classification';
COMMENT ON COLUMN extraction_experiments.classification_completed_at IS 'When classification enrichment was completed';