-- Template Configuration Storage
-- Allows GPs to configure template processing preferences

CREATE TABLE template_configurations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    use_single_template BOOLEAN DEFAULT false,
    selected_template_id INTEGER REFERENCES analysis_templates(id),
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one configuration per user
    CONSTRAINT unique_user_template_config UNIQUE (user_id)
);

-- Index for efficient lookups
CREATE INDEX idx_template_configurations_user_id ON template_configurations(user_id);

-- Update trigger for updated_at timestamp
CREATE OR REPLACE FUNCTION update_template_configurations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_template_configurations_updated_at
  BEFORE UPDATE ON template_configurations
  FOR EACH ROW
  EXECUTE FUNCTION update_template_configurations_updated_at();

-- Add columns to processing_queue to track template decisions
ALTER TABLE processing_queue ADD COLUMN IF NOT EXISTS template_id_used INTEGER REFERENCES analysis_templates(id);
ALTER TABLE processing_queue ADD COLUMN IF NOT EXISTS template_source VARCHAR(50); -- 'user_override', 'classification', 'fallback'

COMMENT ON TABLE template_configurations IS 'Stores GP template processing preferences (single template mode vs classification mode)';
COMMENT ON COLUMN template_configurations.use_single_template IS 'When true, use selected_template_id for all analyses. When false, use classification.';
COMMENT ON COLUMN template_configurations.selected_template_id IS 'Template to use when use_single_template is true';
COMMENT ON COLUMN processing_queue.template_id_used IS 'Actual template ID used for processing (for analytics)';
COMMENT ON COLUMN processing_queue.template_source IS 'How template was selected: user_override, classification, or fallback';