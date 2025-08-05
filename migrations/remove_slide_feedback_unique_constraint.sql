-- Remove unique constraint to allow multiple feedback per slide
-- This enables AI feedback + manual GP/startup feedback on the same slide

-- Drop the unique constraint
ALTER TABLE slide_feedback DROP CONSTRAINT IF EXISTS slide_feedback_pitch_deck_id_slide_number_key;

-- Add a new compound unique constraint that includes feedback_type
-- This allows one AI feedback + multiple manual feedback per slide
ALTER TABLE slide_feedback ADD CONSTRAINT slide_feedback_unique_by_type 
UNIQUE (pitch_deck_id, slide_number, feedback_type);

-- Update the index to include feedback_type for better query performance
DROP INDEX IF EXISTS idx_slide_feedback_slide_number;
CREATE INDEX idx_slide_feedback_slide_lookup ON slide_feedback (pitch_deck_id, slide_number, feedback_type);