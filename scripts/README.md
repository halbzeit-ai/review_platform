# Scripts Directory

This directory contains helper scripts for managing the HALBZEIT AI Review Platform.

## Usage

Run scripts from the project root directory:

```bash
cd /opt/review-platform
./scripts/script_name.py   # Python scripts
./scripts/script_name.sh   # Bash scripts
```

## Database Management

### `reset_database.py` 🗑️
**Purpose:** Completely wipes and recreates the database with fresh schema  
**Use case:** Clean slate for testing, removes all users/data  
**Safety:** Creates automatic backup before deletion  
**Warning:** Requires typing 'DELETE' to confirm - destructive operation  

```bash
./scripts/reset_database.py
```

## Volume Management

### `cleanup_volumes_simple.py` 🧹
**Purpose:** Clean up orphaned volume attachments using standard library only  
**Use case:** Fix "Volume limit exceeded" errors by detaching volumes from deleted instances  
**Features:** No virtual environment required, bypasses Cloudflare protection  

```bash
./scripts/cleanup_volumes_simple.py
```

### `check_all_volumes.py` 📊
**Purpose:** Comprehensive analysis of all volumes in Datacrunch account  
**Use case:** Troubleshoot quota issues, identify orphaned attachments  
**Output:** Detailed report of volume usage and attachment status  

```bash
./scripts/check_all_volumes.py
```

### `cleanup_orphaned_volumes.py` 🔧
**Purpose:** Clean up orphaned attachments using backend API client  
**Use case:** Production cleanup with full application context  
**Requirements:** Virtual environment and backend imports  

```bash
./scripts/cleanup_orphaned_volumes.py
```

## GPU Processing & Testing

### `test_gpu_processing.py` 🧪
**Purpose:** Test GPU processing configuration and API connectivity  
**Use case:** Verify Datacrunch API, shared filesystem, and instance creation  
**Features:** Configuration validation, optional instance creation test  

```bash
./scripts/test_gpu_processing.py
```

### `test_gpu_simple.sh` ⚡
**Purpose:** Quick GPU instance creation test  
**Use case:** Fast verification of GPU deployment without full setup  

```bash
./scripts/test_gpu_simple.sh
```

### `test_gpu_local.sh` 🏠
**Purpose:** Test GPU processing with local AI models  
**Use case:** Development testing without cloud dependencies  

```bash
./scripts/test_gpu_local.sh
```

### `test_nfs_gpu.sh` 💾
**Purpose:** Test NFS shared filesystem access from GPU instances  
**Use case:** Verify file sharing between CPU and GPU instances  

```bash
./scripts/test_nfs_gpu.sh
```

### `test_gpu_processing_local.sh` 🔬
**Purpose:** Local GPU processing pipeline test  
**Use case:** End-to-end testing of AI analysis workflow  

```bash
./scripts/test_gpu_processing_local.sh
```

## System Setup & Configuration

### `setup_shared_filesystem.sh` 🔗
**Purpose:** Initialize and mount NFS shared filesystem  
**Use case:** First-time setup of shared storage for AI processing  

```bash
./scripts/setup_shared_filesystem.sh
```

### `manage_shared_filesystem.sh` 📁
**Purpose:** Manage shared filesystem operations (mount/unmount/status)  
**Use case:** Day-to-day filesystem management  

```bash
./scripts/manage_shared_filesystem.sh
```

### `update_filesystem_config.sh` ⚙️
**Purpose:** Update shared filesystem configuration  
**Use case:** Modify NFS settings or mount points  

```bash
./scripts/update_filesystem_config.sh
```

### `fix_database.sh` 🛠️
**Purpose:** Fix database schema issues (legacy)  
**Use case:** Repair database column problems  

```bash
./scripts/fix_database.sh
```

### `fix_upload_size.sh` 📤
**Purpose:** Configure nginx to allow large file uploads  
**Use case:** Fix PDF upload failures due to size limits  

```bash
./scripts/fix_upload_size.sh
```

## SSH & Remote Management

### `get_ssh_keys.sh` 🔑
**Purpose:** Retrieve SSH key IDs from Datacrunch account  
**Use case:** Get SSH key identifiers for instance creation  

```bash
./scripts/get_ssh_keys.sh
```

### `configure_ssh_manual.sh` 🖥️
**Purpose:** Manual SSH configuration for GPU instances  
**Use case:** Set up SSH access to remote instances  

```bash
./scripts/configure_ssh_manual.sh
```

### `remote_setup.sh` 🌐
**Purpose:** Remote instance setup and configuration  
**Use case:** Initialize new instances with required software  

```bash
./scripts/remote_setup.sh
```

## Code Deployment

### `deploy_gpu_code.sh` 🚀
**Purpose:** Deploy AI processing code to GPU instances  
**Use case:** Update GPU instances with latest AI analysis code  

```bash
./scripts/deploy_gpu_code.sh
```

### `sync_gpu_code.sh` 🔄
**Purpose:** Synchronize code between local and remote instances  
**Use case:** Keep GPU processing code in sync  

```bash
./scripts/sync_gpu_code.sh
```

## Status Checking

### `check_gpu_results.sh` 📋
**Purpose:** Check status and results of GPU processing jobs  
**Use case:** Monitor AI analysis progress and results  

```bash
./scripts/check_gpu_results.sh
```

## Script Development Guidelines

When adding new scripts to this directory:

1. **Naming Convention:**
   - Use snake_case for filenames
   - Add `.py` for Python scripts, `.sh` for Bash scripts
   - Use descriptive names indicating purpose

2. **Permissions:**
   - Make scripts executable: `chmod +x scripts/your_script.py`
   - Add proper shebang: `#!/usr/bin/env python3` or `#!/bin/bash`

3. **Documentation:**
   - Update this README.md with script description
   - Include usage examples and purpose
   - Add safety warnings for destructive operations

4. **Structure:**
   - Add scripts to appropriate category section
   - Include emoji for visual categorization
   - Specify requirements (virtual env, permissions, etc.)

5. **Safety:**
   - Add confirmation prompts for destructive operations
   - Create backups before making changes
   - Include error handling and rollback options

---

**Note:** Always run scripts from the project root directory (`/opt/review-platform`) to ensure proper path resolution and database access.