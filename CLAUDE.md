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
- **Development**: PostgreSQL database `review_dev`
- **Production**: PostgreSQL database `review-platform` 
- **Legacy**: SQLite for development (`backend/sql_app.db`) - deprecated

## Development Commands

### Quick Service Management (Recommended for Claude)
```bash
# Use the improved version with smart features
./dev-services-improved.sh start      # Smart start - only starts what's needed
./dev-services-improved.sh stop       # Stop services by port (precise)
./dev-services-improved.sh restart    # Restart all services
./dev-services-improved.sh restart backend   # Restart only backend
./dev-services-improved.sh restart frontend  # Restart only frontend
./dev-services-improved.sh status     # Check service health and auto-reload
./dev-services-improved.sh logs       # Show logs for both services
./dev-services-improved.sh logs backend  # Show only backend logs
./dev-services-improved.sh reload-check  # Verify auto-reload is enabled

# Key advantages of improved version:
# - Uses correct port 8000 for backend (not 5001)
# - Kills processes by port, not by name (precise)
# - Checks if backend has --reload flag
# - Won't restart services unnecessarily
# - Shows external IP (65.108.32.143) for remote access
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
# IMPORTANT: Use port 8000, not 5001!
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
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

### CRITICAL: Content Creation Rules
- **NEVER** create, generate, or invent prompts, questions, templates, or any content unless EXPLICITLY asked by a human
- **ALWAYS** search for existing content first - check database, migration files, backups, and git history
- If content appears to be missing, inform the user and ask where to find it rather than creating new content
- This applies to ALL content types: prompts, questions, templates, analysis criteria, etc.

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

## Development Setup
- Local development machine running NixOS
- Cloud infrastructure at Datacrunch.io:
  - **Production CPU server**: 65.108.32.168 (nginx, systemd services)
  - **GPU instance**: 135.181.63.133 (AI processing)
- GPU and CPU communicate via HTTP
- Git workflow: Claude commits, human pushes
- Both servers have git repo access (no file copying needed)

## Production Infrastructure

### Web Server: Nginx + Systemd Services
Production uses **nginx** to serve frontend static files and **systemd** for service management:

**Key Production Services:**
```bash
# Backend API service
sudo systemctl status review-platform.service
sudo systemctl restart review-platform.service
sudo journalctl -f -u review-platform.service

# GPU processing service  
sudo systemctl status gpu-http-server.service
sudo systemctl restart gpu-http-server.service
sudo journalctl -f -u gpu-http-server.service
```

**Critical: Systemd Environment Configuration**
Systemd services require explicit `EnvironmentFile=` directive to load `.env` files:
```ini
[Service]
EnvironmentFile=/opt/review-platform/backend/.env
```
Without this, services use default/cached environment variables!

### Frontend Deployment: Zero-Downtime with Nginx
Production frontend uses nginx-compatible atomic deployment via symlinks:

```bash
# Zero-downtime deployment script
/opt/review-platform/scripts/build-frontend.sh production

# Process:
# 1. Build new version in timestamped directory (current stays online)
# 2. Atomic symlink switch: ln -sfn build_new build (no 500 errors)
# 3. Nginx serves from symlink target with zero downtime
# 4. Automatic backup and rollback capability
```

**Rollback if needed:**
```bash
ln -sfn build_backup build
```

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

## Template Management System

### Overview
The platform includes a comprehensive template management system for healthcare sector analysis templates. Templates consist of chapters containing questions with scoring criteria.

### Database Structure
```
analysis_templates (Template metadata)
├── template_chapters (Chapters within templates)
│   └── chapter_questions (Questions within chapters)
└── gp_template_customizations (GP-specific template versions)
```

### Key Database Fields
- **template_chapters**: Use `template_id` (NOT `analysis_template_id`) for the required foreign key
- **chapter_questions**: Requires both `chapter_id` AND `question_id` (NOT NULL)
- Always verify actual column names before writing SQL queries

### Template Edit Workflow
1. **Edit Mode**: Updates complete template structure (name, chapters, questions)
2. **API Endpoint**: `/api/healthcare-templates/templates/{id}/complete`
3. **Frontend**: `updateTemplateComplete()` in `services/api.js`
4. **Atomic Operations**: Delete all existing chapters/questions, then insert new ones

## Dojo Extraction Testing Data Structure

### How Step 2 and Step 3 Cache Results

#### Step 2: Visual Analysis Cache
Visual analysis results are stored in the `visual_analysis_cache` table:
```sql
CREATE TABLE visual_analysis_cache (
    id SERIAL PRIMARY KEY,
    pitch_deck_id INTEGER NOT NULL REFERENCES pitch_decks(id),
    analysis_result_json TEXT NOT NULL,  -- Contains visual_analysis_results array
    vision_model_used VARCHAR(255) NOT NULL,
    prompt_used TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(pitch_deck_id, vision_model_used, prompt_used)
);
```

#### Step 3: Extraction Results Storage
Step 3 stores ALL extraction results in a single `extraction_experiments` table with multiple JSON columns:
```sql
CREATE TABLE extraction_experiments (
    id SERIAL PRIMARY KEY,
    experiment_name VARCHAR(255) NOT NULL,
    pitch_deck_ids INTEGER[] NOT NULL,  -- Array of deck IDs in the experiment
    
    -- Step 3.1: Company Offering
    results_json TEXT NOT NULL,  -- Contains offering extraction results
    
    -- Step 3.2: Classification
    classification_results_json TEXT,
    
    -- Step 3.3: Company Name
    company_name_results_json TEXT,
    
    -- Step 3.4: Funding Amount
    funding_amount_results_json TEXT,
    
    -- Step 3.5: Deck Date
    deck_date_results_json TEXT,
    
    -- Step 4: Template Processing
    template_processing_results_json TEXT,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Important**: There is NO `extraction_experiment_decks` table. All results are stored as JSON in the `extraction_experiments` table.

### Accessing Cached Data in Step 4

To retrieve extraction results for a specific deck:
```sql
SELECT * FROM extraction_experiments 
WHERE :deck_id = ANY(pitch_deck_ids)
ORDER BY created_at DESC
LIMIT 1;
```

Then parse each JSON column to extract data for the specific deck_id.

### Data Flow Between Steps

1. **Step 2** → Saves to `visual_analysis_cache`
2. **Step 3** → Saves all 5 extractions to `extraction_experiments` JSON columns
3. **Step 4** → Reads from both tables to get complete deck data

**Critical**: If you skip Step 3, Step 4 will have no company offering, name, classification, funding amount, or deck date - leading to poor template analysis quality.

## GPU-Backend Communication Architecture

### Data Access Patterns
The GPU server uses three distinct patterns for accessing backend data:

#### ✅ Direct PostgreSQL Connection (Preferred)
- **Pattern**: GPU → PostgreSQL database directly
- **Use cases**: Model configurations, pipeline prompts, template loading, sector data
- **Authentication**: Database credentials (configured via environment variables)
- **Examples**:
  - `analyzer.get_model_by_type("vision")` - model configurations
  - `analyzer._get_pipeline_prompt("offering_extraction")` - pipeline prompts  
  - `analyzer._load_template_config(template_id)` - template configurations
- **Why it works**: GPU server has PostgreSQL credentials configured

#### ✅ Internal HTTP Endpoints (Safe)
- **Pattern**: GPU → Backend HTTP API (internal endpoints)
- **Use cases**: Real-time data exchange, progress updates, caching
- **Authentication**: None required (internal endpoints)
- **Examples**:
  - `POST /api/dojo/internal/get-cached-visual-analysis` - fetch cached visual analysis
  - `POST /api/dojo/internal/cache-visual-analysis` - cache visual analysis results
  - `POST /api/dojo/template-progress-callback` - progress updates
  - `POST /api/internal/update-deck-results` - deck result updates
- **Why it works**: These endpoints only require `db: Session = Depends(get_db)`

#### ❌ User-Authenticated HTTP Endpoints (Problematic)
- **Pattern**: GPU → Backend HTTP API (user endpoints)
- **Use cases**: Should be avoided for GPU server calls
- **Authentication**: Requires `current_user: User = Depends(get_current_user)`
- **Examples**:
  - `GET /api/healthcare-templates/templates/{id}` - template details
  - Most user-facing API endpoints
- **Why it fails**: GPU server has no user authentication credentials

### Architecture Guidelines

**For GPU Server Development:**
1. **Prefer direct PostgreSQL access** for configuration and static data
2. **Use internal HTTP endpoints** for real-time data exchange
3. **Avoid user-authenticated endpoints** - they will return 403 Forbidden
4. **When adding new GPU features**, ensure data access follows these patterns

**Common Error Pattern:**
```
HTTP 403 Forbidden on /api/some-endpoint
```
**Solution**: Check if endpoint requires `current_user` parameter, use direct DB or internal endpoint instead.

## Production Deployment Lessons (CRITICAL for Claude)

### Database Schema Management
**Problem**: Code vs Database Drift - SQLAlchemy models had only 13 tables but database had 29 tables.

**Root Cause**: Many tables were created by manual SQL scripts without corresponding SQLAlchemy models.

**Solution**: All tables now have proper SQLAlchemy models in `backend/app/db/models.py`

**Prevention**:
```bash
# Always verify schema before deployment
python scripts/test_complete_schema.py

# Expected output: "✅ ALL EXPECTED TABLES WOULD BE CREATED"
# If fails, run: python scripts/generate_missing_models.py
```

**Production Schema Creation**:
```bash
# Complete database recreation (preserves users)
python scripts/create_production_schema_final.py
sudo -u postgres psql -d review-platform -f scripts/pipeline_prompts_production.sql
```

### Environment-Aware Frontend Configuration
**Problem**: Manual proxy configuration changes needed for each deployment.

**Solution**: Automatic environment detection in `frontend/src/config/environment.js`
- **Development**: Uses external IPs (65.108.32.143:8000/api)
- **Production**: Uses relative URLs (/api)
- **No more manual package.json proxy changes needed**

### Common Production Deployment Issues

1. **Systemd services ignore .env files** - Always add `EnvironmentFile=` directive
2. **Nginx needs symlink deployment** - Direct directory replacement causes 500 errors  
3. **Frontend environment detection** - Check browser console for environment confirmation
4. **Database connection pooling** - Restart services after environment changes
5. **Filesystem paths** - Verify `SHARED_FILESYSTEM_MOUNT_PATH` in systemd logs

### Production Deployment Checklist
```bash
# 1. Pull latest code
git pull origin main

# 2. Deploy environment configuration (REQUIRED)
./environments/deploy-environment.sh production

# 3. Update database schema (if needed)
python scripts/create_production_schema_final.py

# 4. Deploy frontend with zero downtime
scripts/build-frontend.sh production

# 5. Restart services with new environment
sudo systemctl daemon-reload
sudo systemctl restart review-platform.service
sudo systemctl restart gpu-http-server.service

# 6. Verify deployment
curl http://localhost:8000/api/health
# Check browser console for correct environment detection
```

## Critical Architecture Rules (NEVER VIOLATE)

### 1. No Hardcoded Paths in Source Code
**ABSOLUTE RULE**: Never hardcode filesystem paths like `/mnt/dev-shared/` or `/mnt/CPU-GPU/` in any source file.

**Wrong:**
```python
DOJO_PATH = "/mnt/dev-shared/dojo"  # NEVER DO THIS
full_path = os.path.join("/mnt/dev-shared", file_path)  # FORBIDDEN
```

**Correct:**
```python
DOJO_PATH = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, "dojo")
full_path = os.path.join(settings.SHARED_FILESYSTEM_MOUNT_PATH, file_path)
```

**Why**: Hardcoded paths break environment portability. The same code must work in development (`/mnt/dev-shared/`) and production (`/mnt/CPU-GPU/`) without modification.

### 2. Centralized Environment Management Only
**ABSOLUTE RULE**: ALL environment configuration MUST be managed through `/environments/` directory using the deployment script.

**Directory Structure:**
```
/environments/
├── .env.backend.development
├── .env.backend.production
├── .env.frontend.development  
├── .env.frontend.production
├── .env.gpu.development
├── .env.gpu.production
└── deploy-environment.sh
```

**Deployment Commands:**
```bash
# ONLY way to switch environments
./environments/deploy-environment.sh development
./environments/deploy-environment.sh production
```

**Forbidden:**
- Manual editing of `.env` files in component directories
- Creating new `.env` files outside `/environments/`
- Using different naming conventions
- Hardcoding environment values in config files

**Why**: Scattered environment files caused deployment failures. Centralized management ensures consistency and prevents configuration drift.

### 3. Environment Variables Override Defaults
**RULE**: Configuration classes must read from environment variables, never hardcode environment-specific values.

**Wrong:**
```python
ENVIRONMENT: str = "development"  # NEVER hardcode environment
```

**Correct:**
```python
ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")  # Always use env vars
```

### Enforcement Checklist for Claude

Before ANY deployment or configuration change:
- [ ] Check for hardcoded paths: `grep -r "/mnt/" --include="*.py"`
- [ ] Verify all env changes are in `/environments/`
- [ ] Use deployment script: `./environments/deploy-environment.sh`
- [ ] Never create `.env` files outside `/environments/`
- [ ] Test both development and production environments

**Violations of these rules caused hours of debugging during production deployment. These are NOT guidelines - they are MANDATORY architecture decisions.**

## Debugging Best Practices

### Database Schema Investigation
```python
# Essential query to check table structure
result = db.execute(text('SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = \'table_name\' ORDER BY ordinal_position')).fetchall()
```

### Backend Service Management
```bash
# Start backend with auto-reload (recommended)
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Check what's using a port
lsof -i :8000

# Kill specific process (preferred over pkill)
kill -9 PID

# Check backend logs
tail -f backend.log

# Check GPU processing logs (from development CPU)
tail -f /mnt/dev-shared/logs/gpu_processing.log
```

### Frontend Development
```bash
# Start frontend only (when backend already running)
./start-frontend-only.sh start

# Check frontend compilation
curl -s "http://65.108.32.143:3000" | grep -o "<title>.*</title>"
```

### Common Issues & Solutions

#### Port Conflicts
- Development backend: Port 8000
- Frontend dev server: Port 3000
- Check for duplicate processes before starting services

#### Environment Configuration
- Frontend proxy: Both `package.json` "proxy" and `.env.development` matter
- Use external IP (65.108.32.143) not localhost for remote access
- Backend auto-reload watches for file changes

#### Database Constraint Violations
- Always check NOT NULL constraints
- Verify foreign key relationships
- Use actual column names from schema, not assumed names

### API Development Workflow
1. **Backend**: Create endpoint with Pydantic models
2. **Frontend**: Add API function in `services/api.js`
3. **Component**: Import and use new API function
4. **Testing**: Use browser dev tools to inspect requests
5. **Verification**: Check `/openapi.json` for endpoint registration

### Error Investigation Process
1. **Check HTTP status**: 404 (not found) vs 500 (server error) vs 401 (auth)
2. **Backend logs**: Look for SQL errors and stack traces
3. **Frontend console**: Check for JavaScript errors
4. **Network tab**: Inspect actual request/response payloads
5. **Database state**: Verify data actually exists where expected

### Best Practices
- **Always verify before assuming**: Check database schema, API responses, file paths
- **Use auto-reload**: Backend automatically picks up changes
- **Test incrementally**: Verify each layer works before moving to the next
- **Keep services consistent**: Use standard ports and external IPs
- **Log everything**: Add console.log/logger.info for debugging
- **Handle errors gracefully**: Both frontend and backend should handle edge cases