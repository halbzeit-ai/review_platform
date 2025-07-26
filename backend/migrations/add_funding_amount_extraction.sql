-- Add funding amount extraction columns to extraction_experiments table
ALTER TABLE extraction_experiments 
ADD COLUMN funding_amount_results_json TEXT DEFAULT NULL,
ADD COLUMN funding_amount_completed_at TIMESTAMP DEFAULT NULL;

-- Add indexes for funding amount extraction queries
CREATE INDEX IF NOT EXISTS idx_extraction_experiments_funding_amount_completed_at 
ON extraction_experiments(funding_amount_completed_at DESC);