# Development Environment Setup Guide

This guide completes the development environment setup including shared filesystems and GPU server configuration.

## Current Status

✅ **Completed:**
- Git access setup on development server (65.108.32.143)
- PostgreSQL installation and configuration
- Production database schema export (26 tables)
- Database schema import to development and staging databases
- Backend service running with development database connection
- Environment configuration system with dev/staging/production support

❗ **Still Needed:**
- Shared NFS filesystem mounting between development CPU and GPU
- Development GPU server (135.181.71.17) configuration
- File transfer capabilities between production and development
- Complete functional testing of GPU processing workflow

## Server Configuration

```bash
# Server IP addresses from Datacrunch screenshot
PRODUCTION_CPU="65.108.32.168"    # happy-heart-shines-fn-01
PRODUCTION_GPU="135.181.63.133"   # clean-hand-rings-fn-01
DEVELOPMENT_CPU="65.108.32.143"   # dev-cpu-fn-01
DEVELOPMENT_GPU="135.181.71.17"   # dev-gpu-fn-01
```

## Filesystem Structure

Based on CLAUDE.md and production setup:
- Production shared filesystem: `/mnt/CPU-GPU/` (mounted via Datacrunch NFS)
- Development shared filesystem: `/mnt/dev-CPU-GPU/` (between dev CPU and GPU)
- Production filesystem access: `/mnt/shared-production/` (read-only for file transfers)

File flow:
- Uploads: `{mount}/uploads/`
- Results: `{mount}/results/`
- Cache: `{mount}/cache/`

## Next Steps to Execute on Development Server

### 1. Complete Shared Filesystem Setup

Run the shared filesystem setup script:
```bash
cd /opt/review-platform-dev
./scripts/setup-shared-filesystems.sh
```

### 2. Configure Development GPU Server

SSH to development GPU and setup processing environment:
```bash
./scripts/setup-development-gpu.sh
```

### 3. Test Complete Workflow

Verify end-to-end functionality:
```bash
./scripts/test-development-workflow.sh
```

## Key Environment Files

- `environments/development.env` - Development server configuration
- `environments/production.env` - Production reference (do not modify)
- `backend/.env` - Local backend environment (created during setup)

## Database Connections

- **Development**: `postgresql://dev_user:dev_password@localhost:5432/review_dev`
- **Staging**: `postgresql://staging_user:staging_password@localhost:5432/review_staging`
- **Production**: `postgresql://review_user:review_password@65.108.32.168:5432/review-platform`

## Commands Reference

### Start Development Services
```bash
# Backend (on development CPU)
cd /opt/review-platform-dev/backend
source ../venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Frontend (on development CPU)
cd /opt/review-platform-dev/frontend
npm start

# GPU Processing Service (on development GPU)
cd /opt/review-platform-dev/gpu_processing
python3 main.py --mode=development
```

### Test Database Connection
```bash
# Test development database
PGPASSWORD=dev_password psql -h localhost -U dev_user -d review_dev -c "SELECT COUNT(*) FROM startups;"

# Test staging database
PGPASSWORD=staging_password psql -h localhost -U staging_user -d review_staging -c "SELECT COUNT(*) FROM startups;"
```

## Files Created During Setup

- `schemas/production_schema.sql` - Complete production database schema
- `scripts/setup-shared-filesystems.sh` - NFS mounting script
- `scripts/setup-development-gpu.sh` - GPU server configuration
- `scripts/test-development-workflow.sh` - End-to-end testing
- `environments/development.env` - Development environment variables

## Troubleshooting

### Common Issues
1. **SSH Key Access**: Ensure SSH keys are properly configured for GitHub access
2. **Database Permissions**: Use superuser approach if permission errors occur
3. **Port Conflicts**: Development uses port 3000 (frontend) and 8000 (backend)
4. **Filesystem Mounts**: Verify NFS services are running on both CPU and GPU servers

### Support Scripts
- `scripts/diagnose-development-environment.sh` - System health check
- `scripts/sync-with-production.sh` - Data synchronization utilities

## Security Notes

- Development databases use simple passwords for convenience
- Production filesystem mounted read-only for safety
- All secrets stored in environment files (not committed)
- SSH keys managed per server for security isolation