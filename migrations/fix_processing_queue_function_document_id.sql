-- Fix the get_next_processing_task function to use document_id instead of pitch_deck_id
-- This ensures compatibility with the updated processing queue system

CREATE OR REPLACE FUNCTION get_next_processing_task(
    server_id VARCHAR(255),
    server_capabilities JSONB DEFAULT '{}'
)
RETURNS TABLE(
    task_id INTEGER,
    document_id INTEGER,
    task_type VARCHAR(50),
    file_path TEXT,
    company_id VARCHAR(255),
    processing_options JSONB
) AS $$
DECLARE
    lock_duration INTERVAL := '30 minutes';
    selected_task_id INTEGER;
BEGIN
    -- Clean up any expired locks first
    PERFORM cleanup_expired_locks();
    
    -- Find the next available task (without locking yet)
    SELECT pq.id INTO selected_task_id
    FROM processing_queue pq
    WHERE 
        pq.status IN ('queued', 'retry') 
        AND (pq.next_retry_at IS NULL OR pq.next_retry_at <= CURRENT_TIMESTAMP)
        AND pq.locked_by IS NULL
        -- Check dependencies separately to avoid LEFT JOIN issues
        AND NOT EXISTS (
            SELECT 1 FROM task_dependencies td
            WHERE td.dependent_task_id = pq.id
            AND EXISTS (
                SELECT 1 FROM processing_queue dep 
                WHERE dep.id = td.depends_on_task_id 
                AND dep.status != 'completed'
            )
        )
    ORDER BY pq.priority DESC, pq.created_at ASC
    LIMIT 1;
    
    -- If no task found, return empty
    IF selected_task_id IS NULL THEN
        RETURN;
    END IF;
    
    -- Lock and update the selected task
    UPDATE processing_queue 
    SET 
        locked_by = server_id,
        locked_at = CURRENT_TIMESTAMP,
        lock_expires_at = CURRENT_TIMESTAMP + lock_duration,
        status = 'processing',
        started_at = CASE WHEN started_at IS NULL THEN CURRENT_TIMESTAMP ELSE started_at END
    WHERE id = selected_task_id
    AND locked_by IS NULL  -- Double-check it's still unlocked
    RETURNING 
        processing_queue.id,
        processing_queue.document_id,
        processing_queue.task_type,
        processing_queue.file_path,
        processing_queue.company_id,
        processing_queue.processing_options
    INTO task_id, document_id, task_type, file_path, company_id, processing_options;
    
    -- Return the task if we successfully locked it
    IF task_id IS NOT NULL THEN
        RETURN NEXT;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Also ensure the complete_task function works with document_id
CREATE OR REPLACE FUNCTION complete_task(
    task_id INTEGER,
    results_file_path TEXT DEFAULT NULL,
    processing_metadata JSONB DEFAULT '{}'
)
RETURNS BOOLEAN AS $$
DECLARE
    task_exists BOOLEAN;
BEGIN
    -- Check if task exists
    SELECT EXISTS (
        SELECT 1 FROM processing_queue 
        WHERE id = task_id
    ) INTO task_exists;
    
    IF NOT task_exists THEN
        RETURN FALSE;
    END IF;
    
    -- Mark task as completed
    UPDATE processing_queue 
    SET 
        status = 'completed',
        completed_at = CURRENT_TIMESTAMP,
        results_file_path = complete_task.results_file_path,
        processing_metadata = complete_task.processing_metadata,
        locked_by = NULL,
        locked_at = NULL,
        lock_expires_at = NULL
    WHERE id = task_id;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;