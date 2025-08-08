-- Database Connection Monitoring Queries
-- Run these to check database health in real-time

-- 1. Check active connections and their states
SELECT 
    state,
    COUNT(*) as connection_count,
    AVG(EXTRACT(EPOCH FROM NOW() - query_start)) as avg_duration_seconds
FROM pg_stat_activity 
WHERE datname = 'review-platform' 
GROUP BY state 
ORDER BY connection_count DESC;

-- 2. Find long-running transactions (potential culprits)
SELECT 
    pid,
    usename,
    application_name,
    state,
    query_start,
    NOW() - query_start as duration,
    LEFT(query, 200) as query_preview
FROM pg_stat_activity 
WHERE datname = 'review-platform' 
  AND state != 'idle'
  AND NOW() - query_start > INTERVAL '30 seconds'
ORDER BY query_start;

-- 3. Check for idle in transaction connections (the main culprit)
SELECT 
    pid,
    usename,
    application_name,
    state,
    query_start,
    state_change,
    NOW() - query_start as transaction_duration,
    NOW() - state_change as idle_duration,
    LEFT(query, 100) as last_query
FROM pg_stat_activity 
WHERE state = 'idle in transaction'
  AND datname = 'review-platform'
ORDER BY query_start;

-- 4. Processing queue health check
SELECT 
    status,
    COUNT(*) as count,
    MIN(created_at) as oldest_task,
    MAX(created_at) as newest_task,
    COUNT(CASE WHEN created_at < NOW() - INTERVAL '30 minutes' THEN 1 END) as stuck_tasks
FROM processing_queue 
GROUP BY status;

-- 5. Pitch deck processing status distribution
SELECT 
    processing_status,
    COUNT(*) as count,
    COUNT(CASE WHEN created_at < NOW() - INTERVAL '1 hour' THEN 1 END) as stuck_over_1h,
    COUNT(CASE WHEN created_at < NOW() - INTERVAL '30 minutes' THEN 1 END) as stuck_over_30m
FROM pitch_decks 
WHERE processing_status IN ('pending', 'processing', 'queued', 'failed')
GROUP BY processing_status;

-- 6. Connection pool usage (estimated)
SELECT 
    'Total Active Connections' as metric,
    COUNT(*) as value
FROM pg_stat_activity 
WHERE datname = 'review-platform' AND state IS NOT NULL
UNION ALL
SELECT 
    'Idle Connections' as metric,
    COUNT(*) as value
FROM pg_stat_activity 
WHERE datname = 'review-platform' AND state = 'idle'
UNION ALL
SELECT 
    'Active Queries' as metric,
    COUNT(*) as value
FROM pg_stat_activity 
WHERE datname = 'review-platform' AND state = 'active'
UNION ALL
SELECT 
    'Idle in Transaction' as metric,
    COUNT(*) as value
FROM pg_stat_activity 
WHERE datname = 'review-platform' AND state = 'idle in transaction';