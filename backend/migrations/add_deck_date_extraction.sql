-- Add deck date extraction columns to extraction_experiments table
ALTER TABLE extraction_experiments 
ADD COLUMN deck_date_results_json TEXT DEFAULT NULL,
ADD COLUMN deck_date_completed_at TIMESTAMP DEFAULT NULL;

-- Add indexes for deck date extraction queries
CREATE INDEX IF NOT EXISTS idx_extraction_experiments_deck_date_completed_at 
ON extraction_experiments(deck_date_completed_at DESC);