-- Create stage templates table for reusable stage definitions
CREATE TABLE IF NOT EXISTS stage_templates (
    id SERIAL PRIMARY KEY,
    stage_name VARCHAR(255) NOT NULL,
    stage_code VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    stage_order INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT TRUE,
    estimated_duration_days INTEGER,
    stage_metadata JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);