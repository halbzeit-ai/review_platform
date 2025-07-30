# Move Claude to Development Server

This guide helps you continue the setup process on the development server where the actual configuration needs to happen.

## Quick Start on Development Server

1. **SSH to Development Server:**
   ```bash
   ssh root@65.108.32.143
   ```

2. **Navigate to Project Directory:**
   ```bash
   cd /opt/review-platform-dev
   ```

3. **Pull Latest Changes:**
   ```bash
   git pull origin main
   ```

4. **Continue with Shared Filesystem Setup:**
   ```bash
   ./scripts/setup-shared-filesystems.sh
   ```

## Current Status

✅ **Already Completed:**
- Git access and repository cloning on development server
- PostgreSQL installation and database setup
- Production schema export and import to development
- Backend service configuration and startup
- Environment configuration files created
- Database schemas synchronized (26 tables imported)

❗ **Next Steps to Complete:**
- Setup shared NFS filesystem between CPU (65.108.32.143) and GPU (135.181.71.17)  
- Configure development GPU server for AI processing
- Test complete workflow including GPU processing capabilities
- Verify file synchronization and processing pipeline

## Key Files Ready for Execution

All these scripts are now available in `/opt/review-platform-dev/scripts/`:

- `setup-shared-filesystems.sh` - Mount NFS between CPU and GPU
- `setup-development-gpu.sh` - Configure GPU server for AI processing  
- `test-development-workflow.sh` - End-to-end testing

## Context for Claude on Development Server

When you continue on the development server, you have:

- **Servers Available:**
  - Development CPU: 65.108.32.143 (current server)
  - Development GPU: 135.181.71.17 (needs configuration)
  - Production CPU: 65.108.32.168 (reference/data source)
  - Production GPU: 135.181.63.133 (reference)

- **Database Access:**
  - Development: `postgresql://dev_user:dev_password@localhost:5432/review_dev`
  - Staging: `postgresql://staging_user:staging_password@localhost:5432/review_staging`

- **Filesystem Structure (to be mounted):**
  - `/mnt/dev-CPU-GPU/` - Shared between development CPU and GPU
  - `/mnt/shared-production/` - Read-only access to production files

- **Todo Status:**
  - ✅ Database setup and schema synchronization  
  - ✅ Backend service configuration
  - 🚧 Shared filesystem mounting (in progress)
  - ⏳ GPU server configuration (pending)
  - ⏳ End-to-end workflow testing (pending)

## What to Tell Claude

When you start Claude on the development server, you can say:

> "I'm now on the development server (65.108.32.143). We've completed the database setup and backend configuration. Now we need to complete the shared filesystem setup and GPU server configuration. Please continue with the filesystem mounting by running the setup scripts in the scripts/ directory."

The setup process is well-documented and the scripts are ready to execute. Claude can continue immediately with the shared filesystem setup without needing to recreate any work.