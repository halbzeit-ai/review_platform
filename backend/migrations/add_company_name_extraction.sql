-- Migration: Add company name extraction to extraction experiments
-- Date: 2025-07-26
-- Purpose: Enable company name extraction as incremental enrichment of extraction experiments

-- Add company name extraction columns to extraction_experiments table
ALTER TABLE extraction_experiments 
ADD COLUMN company_name_results_json TEXT DEFAULT NULL,
ADD COLUMN company_name_completed_at TIMESTAMP DEFAULT NULL;

-- Add indexes for company name extraction queries
CREATE INDEX IF NOT EXISTS idx_extraction_experiments_company_name_completed_at 
ON extraction_experiments(company_name_completed_at DESC);

-- Add comments for documentation
COMMENT ON COLUMN extraction_experiments.company_name_results_json IS 'JSON object containing company name extraction results for each deck in the experiment';
COMMENT ON COLUMN extraction_experiments.company_name_completed_at IS 'When company name extraction was completed';