-- Migration: Add slide feedback system
-- Created: 2025-08-05
-- Purpose: Add slide-level AI feedback functionality

-- Create slide_feedback table
CREATE TABLE IF NOT EXISTS slide_feedback (
    id SERIAL PRIMARY KEY,
    pitch_deck_id INTEGER NOT NULL REFERENCES pitch_decks(id) ON DELETE CASCADE,
    slide_number INTEGER NOT NULL,
    slide_filename VARCHAR(255) NOT NULL,
    feedback_text TEXT,
    feedback_type VARCHAR(50) DEFAULT 'ai_analysis',
    has_issues BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pitch_deck_id, slide_number)
);

-- Add index for better query performance
CREATE INDEX IF NOT EXISTS idx_slide_feedback_pitch_deck_id ON slide_feedback(pitch_deck_id);
CREATE INDEX IF NOT EXISTS idx_slide_feedback_slide_number ON slide_feedback(pitch_deck_id, slide_number);

-- Add slide feedback prompt to pipeline_prompts table
INSERT INTO pipeline_prompts (stage_name, prompt_text, created_at, updated_at) 
VALUES (
    'slide_feedback', 
    'Analyze this slide for clarity and effectiveness. Focus on:

1. **Visual Clarity**: Can the content be understood in 10 seconds?
2. **Visual Complexity**: Is the slide cluttered or well-organized?
3. **Business Case Helpfulness**: Does it effectively communicate its intended message?
4. **Overall Comprehension**: Would an investor understand the key point quickly?

Provide concise, actionable feedback (2-3 sentences max) that helps improve the slide''s effectiveness. Focus on specific issues like:
- Text readability (too small, too much text)
- Visual hierarchy problems
- Unclear messaging or confusing layout
- Missing context or unclear purpose

If the slide is clear, well-organized, and effectively communicates its message, respond with exactly "SLIDE_OK".

Slide description: {slide_description}',
    NOW(), 
    NOW()
) ON CONFLICT (stage_name) DO UPDATE SET
    prompt_text = EXCLUDED.prompt_text,
    updated_at = NOW();

-- Add comment to document the table purpose
COMMENT ON TABLE slide_feedback IS 'Stores AI-generated feedback for individual slides in pitch decks';
COMMENT ON COLUMN slide_feedback.pitch_deck_id IS 'Reference to the pitch deck containing this slide';
COMMENT ON COLUMN slide_feedback.slide_number IS 'Sequential number of the slide within the deck (1-based)';
COMMENT ON COLUMN slide_feedback.slide_filename IS 'Filename of the slide image (e.g., slide_001.png)';
COMMENT ON COLUMN slide_feedback.feedback_text IS 'AI-generated feedback text, NULL if has_issues=false';
COMMENT ON COLUMN slide_feedback.feedback_type IS 'Type of feedback: ai_analysis, human_review, etc.';
COMMENT ON COLUMN slide_feedback.has_issues IS 'TRUE if slide has issues requiring feedback, FALSE for "SLIDE_OK"';