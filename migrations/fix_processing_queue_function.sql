-- Fix the get_next_processing_task function
-- The issue is that FOR UPDATE cannot be used with LEFT JOINs on the nullable side

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
        processing_queue.pitch_deck_id,
        processing_queue.task_type,
        processing_queue.file_path,
        processing_queue.company_id,
        processing_queue.processing_options
    INTO task_id, pitch_deck_id, task_type, file_path, company_id, processing_options;
    
    -- Return the task if we successfully locked it
    IF task_id IS NOT NULL THEN
        RETURN NEXT;
    END IF;
END;
$$ LANGUAGE plpgsql;