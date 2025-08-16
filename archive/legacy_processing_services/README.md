# Legacy Processing Services Archive

**Date Archived**: August 16, 2025  
**Reason**: Architecture migration to single queue-based processing system

## Archived Files

### 1. `file_based_processing.py`
- **Purpose**: File-based GPU processing using shared filesystem communication
- **Status**: Legacy - replaced by queue-based HTTP processing
- **Issues**: 
  - Used deprecated `pitch_decks` table instead of `project_documents`
  - Only used in debug scripts, not active processing
  - File-based communication replaced by HTTP API

### 2. `direct_gpu_processing.py`
- **Purpose**: Direct SSH-based GPU processing
- **Status**: Legacy - replaced by HTTP-based processing
- **Issues**:
  - Used deprecated `PitchDeck` model instead of `ProjectDocument`
  - SSH communication replaced by HTTP API
  - Not integrated with queue system

### 3. `processing_worker.py`
- **Purpose**: Background worker service for processing queue tasks
- **Status**: Unused - queue processing handled differently
- **Issues**:
  - Worker pattern not used in current architecture
  - GPU HTTP client handles task processing directly
  - Added complexity without benefits

### 4. `gpu_http_client.py` *(RESTORED)*
- **Purpose**: HTTP client for GPU instance communication
- **Status**: **STILL IN USE** - moved back to active services
- **Note**: Initially thought to be legacy, but still actively imported by:
  - `app/api/config.py`
  - `app/api/dojo.py` (multiple locations)
  - `app/services/startup_classifier.py`
  - Various test files

### 5. `gpu_processing.py` *(NEWLY ARCHIVED)*
- **Purpose**: Legacy Datacrunch on-demand GPU instance processing
- **Status**: Legacy - replaced by persistent GPU server architecture
- **Issues**:
  - Uses deprecated on-demand GPU instances instead of persistent servers
  - File-based communication with completion markers
  - Only used in test scripts, not active processing
  - Replaced by queue-based HTTP communication

## Current Architecture

The platform now uses a **single, clean processing path**:

1. **Upload**: `documents_robust.py` → Queue system
2. **Processing**: 4-layer pipeline via queue tasks
3. **GPU Communication**: Direct HTTP calls from queue system + `gpu_http_client` for Dojo
4. **Results**: Stored via queue completion callbacks

## Migration Notes

- All active processing now goes through `processing_queue_manager`
- GPU processing uses 4 separate task methods in `gpu_processing/main.py`
- No alternative processing paths exist in the active codebase
- `gpu_http_client.py` still used for Dojo testing and GPU management

## Recovery

If any of these files are needed for reference, they are preserved here with their original functionality intact.