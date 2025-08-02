# Environment Configuration History

This directory contains timestamped backups of environment configuration files created during deployments.

## Structure

```
history/
├── backend.env.backup.YYYYMMDD_HHMMSS    # Backend environment backups
├── frontend.env.backup.YYYYMMDD_HHMMSS   # Frontend environment backups  
├── gpu.env.backup.YYYYMMDD_HHMMSS        # GPU environment backups
└── README.md
```

## Automatic Management

- **Created**: Automatically when deploying environments via `../deploy-environment.sh`
- **Retention**: Keeps last 10 backups per component (configurable via `MAX_BACKUPS`)
- **Cleanup**: Old backups automatically removed to prevent disk space issues

## Usage

### View recent backups
```bash
ls -lt history/
```

### Restore from backup
```bash
# Example: Restore backend from specific backup
cp history/backend.env.backup.20250802_075104 ../backend/.env
```

### Manual cleanup
```bash
# Remove all backups older than 30 days
find history/ -name "*.backup.*" -mtime +30 -delete
```

## Configuration

Edit `MAX_BACKUPS` in `../deploy-environment.sh` to change retention policy.