# Scripts Directory

This directory contains maintenance and troubleshooting scripts for the Review Platform deployment.

## Available Scripts

### Production Maintenance Scripts

#### `fix_database.sh`
Fixes database schema issues, particularly the missing `file_path` column error.
```bash
# Run on production server
./scripts/fix_database.sh
```

#### `fix_upload_size.sh`
Updates nginx configuration to allow 50MB file uploads.
```bash
# Run on production server
./scripts/fix_upload_size.sh
```

#### `remote_setup.sh`
Initial server setup script for preparing a fresh Datacrunch instance.
```bash
# Run on fresh instance
./scripts/remote_setup.sh
```

### Deployment Scripts

#### `deploy/deploy_app.sh`
Main deployment script that sets up the entire application stack.
```bash
# Run after uploading code
./deploy/deploy_app.sh
```

## Usage

1. **For production fixes**: Run the specific fix script directly on the server
2. **For new deployments**: Use `remote_setup.sh` first, then `deploy/deploy_app.sh`
3. **For troubleshooting**: Check logs and use appropriate fix script

## Script Categories

- **Database**: `fix_database.sh`
- **Web Server**: `fix_upload_size.sh`
- **Infrastructure**: `remote_setup.sh`
- **Deployment**: `deploy/deploy_app.sh`

All scripts are designed to be run on the production server with proper error handling and status reporting.