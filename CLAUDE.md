# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a startup review platform with a Python FastAPI backend and React frontend. The platform allows:
- Startups to register, upload pitch decks (PDFs), and receive AI-generated reviews
- GPs (General Partners) to review, modify, and approve reviews
- A Q&A system between startups and GPs
- S3 integration for file storage and AI processing triggers

## Architecture

### Backend (FastAPI)
- **Location**: `backend/` directory
- **Main entry**: `backend/app/main.py`
- **Structure**:
  - `app/api/`: API endpoints (auth, decks, reviews, questions, documents)
  - `app/core/`: Configuration and storage utilities
  - `app/db/`: Database models and connection (SQLAlchemy)
  - `app/services/`: Business logic services
  - `app/processing/`: AI processing components

### Frontend (React)
- **Location**: `frontend/` directory
- **Tech stack**: React 18, Material-UI, React Router
- **Structure**:
  - `src/pages/`: Main application pages (Login, Register, Review, Dashboards)
  - `src/components/`: Reusable UI components
  - `src/services/`: API communication layer
  - `src/utils/`: Utility functions (theme, etc.)

### Database
- SQLite for development (`backend/sql_app.db`)
- PostgreSQL for production (as indicated in PRD)

## Development Commands

### Quick Service Management (Recommended for Claude)
```bash
# Start/stop services
./dev-services.sh start      # Start both frontend and backend
./dev-services.sh stop       # Stop both services
./dev-services.sh restart    # Restart both services
./dev-services.sh status     # Check service health
./dev-services.sh logs       # Show logs for both services
./dev-services.sh logs backend  # Show only backend logs
```

### Database Operations (For Claude)
```bash
# Run database migrations with elevated privileges
./claude-dev-helper.sh migrate migrations/filename.sql

# Check database status
./claude-dev-helper.sh db-check              # Test connection and show info
./claude-dev-helper.sh migrate-check         # Check if zip_filename column exists

# Manual database access (if needed)
sudo -u postgres psql review-platform
```

### Development Helper Commands
```bash
# Comprehensive development test
./claude-dev-helper.sh quick-test

# Service management via helper
./claude-dev-helper.sh services start
./claude-dev-helper.sh services status

# Git status summary
./claude-dev-helper.sh git-status
```

### Manual Commands (Fallback if scripts don't work)

#### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
```

#### Frontend
```bash
cd frontend
npm install
DANGEROUSLY_DISABLE_HOST_CHECK=true npm start  # Development server
npm run build    # Production build
npm test         # Run tests
```

#### Type Checking
```bash
cd backend
mypy .
```

## Important Development Rules

The `rules/python.md` file contains comprehensive Python development guidelines including:
- Type safety with strict mypy settings
- Functional programming patterns
- Domain-driven design architecture
- Result types for error handling
- Comprehensive testing strategies

Key principles:
- Always use type hints
- Prefer pure functions and immutable data
- Use dataclasses with `frozen=True`
- Follow domain-driven design patterns
- Implement proper error handling with custom exceptions

## Key Integration Points

- **Shared Filesystem Storage**: Files stored on Datacrunch.io NFS shared filesystem
- **AI Processing**: On-demand GPU instances process uploaded PDFs via shared storage
- **Email Notifications**: System sends emails for review workflows (planned)
- **Authentication**: JWT-based auth system for both user types

## File Storage Flow (Current Implementation)

1. Startup uploads PDF → Shared NFS filesystem (`/mnt/shared/uploads/`)
2. Background task triggers AI processing on on-demand GPU instance
3. AI generates review JSON → stored in shared filesystem (`/mnt/shared/results/`)
4. Review data linked in SQLite database
5. Email notifications sent to relevant parties (planned)

## development setup
- we have a local development machine running nixos
- in the cloud at datacrunch.io, we have a production server CPU and a GPU instance for running LLMs
- the GPU and the CPU communicate via http
- git: claude should always add and commit, human should always push 
- the GPU and the CPU have access to the git repo, i.e. usually no copying between these two is necessary.

## Environment Configuration

The project uses a consistent naming scheme for environment variables to separate service types from environments:

### Server Environment Variables
- `BACKEND_DEVELOPMENT=http://65.108.32.143:8000` - Backend server in development environment
- `BACKEND_PRODUCTION=http://65.108.32.168:8000` - Backend server in production environment  
- `GPU_DEVELOPMENT=135.181.71.17` - GPU server in development environment
- `GPU_PRODUCTION=135.181.63.133` - GPU server in production environment

### Naming Convention
**Pattern**: `{SERVICE_TYPE}_{ENVIRONMENT}`
- **Service Types**: BACKEND, GPU, FRONTEND (if needed)
- **Environments**: DEVELOPMENT, PRODUCTION, STAGING (if added)

### Environment-Aware Configuration
- Services automatically select the correct server based on the `ENVIRONMENT` variable
- GPU HTTP client chooses GPU_DEVELOPMENT for development, GPU_PRODUCTION for production
- Backend services use BACKEND_DEVELOPMENT for callbacks in development environment
- Maintains backward compatibility with legacy variables (GPU_INSTANCE_HOST, PRODUCTION_SERVER_URL)

### File Locations
- Backend environment: `backend/.env`
- GPU processing environment: `gpu_processing/.env.development`
- Configuration classes: `backend/app/core/config.py`

## Development Memories
- please do remember that you are on a development machine, the UUIDs, filepaths and SQL databases I paste are from the production machine