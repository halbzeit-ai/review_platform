# ARCHIVED: On-Demand GPU Instance Spawning Implementation

**Date Archived:** 2025-07-14
**Reason:** Switching to hibernation-based approach due to DataCrunch.io instance limits

## Complete Implementation Inventory

### Core Infrastructure Files

1. **`backend/app/core/datacrunch.py`** - Primary DataCrunch.io API client
   - OAuth2 authentication with token refresh
   - Instance deployment and management (create, get, delete)
   - Volume operations (create, attach, detach, cleanup)
   - Startup script creation and management
   - Instance monitoring and status checking
   - Orphaned volume cleanup functionality

2. **`backend/app/services/gpu_processing.py`** - Main orchestration service
   - Complete GPU instance lifecycle management
   - Automatic instance creation with shared filesystem mounting
   - Processing status tracking and monitoring
   - Error handling and cleanup
   - Integration with database for status updates
   - Background processing support

3. **`backend/app/core/volume_storage.py`** - Shared filesystem storage management
   - File upload and retrieval from shared NFS volume
   - Processing marker creation and cleanup
   - Results storage and retrieval
   - Directory structure management

### GPU Processing Code

4. **`gpu_processing/main.py`** - Main entry point for GPU processing
5. **`gpu_processing/utils/pitch_deck_analyzer.py`** - Core AI analysis engine
6. **`gpu_processing/setup_ai_environment.py`** - AI environment setup

### Configuration

7. **Environment Variables in `backend/app/core/config.py`:**
   - `DATACRUNCH_CLIENT_ID`: OAuth2 client ID
   - `DATACRUNCH_CLIENT_SECRET`: OAuth2 client secret
   - `DATACRUNCH_SHARED_FILESYSTEM_ID`: Shared NFS filesystem ID
   - `DATACRUNCH_SSH_KEY_IDS`: SSH keys for GPU instances
   - `SHARED_FILESYSTEM_MOUNT_PATH`: Mount path for shared storage

### Deployment & Management Scripts

8. **`scripts/deploy_gpu_code.sh`** - Deploys GPU processing code to shared filesystem
9. **`scripts/cleanup_orphaned_volumes.py`** - Cleans up orphaned volume attachments
10. **Various test and monitoring scripts**

### AI Models Used

- **gemma3:12b**: Vision and text analysis
- **phi4:latest**: Scoring and scientific hypothesis extraction

### Processing Workflow

1. File Upload → Shared NFS volume
2. Background task triggers GPU processing
3. Creates startup script with AI environment setup
4. Deploys GPU instance (`1RTX6000ADA.10V`) with shared volume
5. Instance processes PDF with AI models
6. Results saved to shared volume
7. Instance auto-shuts down and cleanup

### Known Issues Leading to Hibernation Approach

- ❌ Volume attachment quota limits
- ❌ API rate limiting challenges  
- ❌ Instance creation failures due to account limits
- ❌ Cost inefficiency from constant spawn/destroy cycles

## Files to Preserve

All implementation files are preserved in the codebase under:
- `backend/app/core/datacrunch.py`
- `backend/app/services/gpu_processing.py`
- `backend/app/core/volume_storage.py`
- `gpu_processing/` directory
- `scripts/` directory

## Reactivation Notes

To reactivate this approach:
1. Ensure DataCrunch.io quotas are sufficient
2. Update instance types if needed
3. Review API rate limits
4. Test deployment scripts
5. Verify AI model availability

This implementation is complete and production-ready, archived for potential future use.