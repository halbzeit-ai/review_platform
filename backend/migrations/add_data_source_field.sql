-- Add data_source field to pitch_decks table
-- This allows distinguishing between startup uploads and dojo training data

ALTER TABLE pitch_decks ADD COLUMN data_source VARCHAR(50) DEFAULT 'startup';

-- Add index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_pitch_decks_data_source 
ON pitch_decks(data_source);

-- Add check constraint to ensure valid values
ALTER TABLE pitch_decks ADD CONSTRAINT chk_data_source 
CHECK (data_source IN ('startup', 'dojo'));

-- Update existing records to have 'startup' as default
UPDATE pitch_decks SET data_source = 'startup' WHERE data_source IS NULL;

-- Add comment for documentation
COMMENT ON COLUMN pitch_decks.data_source IS 'Source of the pitch deck: startup (user uploads) or dojo (training data)';