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

#### Log Analysis
```bash
# Monitor real-time processing
tail -f /mnt/CPU-GPU/logs/processing_worker.log

# Search for errors across all services
grep -i "error\|failed" /mnt/CPU-GPU/logs/*.log

# Check specific task processing
grep "task.*123" /mnt/CPU-GPU/logs/processing_worker.log
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

## Future Enhancements

### Planned Improvements
1. **Concurrency Optimization**: Fix duplicate task processing issue
2. **Priority Queues**: Enhanced priority handling for urgent tasks
3. **Workflow Support**: Complex multi-step processing workflows
4. **Metrics Integration**: Prometheus/Grafana monitoring
5. **Auto-scaling**: Dynamic worker scaling based on queue depth

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