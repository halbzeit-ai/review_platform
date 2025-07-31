-- Add zip_filename column to pitch_decks table
-- This column stores the original ZIP filename for dojo files to enable filtering by archive

ALTER TABLE pitch_decks 
ADD COLUMN zip_filename VARCHAR(255) NULL;

-- Add index for performance when filtering by ZIP filename
CREATE INDEX idx_pitch_decks_zip_filename ON pitch_decks(zip_filename);

-- Add comment for documentation
COMMENT ON COLUMN pitch_decks.zip_filename IS 'Original ZIP filename for dojo files, used for filtering decks by archive';