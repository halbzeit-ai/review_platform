-- Add AI extracted startup name field to pitch_decks table
-- This allows comparison between user-provided company name and AI-extracted startup name

ALTER TABLE pitch_decks ADD COLUMN ai_extracted_startup_name VARCHAR(255) DEFAULT NULL;

-- Add index for efficient searching
CREATE INDEX IF NOT EXISTS idx_pitch_decks_ai_extracted_startup_name 
ON pitch_decks(ai_extracted_startup_name);

-- Add comment for documentation
COMMENT ON COLUMN pitch_decks.ai_extracted_startup_name IS 'AI-extracted startup name from pitch deck content, can be compared with user-provided company_name';