# Centralized Environment Configuration

This directory contains all environment configurations for the entire platform in one place.

## Structure

```
environments/
├── .env.backend.development
├── .env.backend.production
├── .env.frontend.development
├── .env.frontend.production
├── .env.gpu.development
├── .env.gpu.production
├── deploy-environment.sh
└── README.md
```

## Usage

```bash
# Deploy development environment (default)
./environments/deploy-environment.sh development

# Deploy production environment
./environments/deploy-environment.sh production

# Check current environment
./environments/deploy-environment.sh status
```

## Benefits

1. **Single source of truth** - All environment configs in one place
2. **Easy comparison** - See differences between dev/prod easily
3. **Atomic deployment** - One command switches entire environment
4. **Version control** - All configs tracked together
5. **Easy maintenance** - Claude and developers look in one place

## File Naming Convention

Format: `.env.{component}.{environment}`
- `component`: backend, frontend, gpu
- `environment`: development, production, staging