# Processing Worker System - Product Requirements Document

## Overview

The Processing Worker System is a robust, persistent task queue architecture designed to handle PDF processing tasks reliably across server restarts, crashes, and network failures. It replaces the fragile in-memory processing system with a PostgreSQL-backed queue that ensures no tasks are lost and provides comprehensive progress tracking.

## Problem Statement

### Original Issues
- **Lost Tasks During Restarts**: Server restarts caused processing tasks to disappear, leaving pitch decks in inconsistent states
- **No Progress Persistence**: Progress information was lost when services restarted
- **Race Conditions**: Multiple processing attempts for the same deck
- **No Recovery Mechanism**: Failed tasks remained stuck without automatic retry
- **Limited Observability**: No centralized logging accessible from all servers

### User Impact
- Startups experienced "quirky states" where decks appeared to be processing indefinitely
- GPs couldn't reliably track processing status
- Manual intervention required to fix stuck processing tasks
- Poor user experience with inconsistent processing states

## Solution Architecture

### Core Components

#### 1. PostgreSQL Database Schema
**Tables:**
- `processing_queue` - Main task queue with locking mechanisms
- `processing_progress` - Detailed progress tracking for each processing step  
- `processing_servers` - Server registration and heartbeat monitoring
- `task_dependencies` - Support for complex workflows with task dependencies

**PostgreSQL Functions:**
- `get_next_processing_task()` - Atomically retrieve and lock next available task
- `update_task_progress()` - Update progress with lock extension
- `complete_task()` - Mark task complete and update related records
- `cleanup_expired_locks()` - Recover abandoned tasks from crashed servers
- `retry_failed_task()` - Implement exponential backoff retry logic

#### 2. Processing Worker Service
**Location:** `backend/app/services/processing_worker.py`

**Key Features:**
- **Systemd Service**: Runs as `processing-worker.service` with auto-restart
- **Server Registration**: Registers with database and sends periodic heartbeats
- **Concurrent Processing**: Configurable max concurrent tasks (default: 3)
- **Graceful Shutdown**: Handles SIGTERM/SIGINT signals properly
- **Automatic Recovery**: Recovers abandoned tasks on startup
- **Shared Logging**: Logs to shared filesystem for cross-server access

#### 3. Robust API Endpoints
**Location:** `backend/app/api/documents_robust.py`

**Endpoints:**
- `POST /api/robust/documents/upload` - Upload with persistent queue
- `GET /api/robust/documents/processing-progress/{id}` - Multi-source progress tracking
- `GET /api/robust/documents/queue-stats` - Queue statistics (GP only)
- `POST /api/robust/documents/admin/recover-tasks` - Manual task recovery
- `POST /api/robust/documents/admin/retry-failed-tasks` - Retry failed tasks

## Technical Specifications

### Task Lifecycle

```
1. UPLOAD → Task created in 'queued' status
2. WORKER → Task atomically locked and status → 'processing'
3. PROGRESS → Regular progress updates with lock extension
4. GPU → Calls existing GPU HTTP endpoints (no changes needed)
5. COMPLETION → Task marked 'completed' or 'failed' with results
6. CLEANUP → Server lock released, related records updated
```

### Locking Mechanism
- **Atomic Locking**: PostgreSQL functions ensure only one worker gets each task
- **Lock Duration**: 30 minutes with automatic extension during processing
- **Heartbeat System**: Servers send heartbeats every 30 seconds
- **Lock Expiration**: Automatic cleanup of expired locks from crashed servers

### Retry Logic
- **Max Retries**: 3 attempts per task (configurable)
- **Exponential Backoff**: `5 minutes * 2^retry_count` delay between retries
- **Failure Tracking**: Detailed error messages and retry counters stored

### Progress Tracking
- **Multi-Level**: Both task-level and detailed step-level progress
- **Real-Time Updates**: Progress visible immediately via API endpoints
- **Fallback Sources**: Robust API checks queue → completed status → legacy GPU → database-only
- **Cross-Server Access**: Progress accessible from any server via shared database

## Deployment Architecture

### Server Environment Detection
The system automatically detects server environment:
- **dev_cpu** (65.108.32.143) - Development CPU server
- **prod_cpu** (65.108.32.168) - Production CPU server  
- **dev_gpu** (135.181.71.17) - Development GPU server
- **prod_gpu** (135.181.63.133) - Production GPU server

### Shared Filesystem Logging
**Log Locations:**
- Development: `/mnt/dev-shared/logs/processing_worker.log`
- Production: `/mnt/CPU-GPU/logs/processing_worker.log`

**Benefits:**
- GPU servers can access CPU processing logs
- CPU servers can access GPU processing logs
- Centralized debugging and monitoring

### Service Management
```bash
# Installation and management
/opt/review-platform/scripts/setup_processing_worker.sh install
/opt/review-platform/scripts/setup_processing_worker.sh start|stop|restart
/opt/review-platform/scripts/setup_processing_worker.sh status|logs

# Systemd integration
sudo systemctl status processing-worker.service
sudo journalctl -f -u processing-worker.service
```

## Integration Points

### Existing System Compatibility
- **GPU Server**: No changes required - continues to receive HTTP requests
- **Frontend**: Can use legacy endpoints while robust endpoints are being integrated
- **Database**: All existing pitch_decks records remain compatible
- **Storage**: Uses existing shared filesystem infrastructure

### API Integration Patterns

#### Legacy Upload Flow (Current)
```
Frontend → /api/documents/upload → Background Task → GPU HTTP → Results
```

#### Robust Upload Flow (New)
```
Frontend → /api/robust/documents/upload → PostgreSQL Queue → Worker → GPU HTTP → Results
```

### Progress Tracking Integration
```javascript
// Frontend can check multiple sources
const progress = await api.get(`/api/robust/documents/processing-progress/${deckId}`);
// Returns: { source: "queue_system|completed|legacy_gpu|database_only", progress: {...} }
```

## Operational Procedures

### Deployment Checklist
1. **Database Migration**: Run `scripts/deploy_processing_queue_migration.py`
2. **Service Installation**: Run `scripts/setup_processing_worker.sh install`
3. **Backend Restart**: Include robust API endpoints in main.py
4. **Service Start**: `systemctl start processing-worker.service`
5. **Verification**: Check queue stats and logs

### Monitoring and Maintenance

#### Health Checks
```bash
# Service status
sudo systemctl status processing-worker.service

# Queue statistics  
curl -H "Authorization: Bearer $GP_TOKEN" \
  "http://localhost:8000/api/robust/documents/queue-stats"

# Server registrations
psql -d review-platform -c "SELECT * FROM processing_servers WHERE status='active';"
```

#### Common Operations
```bash
# Recover abandoned tasks
curl -X POST -H "Authorization: Bearer $GP_TOKEN" \
  "http://localhost:8000/api/robust/documents/admin/recover-tasks"

# Retry failed tasks
curl -X POST -H "Authorization: Bearer $GP_TOKEN" \
  "http://localhost:8000/api/robust/documents/admin/retry-failed-tasks"

# Clean up old server registrations
psql -d review-platform -c "DELETE FROM processing_servers WHERE last_heartbeat < CURRENT_TIMESTAMP - INTERVAL '1 hour';"
```

### Troubleshooting

#### Common Issues
1. **Multiple Server Registrations**: Clean up stale servers with heartbeat cleanup
2. **Stuck Tasks**: Check lock expiration and run recovery procedures
3. **GPU Connection Issues**: Monitor shared logs for GPU HTTP client errors
4. **Database Connection**: Verify environment variables and PostgreSQL service
5. **🆕 Database Transaction Lockup**: System unresponsive, 30+ second API timeouts
6. **🆕 Connection Pool Exhaustion**: High connection count, "pool limit reached" errors

#### 🆕 Database Health Troubleshooting
```bash
# Quick health check - run immediately for any database issues
/opt/review-platform/scripts/database-health-monitor.sh

# Detailed connection analysis
sudo -u postgres psql -d review-platform -f scripts/db-connection-monitor.sql

# Check for stuck transactions (most common issue)
sudo -u postgres psql -d review-platform -c "
SELECT pid, state, query_start, NOW() - query_start as duration
FROM pg_stat_activity 
WHERE state = 'idle in transaction' AND datname = 'review-platform'
ORDER BY query_start;"

# Emergency transaction cleanup (use with caution)
sudo -u postgres psql -d review-platform -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle in transaction' 
  AND query_start < NOW() - INTERVAL '5 minutes';"

# Check processing queue for stuck decks
sudo -u postgres psql -d review-platform -c "
SELECT processing_status, COUNT(*), 
       COUNT(CASE WHEN created_at < NOW() - INTERVAL '30 minutes' THEN 1 END) as stuck
FROM pitch_decks 
WHERE processing_status IN ('pending', 'processing', 'queued')
GROUP BY processing_status;"

# Clean up stuck processing decks
sudo -u postgres psql -d review-platform -c "
UPDATE pitch_decks 
SET processing_status = 'failed', current_processing_task_id = NULL
WHERE processing_status IN ('pending', 'processing', 'queued') 
  AND created_at < NOW() - INTERVAL '30 minutes';"
```

#### Log Analysis
```bash
# Monitor real-time processing
tail -f /mnt/CPU-GPU/logs/processing_worker.log

# Monitor database health logs
tail -f /mnt/CPU-GPU/logs/database-health.log

# Search for errors across all services
grep -i "error\|failed" /mnt/CPU-GPU/logs/*.log

# Check specific task processing
grep "task.*123" /mnt/CPU-GPU/logs/processing_worker.log

# Look for database connection issues
grep -i "connection\|pool\|transaction" /mnt/CPU-GPU/logs/backend.log

# Check for queue processor issues
grep -i "queue_processor\|idle in transaction" /mnt/CPU-GPU/logs/backend.log
```

#### 🆕 Emergency Response Procedures

**Symptoms**: API timeouts, frontend login failures, slow response times

**Immediate Actions:**
1. **Run health monitor**: `/opt/review-platform/scripts/database-health-monitor.sh`
2. **Check service status**: `sudo systemctl status review-platform.service`
3. **Monitor active connections**: Check for high idle transaction counts
4. **Emergency cleanup**: Kill stuck transactions if >20 detected
5. **Service restart**: `sudo systemctl restart review-platform.service` if necessary

**Recovery Verification:**
```bash
# Test API responsiveness
curl -w "Time: %{time_total}s" "https://halbzeit.ai/api/health"

# Verify connection health
sudo -u postgres psql -d review-platform -c "
SELECT COUNT(*) as active_connections,
       COUNT(CASE WHEN state = 'idle in transaction' THEN 1 END) as idle_in_transaction
FROM pg_stat_activity WHERE datname = 'review-platform';"

# Check processing queue status
curl -H "Authorization: Bearer $GP_TOKEN" "https://halbzeit.ai/api/robust/documents/queue-stats"
```

## Performance Characteristics

### Scalability
- **Concurrent Tasks**: Configurable per server (default: 3)
- **Multiple Workers**: Can run multiple worker instances
- **Database Performance**: PostgreSQL functions optimized for concurrent access
- **Lock Contention**: Minimal due to atomic operations and row-level locking

### Resource Usage
- **Memory**: ~50MB per worker process
- **CPU**: Low overhead, spikes during GPU communication
- **Database**: Efficient indexes on status, priority, and timestamps
- **Storage**: Minimal - only task metadata stored

## Critical Production Issues & Solutions (Updated 2025-08-08)

### Database Transaction Management Crisis

#### **Issue**: Production Database Lockup (Severity: Critical)
On 2025-08-08, the production system experienced complete unresponsiveness due to database transaction management issues in the processing queue system.

**Root Cause Analysis:**
- **Transaction Leaks**: `queue_processor.py` created database sessions without proper commit/rollback
- **Long-running Operations**: Split processing (30+ seconds) kept transactions open indefinitely  
- **Exception Handling Gap**: Errors left transactions in "idle in transaction" state
- **Connection Pool Exhaustion**: 15+ stuck transactions blocked new connections → 30-second API timeouts

**Symptoms:**
- Backend API responses: 30+ seconds instead of milliseconds
- Frontend login timeouts: "Request aborted" errors
- Database showing multiple "idle in transaction" connections
- Connection pool exhaustion despite low actual load

#### **Immediate Fixes Applied** ✅

1. **Queue Processor Transaction Management** (`backend/app/services/queue_processor.py`)
   ```python
   # Before: Missing transaction management
   db = SessionLocal()
   # ... long operations ...
   finally:
       db.close()  # Never committed!
   
   # After: Explicit transaction management
   db = SessionLocal()
   try:
       task = processing_queue_manager.get_next_task(db)
       if not task:
           db.commit()  # Commit even empty operations
           return
       
       # ... process task ...
       db.commit()  # Commit success
   except Exception as e:
       db.rollback()  # Rollback on error
   finally:
       db.close()
   ```

2. **Database Connection Pool Configuration** (`backend/app/db/database.py`)
   ```python
   engine = create_engine(
       settings.DATABASE_URL,
       pool_size=10,           # Increased from default 5
       max_overflow=20,        # Additional connections
       pool_timeout=30,        # Timeout when getting connection
       pool_recycle=3600,      # Recycle connections hourly
       pool_pre_ping=True,     # Validate connections
   )
   ```

3. **Automated Cleanup & Recovery** (`scripts/database-health-monitor.sh`)
   - Runs every 5 minutes via cron
   - Detects stuck transactions (>2 minutes)
   - Auto-kills transactions stuck >5 minutes
   - Auto-restarts backend if >10 transactions cleaned
   - Monitors processing queue health

#### **Prevention Systems** 🛡️

**Automated Monitoring & Recovery:**
- **Health Monitor**: `scripts/database-health-monitor.sh` (cron: */5 * * * *)
- **Connection Monitoring**: `scripts/db-connection-monitor.sql` (manual diagnostics)
- **Alert Thresholds**: 
  - Warning: >10 idle transactions
  - Critical: >20 idle transactions (auto-cleanup)
  - Processing: >15 stuck decks (auto-reset to failed)

**Operational Procedures:**
```bash
# Real-time health check
/opt/review-platform/scripts/database-health-monitor.sh

# Manual diagnostics
sudo -u postgres psql -d review-platform -f scripts/db-connection-monitor.sql

# Emergency cleanup (if needed)
sudo -u postgres psql -d review-platform -c "
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle in transaction' 
  AND query_start < NOW() - INTERVAL '5 minutes';"
```

#### **Lessons Learned** 📚

1. **Transaction Discipline**: Every database session MUST have explicit commit/rollback
2. **Connection Pool Sizing**: Default settings insufficient for concurrent processing
3. **Monitoring Essential**: Problems compound quickly without early detection
4. **Graceful Degradation**: System should fail gracefully, not lock up completely
5. **Documentation Critical**: Team needs runbooks for rapid incident response

#### **Future Improvements**

**Technical Debt:**
- Audit ALL database session usage for proper transaction management
- Implement connection pool metrics and alerting
- Add circuit breaker pattern for GPU communication failures
- Consider read-only replicas for progress polling to reduce primary load

**Operational Improvements:**
- Dashboard for real-time database health metrics
- Automated alerts via Slack/email for critical thresholds
- Runbook automation for common recovery procedures
- Load testing to validate connection pool sizing

## Future Enhancements

### Planned Improvements
1. **Transaction Audit**: Complete audit of all database session usage patterns
2. **Circuit Breakers**: Implement circuit breaker pattern for external service calls
3. **Connection Pool Metrics**: Real-time monitoring of database connection health
4. **Priority Queues**: Enhanced priority handling for urgent tasks
5. **Workflow Support**: Complex multi-step processing workflows
6. **Metrics Integration**: Prometheus/Grafana monitoring with database health metrics
7. **Auto-scaling**: Dynamic worker scaling based on queue depth

### Frontend Integration
1. **Progressive Enhancement**: Gradually migrate to robust endpoints
2. **Real-time Updates**: WebSocket integration for live progress
3. **Admin Dashboard**: Queue management interface for GPs
4. **Error Recovery**: User-friendly retry mechanisms

## Security Considerations

### Access Control
- **Admin Endpoints**: GP role required for queue management
- **Progress Access**: User can only access their own deck progress
- **Service Authentication**: Systemd service runs with restricted permissions

### Data Protection
- **Sensitive Information**: No sensitive data stored in queue (only metadata)
- **Audit Trail**: Complete processing history maintained
- **Error Handling**: Sanitized error messages in user-facing APIs

## Testing Strategy

### Unit Tests
- ProcessingQueueManager methods
- PostgreSQL function testing
- Task lifecycle validation

### Integration Tests
- End-to-end upload processing
- Server restart recovery scenarios
- Multi-server coordination

### Load Testing
- High-volume upload scenarios
- Concurrent processing limits
- Database performance under load

## Migration Strategy

### Phase 1: Parallel Operation (Current)
- Robust system deployed alongside legacy system
- Legacy endpoints continue to work
- Testing and validation in production

### Phase 2: Gradual Migration
- Frontend updates to use robust endpoints
- Legacy system remains as fallback
- Monitoring and performance validation

### Phase 3: Full Migration
- All uploads use robust queue system
- Legacy processing endpoints deprecated
- Enhanced monitoring and alerting

## Success Metrics

### Reliability Metrics
- **Zero Lost Tasks**: No tasks lost during server restarts
- **Recovery Time**: < 1 minute to recover from server failures
- **Processing Success Rate**: > 99% task completion rate

### Performance Metrics
- **Queue Processing Time**: Average time from queue to GPU
- **Progress Update Frequency**: Real-time progress updates
- **Server Utilization**: Optimal concurrent task distribution

### User Experience Metrics
- **Processing Transparency**: Users always know current status
- **Error Recovery**: Clear error messages and retry options
- **System Reliability**: Consistent processing behavior

---

## Implementation Details

### Environment Configuration
- **Development**: Uses `dev_cpu` and `dev_gpu` servers with `/mnt/dev-shared/` storage
- **Production**: Uses `prod_cpu` and `prod_gpu` servers with `/mnt/CPU-GPU/` storage
- **Database**: PostgreSQL with environment-specific credentials

### Code Locations
- **Queue Manager**: `backend/app/services/processing_queue.py`
- **Worker Service**: `backend/app/services/processing_worker.py`
- **Robust API**: `backend/app/api/documents_robust.py`
- **Database Migration**: `migrations/create_processing_queue_system.sql`
- **Service Scripts**: `scripts/setup_processing_worker.sh`

### Dependencies
- **PostgreSQL**: Primary database with JSONB support
- **SQLAlchemy**: ORM and database abstraction
- **asyncio**: Asynchronous task processing
- **systemd**: Service management and auto-restart
- **Shared Filesystem**: Cross-server file and log access

This robust processing queue system transforms the fragile, restart-sensitive processing into a resilient, observable, and maintainable architecture that scales with the platform's growth.