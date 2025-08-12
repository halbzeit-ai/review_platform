-- Migration: Add context window information to model_configs table
-- This replaces hardcoded model name guessing with proper database-driven context window management

-- Add new columns to model_configs table
ALTER TABLE model_configs 
ADD COLUMN IF NOT EXISTS max_context_window INTEGER DEFAULT 4096,
ADD COLUMN IF NOT EXISTS recommended_context_window INTEGER DEFAULT 4096,
ADD COLUMN IF NOT EXISTS context_window_notes TEXT;

-- Update existing models with their actual context window sizes
-- Based on official model specifications

-- gemma3:12b - 128k context window
UPDATE model_configs 
SET max_context_window = 131072,  -- 128k tokens
    recommended_context_window = 32768,  -- Use 32k for safety/performance
    context_window_notes = 'Gemma 3 12B with 128k context window. Using 32k for optimal performance.'
WHERE model_name = 'gemma3:12b';

-- phi4:latest - 16k context window  
UPDATE model_configs 
SET max_context_window = 16384,   -- 16k tokens
    recommended_context_window = 16384,  -- Use full 16k
    context_window_notes = 'Phi-4 with 16k context window. Safe to use full capacity.'
WHERE model_name = 'phi4:latest';

-- Add entries for other common models (not currently active but for future use)
INSERT INTO model_configs (model_name, model_type, max_context_window, recommended_context_window, context_window_notes, is_active, created_at, updated_at)
VALUES 
    ('gemma3:27b', 'text', 131072, 65536, 'Gemma 3 27B with 128k context window. Using 64k for optimal performance.', false, NOW(), NOW()),
    ('qwen2.5:32b', 'text', 262144, 131072, 'Qwen 2.5 32B with 256k context window. Using 128k for optimal performance.', false, NOW(), NOW()),
    ('moondream:latest', 'vision', 2048, 2048, 'Moondream vision model with 2k context window. Limited capacity.', false, NOW(), NOW())
ON CONFLICT (model_name, model_type) DO UPDATE SET
    max_context_window = EXCLUDED.max_context_window,
    recommended_context_window = EXCLUDED.recommended_context_window,
    context_window_notes = EXCLUDED.context_window_notes,
    updated_at = NOW();

-- Verify the updates
SELECT 
    model_name,
    model_type,
    is_active,
    max_context_window,
    recommended_context_window,
    context_window_notes
FROM model_configs 
ORDER BY is_active DESC, model_type, model_name;