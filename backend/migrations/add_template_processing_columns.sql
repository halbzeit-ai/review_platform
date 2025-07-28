-- Add template processing columns to extraction_experiments table
ALTER TABLE extraction_experiments 
ADD COLUMN IF NOT EXISTS template_processing_results_json TEXT;

ALTER TABLE extraction_experiments 
ADD COLUMN IF NOT EXISTS template_processing_completed_at TIMESTAMP;

-- Add index for template processing completed timestamp
CREATE INDEX IF NOT EXISTS idx_extraction_experiments_template_completed 
ON extraction_experiments(template_processing_completed_at);