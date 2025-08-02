-- Fix missing unique constraint on visual_analysis_cache table
-- This constraint is required for the ON CONFLICT clause in the insert statement

-- Add unique constraint for (pitch_deck_id, vision_model_used, prompt_used)
ALTER TABLE visual_analysis_cache 
ADD CONSTRAINT visual_analysis_cache_unique_deck_model_prompt 
UNIQUE (pitch_deck_id, vision_model_used, prompt_used);

-- Also add an index on created_at for performance
CREATE INDEX IF NOT EXISTS idx_visual_analysis_cache_created_at 
ON visual_analysis_cache(created_at DESC);