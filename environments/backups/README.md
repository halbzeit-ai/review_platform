# Environment Configuration Backups

This directory contains historical environment configuration files that were previously scattered throughout the project.

## Structure

```
backups/
├── backend/      # Historical backend .env files
├── frontend/     # Historical frontend .env files  
├── gpu/          # Historical GPU processing .env files
└── README.md
```

## Purpose

- Preserve configuration history for reference
- Avoid confusion with active configurations
- All active configs are now in parent `/environments/` directory
- Use `../deploy-environment.sh` to manage active configurations

## Migration Date

Files moved here on: $(date)
