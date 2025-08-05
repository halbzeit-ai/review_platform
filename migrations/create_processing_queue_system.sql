-- Create a robust processing queue system to handle server restarts gracefully
-- This ensures processing tasks survive server restarts and handle failures gracefully

-- Processing queue table to store all processing tasks
CREATE TABLE IF NOT EXISTS processing_queue (
    id SERIAL PRIMARY KEY,
    pitch_deck_id INTEGER NOT NULL REFERENCES pitch_decks(id) ON DELETE CASCADE,
    task_type VARCHAR(50) NOT NULL DEFAULT 'pdf_analysis',
    status VARCHAR(20) NOT NULL DEFAULT 'queued', -- queued, processing, completed, failed, retry
    priority INTEGER NOT NULL DEFAULT 1, -- 1=normal, 2=high, 3=urgent
    
    -- Task parameters
    file_path TEXT NOT NULL,
    company_id VARCHAR(255) NOT NULL,
    processing_options JSONB DEFAULT '{}',
    
    -- Progress tracking
    progress_percentage INTEGER DEFAULT 0,
    current_step VARCHAR(255),
    progress_message TEXT,
    
    -- Timing and retry logic
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    next_retry_at TIMESTAMP,
    
    -- Error handling
    last_error TEXT,
    error_count INTEGER DEFAULT 0,
    
    -- Locking mechanism for concurrent processing
    locked_by VARCHAR(255), -- server instance identifier
    locked_at TIMESTAMP,
    lock_expires_at TIMESTAMP,
    
    -- Results
    results_file_path TEXT,
    processing_metadata JSONB DEFAULT '{}'
);

-- Index for efficient queue processing
CREATE INDEX IF NOT EXISTS idx_processing_queue_status_priority ON processing_queue(status, priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_processing_queue_pitch_deck ON processing_queue(pitch_deck_id);
CREATE INDEX IF NOT EXISTS idx_processing_queue_retry ON processing_queue(status, next_retry_at) WHERE status = 'retry';
CREATE INDEX IF NOT EXISTS idx_processing_queue_lock ON processing_queue(locked_by, lock_expires_at) WHERE locked_by IS NOT NULL;

-- Processing progress tracking table (for detailed progress steps)
CREATE TABLE IF NOT EXISTS processing_progress (
    id SERIAL PRIMARY KEY,
    processing_queue_id INTEGER NOT NULL REFERENCES processing_queue(id) ON DELETE CASCADE,
    step_name VARCHAR(255) NOT NULL,
    step_status VARCHAR(20) NOT NULL, -- started, completed, failed
    progress_percentage INTEGER DEFAULT 0,
    message TEXT,
    step_data JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_processing_progress_queue ON processing_progress(processing_queue_id, created_at DESC);

-- Server instance tracking for distributed processing
CREATE TABLE IF NOT EXISTS processing_servers (
    id VARCHAR(255) PRIMARY KEY, -- server identifier (hostname + process_id)
    server_type VARCHAR(50) NOT NULL, -- 'cpu', 'gpu' 
    status VARCHAR(20) NOT NULL DEFAULT 'active', -- active, inactive, maintenance
    last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    capabilities JSONB DEFAULT '{}',
    current_load INTEGER DEFAULT 0,
    max_concurrent_tasks INTEGER DEFAULT 5,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Task dependencies (for complex workflows)
CREATE TABLE IF NOT EXISTS task_dependencies (
    id SERIAL PRIMARY KEY,
    dependent_task_id INTEGER NOT NULL REFERENCES processing_queue(id) ON DELETE CASCADE,
    depends_on_task_id INTEGER NOT NULL REFERENCES processing_queue(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50) DEFAULT 'completion', -- completion, success_only
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add task queue reference to pitch_decks table
ALTER TABLE pitch_decks 
ADD COLUMN IF NOT EXISTS current_processing_task_id INTEGER REFERENCES processing_queue(id);

-- Function to clean up expired locks
CREATE OR REPLACE FUNCTION cleanup_expired_locks()
RETURNS INTEGER AS $$
DECLARE
    cleaned_count INTEGER;
BEGIN
    UPDATE processing_queue 
    SET 
        locked_by = NULL,
        locked_at = NULL,
        lock_expires_at = NULL,
        status = CASE 
            WHEN status = 'processing' THEN 'queued'  -- Reset to queued for retry
            ELSE status
        END
    WHERE 
        locked_by IS NOT NULL 
        AND lock_expires_at < CURRENT_TIMESTAMP;
    
    GET DIAGNOSTICS cleaned_count = ROW_COUNT;
    RETURN cleaned_count;
END;
$$ LANGUAGE plpgsql;

-- Function to get next available task for processing
CREATE OR REPLACE FUNCTION get_next_processing_task(
    server_id VARCHAR(255),
    server_capabilities JSONB DEFAULT '{}'
)
RETURNS TABLE(
    task_id INTEGER,
    pitch_deck_id INTEGER,
    task_type VARCHAR(50),
    file_path TEXT,
    company_id VARCHAR(255),
    processing_options JSONB
) AS $$
DECLARE
    lock_duration INTERVAL := '30 minutes';
BEGIN
    -- Clean up any expired locks first
    PERFORM cleanup_expired_locks();
    
    -- Find and lock the next available task
    UPDATE processing_queue 
    SET 
        locked_by = server_id,
        locked_at = CURRENT_TIMESTAMP,
        lock_expires_at = CURRENT_TIMESTAMP + lock_duration,
        status = 'processing',
        started_at = CASE WHEN started_at IS NULL THEN CURRENT_TIMESTAMP ELSE started_at END
    WHERE id = (
        SELECT pq.id
        FROM processing_queue pq
        LEFT JOIN task_dependencies td ON pq.id = td.dependent_task_id
        LEFT JOIN processing_queue dep ON td.depends_on_task_id = dep.id
        WHERE 
            pq.status IN ('queued', 'retry') 
            AND (pq.next_retry_at IS NULL OR pq.next_retry_at <= CURRENT_TIMESTAMP)
            AND pq.locked_by IS NULL
            -- Check dependencies are satisfied
            AND (td.id IS NULL OR dep.status = 'completed')
        ORDER BY pq.priority DESC, pq.created_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    )
    RETURNING 
        processing_queue.id,
        processing_queue.pitch_deck_id,
        processing_queue.task_type,
        processing_queue.file_path,
        processing_queue.company_id,
        processing_queue.processing_options;
END;
$$ LANGUAGE plpgsql;

-- Function to update task progress
CREATE OR REPLACE FUNCTION update_task_progress(
    task_id INTEGER,
    new_progress INTEGER,
    step_name VARCHAR(255) DEFAULT NULL,
    message TEXT DEFAULT NULL,
    step_data JSONB DEFAULT '{}'
)
RETURNS BOOLEAN AS $$
BEGIN
    -- Update main task progress
    UPDATE processing_queue 
    SET 
        progress_percentage = new_progress,
        current_step = COALESCE(step_name, current_step),
        progress_message = COALESCE(message, progress_message),
        lock_expires_at = CURRENT_TIMESTAMP + INTERVAL '30 minutes' -- Extend lock
    WHERE id = task_id;
    
    -- Insert detailed progress step if step_name provided
    IF step_name IS NOT NULL THEN
        INSERT INTO processing_progress (
            processing_queue_id, step_name, step_status, 
            progress_percentage, message, step_data
        ) VALUES (
            task_id, step_name, 'started',
            new_progress, message, step_data
        );
    END IF;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to complete a task
CREATE OR REPLACE FUNCTION complete_task(
    task_id INTEGER,
    success BOOLEAN,
    results_path TEXT DEFAULT NULL,
    error_message TEXT DEFAULT NULL,
    metadata JSONB DEFAULT '{}'
)
RETURNS BOOLEAN AS $$
DECLARE
    deck_id INTEGER;
BEGIN
    -- Update task status
    UPDATE processing_queue 
    SET 
        status = CASE WHEN success THEN 'completed' ELSE 'failed' END,
        completed_at = CURRENT_TIMESTAMP,
        progress_percentage = CASE WHEN success THEN 100 ELSE progress_percentage END,
        results_file_path = results_path,
        last_error = error_message,
        error_count = CASE WHEN success THEN error_count ELSE error_count + 1 END,
        processing_metadata = metadata,
        locked_by = NULL,
        locked_at = NULL,
        lock_expires_at = NULL
    WHERE id = task_id
    RETURNING pitch_deck_id INTO deck_id;
    
    -- Update pitch deck status
    IF FOUND AND success THEN
        UPDATE pitch_decks 
        SET 
            processing_status = 'completed',
            results_file_path = results_path,
            current_processing_task_id = NULL
        WHERE id = deck_id;
    ELSIF FOUND AND NOT success THEN
        UPDATE pitch_decks 
        SET processing_status = 'failed'
        WHERE id = deck_id;
    END IF;
    
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Function to retry failed tasks
CREATE OR REPLACE FUNCTION retry_failed_task(task_id INTEGER)
RETURNS BOOLEAN AS $$
BEGIN
    UPDATE processing_queue 
    SET 
        status = 'retry',
        retry_count = retry_count + 1,
        next_retry_at = CURRENT_TIMESTAMP + (INTERVAL '5 minutes' * POWER(2, retry_count)), -- Exponential backoff
        locked_by = NULL,
        locked_at = NULL,
        lock_expires_at = NULL
    WHERE 
        id = task_id 
        AND status = 'failed'
        AND retry_count < max_retries;
        
    RETURN FOUND;
END;
$$ LANGUAGE plpgsql;

-- Comments explaining the system
COMMENT ON TABLE processing_queue IS 'Persistent task queue for PDF processing that survives server restarts';
COMMENT ON TABLE processing_progress IS 'Detailed progress tracking for each processing step';
COMMENT ON TABLE processing_servers IS 'Active server instances for distributed processing';
COMMENT ON TABLE task_dependencies IS 'Task dependency management for complex workflows';