#!/bin/bash

# Database Health Monitor - Detects and prevents transaction buildup
# Run this every 5 minutes via cron to catch issues early

set -euo pipefail

LOG_FILE="/mnt/CPU-GPU/logs/database-health.log"
ALERT_THRESHOLD=10  # Alert if more than 10 idle transactions
CLEANUP_THRESHOLD=5 # Auto-cleanup transactions older than 5 minutes
NOTIFICATION_EMAIL="admin@halbzeit.ai"

log() {
    echo "$(date -Iseconds) [DB-HEALTH] $1" | tee -a "$LOG_FILE"
}

check_idle_transactions() {
    local count
    count=$(sudo -u postgres psql -d review-platform -t -c "
        SELECT COUNT(*) 
        FROM pg_stat_activity 
        WHERE state = 'idle in transaction' 
          AND query_start < NOW() - INTERVAL '2 minutes';
    " | tr -d ' ')
    
    echo "$count"
}

get_idle_transaction_details() {
    sudo -u postgres psql -d review-platform -c "
        SELECT pid, usename, application_name, state, 
               query_start, state_change, 
               NOW() - query_start AS duration,
               LEFT(query, 100) AS query_preview
        FROM pg_stat_activity 
        WHERE state = 'idle in transaction' 
          AND query_start < NOW() - INTERVAL '2 minutes'
        ORDER BY query_start;
    "
}

cleanup_stuck_transactions() {
    local cleanup_count
    cleanup_count=$(sudo -u postgres psql -d review-platform -t -c "
        SELECT COUNT(pg_terminate_backend(pid))
        FROM pg_stat_activity 
        WHERE state = 'idle in transaction' 
          AND query_start < NOW() - INTERVAL '${CLEANUP_THRESHOLD} minutes';
    " | tr -d ' ')
    
    echo "$cleanup_count"
}

check_connection_pool_exhaustion() {
    local active_connections
    active_connections=$(sudo -u postgres psql -d review-platform -t -c "
        SELECT COUNT(*) 
        FROM pg_stat_activity 
        WHERE datname = 'review-platform' AND state IS NOT NULL;
    " | tr -d ' ')
    
    echo "$active_connections"
}

check_processing_queue_health() {
    local stuck_pending
    stuck_pending=$(sudo -u postgres psql -d review-platform -t -c "
        SELECT COUNT(*) 
        FROM pitch_decks 
        WHERE processing_status IN ('pending', 'processing', 'queued') 
          AND created_at < NOW() - INTERVAL '30 minutes';
    " | tr -d ' ')
    
    echo "$stuck_pending"
}

main() {
    log "=== Database Health Check Started ==="
    
    # Check 1: Idle transactions
    idle_count=$(check_idle_transactions)
    log "Idle transactions: $idle_count"
    
    if [ "$idle_count" -gt "$ALERT_THRESHOLD" ]; then
        log "⚠️  ALERT: $idle_count idle transactions detected (threshold: $ALERT_THRESHOLD)"
        get_idle_transaction_details | tee -a "$LOG_FILE"
        
        # Auto-cleanup if severe
        if [ "$idle_count" -gt 20 ]; then
            log "🚨 CRITICAL: Auto-cleaning up stuck transactions"
            cleaned=$(cleanup_stuck_transactions)
            log "✅ Cleaned up $cleaned stuck transactions"
            
            # Restart backend service if necessary
            if [ "$cleaned" -gt 10 ]; then
                log "🔄 Restarting backend service due to transaction cleanup"
                sudo systemctl restart review-platform.service
                sleep 10
                log "✅ Backend service restarted"
            fi
        fi
    fi
    
    # Check 2: Connection pool health
    active_conn=$(check_connection_pool_exhaustion)
    log "Active connections: $active_conn"
    
    if [ "$active_conn" -gt 25 ]; then
        log "⚠️  WARNING: High connection count ($active_conn)"
    fi
    
    # Check 3: Processing queue health
    stuck_processing=$(check_processing_queue_health)
    log "Stuck processing decks: $stuck_processing"
    
    if [ "$stuck_processing" -gt 5 ]; then
        log "⚠️  WARNING: $stuck_processing decks stuck in processing"
        
        # Auto-cleanup stuck processing if severe
        if [ "$stuck_processing" -gt 15 ]; then
            log "🚨 CRITICAL: Auto-cleaning stuck processing decks"
            sudo -u postgres psql -d review-platform -c "
                UPDATE pitch_decks 
                SET processing_status = 'failed', 
                    current_processing_task_id = NULL,
                    ai_analysis_results = COALESCE(ai_analysis_results, 
                        '{\"error\": \"Processing timeout - auto-cleanup\", \"cleanup_timestamp\": \"$(date -Iseconds)\"}')
                WHERE processing_status IN ('pending', 'processing', 'queued') 
                  AND created_at < NOW() - INTERVAL '30 minutes';
            " | tee -a "$LOG_FILE"
        fi
    fi
    
    # Check 4: Backend service health
    if ! systemctl is-active --quiet review-platform.service; then
        log "🚨 CRITICAL: Backend service is not running"
        sudo systemctl restart review-platform.service
        sleep 10
        log "🔄 Backend service restarted"
    fi
    
    log "=== Database Health Check Complete ==="
}

main "$@"