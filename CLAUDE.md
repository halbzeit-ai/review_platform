# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## CRITICAL: Claude Debugging and Investigation Permissions

**IMPORTANT**: Claude is ALWAYS allowed to use the following tools for debugging and investigation:
- **grep, rg, find** - Search for patterns, files, code structures across the entire codebase
- **ls, cat, head, tail** - Read and navigate files and directories anywhere in the system
- **PostgreSQL access** - Query database directly for data, structures, schemas, debugging
- **Log file access** - Read all log files in shared filesystem for troubleshooting

These permissions are UNRESTRICTED for debugging, investigation, and understanding system behavior. Use these tools proactively to solve problems.

## CRITICAL: Claude Server Environment Detection

**IMPORTANT**: Claude Code runs on different servers depending on the session. Always run the environment detection script first:

```bash
# ALWAYS run this first to determine which server Claude is on
./scripts/detect-claude-environment.sh
```

**Server Infrastructure**:
- **dev_cpu** (65.108.32.143): Development CPU server
- **dev_gpu** (135.181.71.17): Development GPU server  
- **prod_cpu** (135.181.63.224): Production CPU server
- **prod_gpu** (135.181.63.133): Production GPU server
- **Local machines**: NixOS, MacBook Air, etc. (developer workstations)

**Claude Code Capabilities by Server**:

### If Claude is on dev_cpu (65.108.32.143):
- ✅ **Full development access** - Can edit code, run services, test changes
- ✅ **Database access** - Can run migrations, test schemas  
- ✅ **Service management** - Can start/stop backend and frontend
- ❌ **No production access** - Cannot directly modify production
- ✅ **Git operations** - Can commit changes for user to deploy

### If Claude is on prod_cpu (135.181.63.224):
- ✅ **Production management** - Can deploy, restart services, check logs
- ✅ **Database access** - Can run production queries and migrations
- ✅ **Service debugging** - Can check systemd services, nginx configuration
- ❌ **Limited code editing** - Should primarily deploy from development
- ✅ **Emergency fixes** - Can make direct production edits if required

### If Claude is on dev_gpu (135.181.71.17):
- ✅ **AI development** - Can test GPU processing, develop AI features
- ✅ **Processing debugging** - Can check AI pipeline logs and performance
- ✅ **Database access** - Can connect to development database on dev_cpu (65.108.32.143)
- ❌ **No service management** - Cannot start/stop CPU services
- ✅ **Shared filesystem** - Can access development shared storage

### If Claude is on prod_gpu (135.181.63.133):
- ✅ **AI processing** - Can run production GPU tasks, debug AI issues
- ✅ **Processing debugging** - Can check production AI pipeline logs
- ✅ **Database access** - Can connect to production database on prod_cpu (135.181.63.224)
- ❌ **No service management** - Cannot start/stop CPU services  
- ✅ **Shared filesystem** - Can access production shared storage

**Deployment Workflow (Server-Dependent)**:

### From dev_cpu (65.108.32.143):
1. Claude makes changes in development environment
2. User pulls changes to prod_cpu (`git pull origin main` on 135.181.63.224)
3. User runs deployment commands on production servers
4. User provides production logs/output back to Claude for analysis

### From prod_cpu (135.181.63.224):
1. Claude can deploy directly from git
2. Claude can restart services and check deployment status
3. Claude can verify deployment and provide real-time feedback

### Detection Script Usage:
```bash
# The script will output one of:
# "dev_cpu" (65.108.32.143)
# "prod_cpu" (135.181.63.224)
# "dev_gpu" (135.181.71.17) 
# "prod_gpu" (135.181.63.133)
# "local" (developer workstation)
```

**CRITICAL**: Always check server environment before starting any work to understand your capabilities and limitations.

## IMPORTANT: Read Product Requirements First

**Before starting any work, always read through the Product Requirements Documents (PRDs) to understand the overall product vision and context:**

```bash
# Essential reading for understanding the product:
cat PRD/PRD.md                    # Overall product requirements and vision
cat PRD/dojo-PRD.md               # Dojo testing environment specifications  
cat PRD/startup-journey.md        # 14-stage funding process details
cat PRD/beta-startup-onboarding.md # Beta testing and onboarding process
```

This will give you the complete context of:
- User personas (GPs vs Startups)
- Core product areas and features
- Technical architecture decisions
- Funding process workflow (14 stages)
- Dojo testing environment capabilities

## Project Overview

This is a startup review platform with a Python FastAPI backend and React frontend. The platform allows:
- Startups to register, upload pitch decks (PDFs), and receive AI-generated reviews
- GPs (General Partners) to review, modify, and approve reviews
- A Q&A system between startups and GPs
- Dojo testing environment for GPs to experiment with AI parameters
- 14-stage funding process management
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
- **Development**: PostgreSQL database `review_dev` running on dev_cpu (65.108.32.143)
- **Production**: PostgreSQL database `review-platform` running on prod_cpu (65.108.32.168)
- **Important**: These are completely separate PostgreSQL instances with distinct data
- **GPU Access**: Both dev_gpu and prod_gpu connect to their respective CPU databases remotely
- **Legacy**: SQLite for development (`backend/sql_app.db`) - deprecated

## Database and Model Synchronization

**IMPORTANT**: Keep database and models.py in sync to avoid deployment issues.

### Quick Sync Check
```bash
# Check if database and models.py are in sync
./scripts/db-sync-simple.sh

# Expected output if in sync:
# ✅ Database and models.py are IN SYNC!
# ✅ All foreign keys are valid
```

### Database Management Tools
```bash
# Comprehensive database management
./scripts/db-management.sh check       # Check sync status
./scripts/db-management.sh orphans     # List tables without models
./scripts/db-management.sh validate-fk # Validate foreign keys
./scripts/db-management.sh create-model <table_name> # Generate model from table

# Pre-commit hook (automatically checks sync before commits)
# Already installed at .git/hooks/pre-commit
```

### Common Sync Issues and Solutions
1. **Table only in database**: Either add model to models.py or drop table
2. **Table only in models.py**: Run migration to create table or remove unused model
3. **Column mismatch**: Update model or run migration
4. **Example**: ProjectProgress model was defined but never used - removed it

### Best Practices
- Always run sync check before deployment
- Remove unused models to keep codebase clean
- Keep table names consistent (snake_case)
- Document any intentional mismatches

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

### API Debugging Tools (For Claude) ⭐ MASSIVELY ENHANCED ⭐

**CRITICAL FOR EFFICIENT DEBUGGING**: Comprehensive debugging toolkit with 20+ commands covering all system areas, using authentication-free debug endpoints and direct database queries.

#### 📊 SYSTEM & ENVIRONMENT
```bash
./scripts/debug-api.sh health                       # System health check
./scripts/debug-api.sh env                          # Environment configuration  
./scripts/debug-api.sh tables                       # List all database tables
./scripts/debug-api.sh table project_documents     # Table structure & sample data
./scripts/debug-api.sh models                       # AI model configuration
./scripts/debug-api.sh prompts                      # All pipeline prompts
./scripts/debug-api.sh prompts offering_extraction  # Specific prompt stage
```

#### 🔧 PROCESSING & DOCUMENTS  
```bash
./scripts/debug-api.sh processing                   # Overall processing queue analysis
./scripts/debug-api.sh processing 152               # Specific document processing details
./scripts/debug-api.sh queue                        # Queue health & failed tasks
./scripts/debug-api.sh document 152                  # Document status (API endpoint)
./scripts/debug-api.sh specialized 152              # Specialized analysis results for document
```

#### 🏗️ PROJECTS & USERS
```bash
./scripts/debug-api.sh project 31                   # Project relationships & overview
./scripts/debug-api.sh project-docs 31              # Project document processing pipeline  
./scripts/debug-api.sh user user@startup.com        # User relationships & dependencies
./scripts/debug-api.sh invitations user@email.com   # User invitation history
./scripts/debug-api.sh invitations 42               # Project invitation status
./scripts/debug-api.sh deletion 31                  # Preview deletion impact
./scripts/debug-api.sh orphans                      # Orphaned projects analysis
```

#### 🧪 DOJO & EXPERIMENTS
```bash
./scripts/debug-api.sh dojo stats                   # Dojo system statistics
./scripts/debug-api.sh dojo experiments             # Active extraction experiments
./scripts/debug-api.sh dojo cache                   # Visual analysis cache status
./scripts/debug-api.sh dojo projects                # Dojo test projects
./scripts/debug-api.sh dojo cleanup                 # Storage impact analysis
```

#### 🏥 HEALTHCARE TEMPLATES
```bash
./scripts/debug-api.sh templates list               # Available templates
./scripts/debug-api.sh templates performance        # Usage & performance metrics
./scripts/debug-api.sh templates sectors            # Healthcare sectors & classification
./scripts/debug-api.sh templates customizations     # GP template customizations
```

#### ⚡ COMPREHENSIVE ANALYSIS
```bash
./scripts/debug-api.sh all                          # Full system debug report
./scripts/debug-api.sh help                         # Complete usage guide
```

**Architecture**: Combines authentication-free API endpoints with direct PostgreSQL queries for comprehensive system analysis without authentication barriers.

**New API Endpoints Added**:
```bash
# Authentication-free debug endpoints
GET /api/debug/processing/queue-stats          # Processing queue statistics
GET /api/debug/processing/deck/{id}            # Comprehensive deck processing info
GET /api/debug/dojo/experiments-summary        # Dojo experiment statistics  
GET /api/debug/templates/performance           # Template usage metrics
GET /api/debug/models/config                   # AI model configuration
```

**Why This Exists**: Regular API endpoints return `{"detail": "Not authenticated"}` which makes debugging inefficient. This toolkit provides instant access to all system areas for comprehensive troubleshooting.

**Key Capabilities**:
- ✅ **Processing Pipeline**: Queue health, deck processing, error analysis
- ✅ **Project System**: Relationships, documents, invitations, orphaned projects
- ✅ **Dojo Experiments**: Visual cache, extraction experiments, test data
- ✅ **Healthcare Templates**: Performance, sectors, customizations
- ✅ **System Configuration**: Models, prompts, environment settings
- ✅ **Cross-System Analysis**: Relationships between users, projects, and data

### Secure Authentication Helper: auth-helper.sh ⭐ NEW ⭐

**SECURE API TESTING**: For cases where you need to test authenticated endpoints safely.

```bash
# SETUP (One-time)
./scripts/auth-helper.sh setup                    # Initialize secure config
./scripts/auth-helper.sh config                   # Show configuration

# AUTHENTICATION (Uses real login endpoints - no backdoors)
./scripts/auth-helper.sh login startup user@example.com   # Login as startup user
./scripts/auth-helper.sh login gp gp@example.com         # Login as GP
./scripts/auth-helper.sh whoami                          # Show current user

# AUTHENTICATED API TESTING
./scripts/auth-helper.sh api GET /api/projects/my-projects          # User's projects
./scripts/auth-helper.sh api GET /api/projects/extraction-results   # User's results
./scripts/auth-helper.sh api POST /api/projects/upload -F file=@doc.pdf  # File upload
./scripts/auth-helper.sh logout                                     # Clean logout
```

**Security Features**:
- ✅ **No Backdoors**: Uses legitimate authentication endpoints only
- ✅ **Real Credentials**: Requires actual user passwords from secure config
- ✅ **Production Warnings**: Detects production environment and warns
- ✅ **Secure Storage**: Tokens stored with proper permissions (chmod 600)
- ✅ **Automatic Cleanup**: Tokens removed on logout
- ✅ **Role Validation**: Ensures user role matches config

**Configuration**:
```bash
# Add test users to /opt/review-platform/scripts/test-users.conf:
testuser@startup.com:SecurePassword123:startup
testgp@halbzeit.ai:GPPassword456:gp
```

**When to Use**: 
- ✅ Testing user-specific endpoints that require authentication
- ✅ Debugging file upload workflows 
- ✅ Testing project member access
- ❌ **Still prefer debug-api.sh for system-level debugging** (no auth required)

## Claude Development Helper Script: Comprehensive Toolkit ⭐

**Location**: `./claude-dev-helper.sh`

**Core Purpose**: Provides elevated-privilege database operations and comprehensive development diagnostics that Claude frequently needs.

### Database Management Commands
```bash
# Database migrations with elevated privileges
./claude-dev-helper.sh migrate migrations/filename.sql

# Database connectivity and health checks
./claude-dev-helper.sh db-check              # Test connection and show dojo files count
./claude-dev-helper.sh migrate-check         # Check if specific columns exist
./claude-dev-helper.sh db-connect            # Direct PostgreSQL connection
./claude-dev-helper.sh query "SELECT * FROM table_name;"  # Execute custom SQL
```

### GPU Processing & Cache Debugging
```bash
# GPU log monitoring (shared filesystem access)
./claude-dev-helper.sh gpu-logs              # Last 50 lines
./claude-dev-helper.sh gpu-logs tail         # Follow in real-time
./claude-dev-helper.sh gpu-logs errors       # Recent errors and warnings
./claude-dev-helper.sh gpu-logs backend      # Backend URL configuration
./claude-dev-helper.sh gpu-logs cache        # Caching operations

# Visual analysis cache debugging
./claude-dev-helper.sh debug-cache           # Comprehensive cache analysis
./claude-dev-helper.sh cache-check          # Database cache status
```

### Development & Service Management
```bash
# Comprehensive development test
./claude-dev-helper.sh quick-test           # Services + database + API endpoints

# Service management via delegation
./claude-dev-helper.sh services start       # Start all development services
./claude-dev-helper.sh services status      # Check service health
./claude-dev-helper.sh services stop        # Stop all services

# Git workflow assistance
./claude-dev-helper.sh git-status          # Branch + changes + recent commits
```

**Key Advantages Over Other Scripts**:
- **Database Privileges**: Uses `sudo -u postgres` for direct database access
- **GPU Access**: Reads GPU processing logs from shared filesystem (`/mnt/dev-shared/logs/`)
- **Cache Debugging**: Specialized tools for visual analysis caching issues
- **Cross-Service**: Combines backend, database, and GPU debugging in one tool
- **Claude-Optimized**: Designed specifically for Claude's debugging workflow

**When to Use claude-dev-helper.sh**:
- ✅ Database schema investigations and migrations
- ✅ GPU processing pipeline debugging  
- ✅ Visual analysis cache troubleshooting
- ✅ Cross-system health checks
- ✅ When you need elevated database privileges

**vs dev-services-improved.sh**: claude-dev-helper focuses on debugging and database operations with elevated privileges, while dev-services-improved.sh focuses on service lifecycle management with smart port detection.

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
./scripts/build-frontend.sh production

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

## Frontend Build Script: Advanced Deployment Tool ⭐

**Location**: `./scripts/build-frontend.sh`

**Core Functionality**:
```bash
# Zero-downtime production deployment
./scripts/build-frontend.sh production

# Development build with live reload
./scripts/build-frontend.sh development

# Build with environment validation
./scripts/build-frontend.sh production --env-check

# Force rebuild (ignore existing builds)  
./scripts/build-frontend.sh production --force
```

**Key Features**:
- **Atomic Deployment**: Uses timestamped directories and symlink switching for zero downtime
- **Environment Detection**: Automatically configures build for correct backend URLs
- **Rollback Support**: Maintains backup builds for instant rollback capability
- **Build Optimization**: Production builds are minified and optimized for performance
- **Health Verification**: Validates build success before deployment
- **Nginx Integration**: Seamlessly works with nginx reverse proxy configuration

**Deployment Flow**:
1. **Build Preparation**: Creates timestamped build directory (`build_YYYYMMDD_HHMMSS`)
2. **Environment Setup**: Configures REACT_APP variables for target environment  
3. **Compilation**: Runs `npm run build` with optimizations
4. **Health Check**: Validates build artifacts and entry points
5. **Atomic Switch**: Updates symlink to new build (zero downtime)
6. **Cleanup**: Maintains backup builds, removes old builds
7. **Verification**: Confirms deployment success

**Production Safety**:
- Never interrupts running services
- Preserves previous build as automatic backup
- Detailed logging for deployment tracking
- Error handling with automatic rollback on failure

## Environment Configuration

The project uses a consistent naming scheme for environment variables to separate service types from environments:

### Server Environment Variables
- `BACKEND_DEVELOPMENT=http://65.108.32.143:8000` - Backend server on dev_cpu (65.108.32.143)
- `BACKEND_PRODUCTION=http://65.108.32.168:8000` - Backend server on prod_cpu (65.108.32.168)
- `GPU_DEVELOPMENT=135.181.71.17` - GPU server on dev_gpu (135.181.71.17)
- `GPU_PRODUCTION=135.181.63.133` - GPU server on prod_gpu (135.181.63.133)

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

## Email Configuration

The platform uses a centralized email system for user communication (registration verification, GP invitations, password resets, welcome emails).

### Email Configuration Management
**Configuration Location**: `/environments/.env.backend.production`
```bash
SMTP_SERVER=mail.halbzeit.ai
SMTP_PORT=587
SMTP_USERNAME=registration@halbzeit.ai
SMTP_PASSWORD=$HZregistration1024
FROM_EMAIL=registration@halbzeit.ai
FROM_NAME=HALBZEIT AI Review Platform
```

### Email Configuration Deployment Process
```bash
# 1. Edit centralized environment file (NEVER edit backend/.env directly)
# /environments/.env.backend.production

# 2. Deploy using environment script
./environments/deploy-environment.sh production --component backend

# 3. Restart backend service to load new configuration
sudo systemctl restart review-platform.service

# 4. Verify service is running
sudo systemctl status review-platform.service
```

### Email Features
- **User Registration**: Verification emails with activation links
- **GP Invitations**: Invitation emails with temporary passwords and verification links
- **Password Reset**: Secure password reset emails with time-limited tokens
- **Welcome Messages**: Welcome emails sent after successful email verification

### Email Service Architecture
- **Service**: `backend/app/services/email_service.py`
- **SMTP Provider**: Hetzner mail server (mail.halbzeit.ai)
- **Templates**: Multilingual support (German/English)
- **Security**: All tokens are hashed and time-limited
- **Gmail Compatibility**: Enhanced headers and HTML structure for better deliverability

## Forced Password Change System

All invited users (GPs and project participants) must change their temporary password on first login for security.

### Database Schema
```sql
-- User table includes forced password change tracking
ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT FALSE;
```

### Backend Implementation
- **Login Flow**: `/auth/login` returns `must_change_password: true` for users requiring password change
- **Change Password Endpoint**: `/auth/change-password` validates current password and updates to new one
- **Security**: Temporary tokens expire in 30 minutes for password changes

### Frontend Flow
1. **Login Check**: Login component detects `must_change_password` response
2. **Redirect**: User redirected to `/change-password` with temporary token
3. **Password Change**: Secure form with current/new/confirm password fields
4. **Completion**: After successful change, user proceeds to dashboard

### Automatic Triggers
- **GP Invitations**: All invited GPs automatically get `must_change_password = true`
- **Migration**: Existing GPs (except ramin@halbzeit.ai) were flagged for password change
- **Security**: Prevents use of temporary passwords beyond initial login

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

### 3. Standard .env File Reading Only
**ABSOLUTE RULE**: All services MUST read from their standard `.env` file in their component directory. Never use custom environment file names.

**Standard Pattern:**
```
backend/.env          ← Backend service reads this
frontend/.env         ← Frontend (if needed) reads this  
gpu_processing/.env   ← GPU processing reads this
```

**Environment File Generation:**
```bash
# deploy-environment.sh creates these files:
backend/.env          (from environments/.env.backend.{environment})
frontend/.env.{env}   (from environments/.env.frontend.{environment})
gpu_processing/.env   (from environments/.env.gpu.{environment})
```

**Forbidden Patterns:**
- ❌ Custom file names: `.env.gpu`, `.env.production`, `.env.development`
- ❌ Hardcoded paths: `/opt/gpu_processing/.env.gpu`
- ❌ Environment-specific files in component directories
- ❌ Multiple `.env.*` files in same directory

**Why Critical**: During production deployment, GPU service failed because:
1. Code was hardcoded to read `.env.gpu` 
2. Deployment script created `.env.production`
3. Service kept using old cached environment with wrong DATABASE_HOST
4. Led to authentication failures and service downtime

**Prevention Checklist:**
- [ ] All Python code uses `load_dotenv('.env')` or `load_dotenv()`
- [ ] Systemd services use `EnvironmentFile=.env` (relative paths)
- [ ] No `.env.*` files exist outside `/environments/` (except `.env.example`)
- [ ] `find . -name ".env.*" -not -path "./environments/*"` returns only examples

**Root Cause of GPU Auth Failures (2025-08-02)**:
GPU processing was hardcoded to read `.env.gpu` while centralized deployment created `.env.production`. Service ran with stale environment containing `DATABASE_HOST=localhost` instead of production CPU IP `65.108.32.168`, causing PostgreSQL authentication failures.

## Shared Filesystem Logging

Both backend and GPU services write their logs to the shared filesystem, allowing Claude to access logs from any server regardless of where services are running.

### Log File Locations
**Development Environment** (`/mnt/dev-shared/logs/`):
- `backend.log` - Backend service logs (FastAPI, database operations, API requests)
- `gpu_http_server.log` - GPU HTTP server logs (model operations, PDF processing)

**Production Environment** (`/mnt/CPU-GPU/logs/`):
- `backend.log` - Backend service logs
- `gpu_http_server.log` - GPU HTTP server logs

### Accessing Logs from Any Server

#### From CPU servers (dev_cpu/prod_cpu):
```bash
# Development environment
tail -f /mnt/dev-shared/logs/backend.log
tail -f /mnt/dev-shared/logs/gpu_http_server.log

# Production environment  
tail -f /mnt/CPU-GPU/logs/backend.log
tail -f /mnt/CPU-GPU/logs/gpu_http_server.log

# View both logs simultaneously
tail -f /mnt/dev-shared/logs/*.log    # Development
tail -f /mnt/CPU-GPU/logs/*.log       # Production
```

#### From GPU servers (dev_gpu/prod_gpu):
```bash
# Same commands work from GPU servers
# Development
tail -f /mnt/dev-shared/logs/backend.log
tail -f /mnt/dev-shared/logs/gpu_http_server.log

# Production
tail -f /mnt/CPU-GPU/logs/backend.log
tail -f /mnt/CPU-GPU/logs/gpu_http_server.log

# Search for specific errors across all logs
grep -i "error\|exception\|failed" /mnt/dev-shared/logs/*.log    # Development
grep -i "error\|exception\|failed" /mnt/CPU-GPU/logs/*.log       # Production
```

### Environment-Specific Paths
Use the correct shared filesystem path based on your environment:
- **Development**: `/mnt/dev-shared/logs/`
- **Production**: `/mnt/CPU-GPU/logs/`

### Log Format
All logs use consistent formatting:
```
2025-01-15 10:30:45,123 - service_name - INFO - Log message here
```

### Common Log Analysis Commands
```bash
# Show last 100 lines from all logs
tail -n 100 /mnt/dev-shared/logs/*.log      # Development
tail -n 100 /mnt/CPU-GPU/logs/*.log         # Production

# Follow logs in real-time with timestamps
tail -f /mnt/dev-shared/logs/*.log | ts '%Y-%m-%d %H:%M:%S'    # Development
tail -f /mnt/CPU-GPU/logs/*.log | ts '%Y-%m-%d %H:%M:%S'       # Production

# Find errors in the last hour
find /mnt/dev-shared/logs/ -name "*.log" -mmin -60 -exec grep -H "ERROR\|CRITICAL" {} \;    # Development
find /mnt/CPU-GPU/logs/ -name "*.log" -mmin -60 -exec grep -H "ERROR\|CRITICAL" {} \;       # Production

# Monitor specific deck processing
grep "deck.*123" /mnt/dev-shared/logs/gpu_http_server.log    # Development
grep "deck.*123" /mnt/CPU-GPU/logs/gpu_http_server.log       # Production

# Check service startup issues
grep -A5 -B5 "Starting\|Failed to start" /mnt/dev-shared/logs/*.log    # Development
grep -A5 -B5 "Starting\|Failed to start" /mnt/CPU-GPU/logs/*.log       # Production
```

### Benefits for Claude
- **Cross-server access**: View backend logs from GPU servers and vice versa
- **Centralized debugging**: All service logs in one location
- **Persistent logging**: Logs survive service restarts and server reboots
- **Real-time monitoring**: Use `tail -f` to watch logs during debugging

## Debugging Best Practices

### STEP 1: Use Debug API Tools First ⭐ CRITICAL ⭐

**ALWAYS use debug tools before manual database queries or authenticated API calls:**

```bash
# Instead of: curl -s "http://localhost:8000/api/documents/processing-progress/143" 
# (Returns: {"detail": "Not authenticated"})

# Use this: 
./scripts/debug-api.sh document 143
# ✅ Gets full document status, processing info, and table relationships immediately

# Quick investigation workflow:
./scripts/debug-api.sh health        # 1. Check system health
./scripts/debug-api.sh tables        # 2. See available tables  
./scripts/debug-api.sh document 143   # 3. Check specific document
./scripts/debug-api.sh table reviews # 4. Investigate table structure if needed
```

**When investigating issues:**
1. **Start with debug tools** - They provide comprehensive context
2. **Check table structure** - Use `./scripts/debug-api.sh table tablename` 
3. **Verify data exists** - Debug endpoints show record counts and samples
4. **Only then** - Drop to manual SQL if needed

### Database Schema Investigation
```bash
# NEW: Use debug tools instead of manual SQL
./scripts/debug-api.sh table project_documents # Get full table info + samples
./scripts/debug-api.sh tables               # List all available tables

# OLD: Manual SQL (use only when debug tools aren't sufficient)
# result = db.execute(text('SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = \'table_name\' ORDER BY ordinal_position')).fetchall()
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

### Error Investigation Process (UPDATED WORKFLOW)
1. **Use debug tools first**: `./scripts/debug-api.sh health` and `./scripts/debug-api.sh document <id>`
2. **Check HTTP status**: 404 (not found) vs 500 (server error) vs 401 (auth)  
3. **Backend logs**: Look for SQL errors and stack traces
4. **Frontend console**: Check for JavaScript errors
5. **Network tab**: Inspect actual request/response payloads
6. **Database state**: Use `./scripts/debug-api.sh table <name>` to verify data

### Best Practices (ENHANCED)
- **⭐ CRITICAL: Use debug API tools first** - Eliminates authentication issues and provides rich context
- **Always verify before assuming**: Use `./scripts/debug-api.sh table <name>` to check schema and data
- **Use auto-reload**: Backend automatically picks up changes
- **Test incrementally**: Verify each layer works before moving to the next
- **Keep services consistent**: Use standard ports and external IPs
- **Log everything**: Add console.log/logger.info for debugging
- **Handle errors gracefully**: Both frontend and backend should handle edge cases

## Claude's Enhanced Debugging Capabilities

**I now have powerful debug tools that make me more effective at troubleshooting issues:**

### What I Can Do Efficiently:
✅ **Investigate document processing issues** without authentication barriers
✅ **Check database table existence and structure** instantly
✅ **Get sample data** from any table for analysis
✅ **Verify system health** comprehensively
✅ **Understand data relationships** between tables
✅ **Debug API endpoints** that would normally return "Not authenticated"

### My Debugging Workflow:
1. **Start with system health**: `./scripts/debug-api.sh health`
2. **Check specific document issues**: `./scripts/debug-api.sh document <id>` 
3. **Investigate database structure**: `./scripts/debug-api.sh table <name>`
4. **Verify environment config**: `./scripts/debug-api.sh env`
5. **Only then** resort to manual SQL or authenticated API calls

### Example Scenarios I Handle Better:
- **"Error fetching progress for document 143"** → `./scripts/debug-api.sh document 143` shows processing status, table relationships, and file info
- **"Does table X exist?"** → `./scripts/debug-api.sh tables` lists all tables instantly
- **"What columns does project_documents have?"** → `./scripts/debug-api.sh table project_documents` shows structure + samples
- **"Is the backend healthy?"** → `./scripts/debug-api.sh health` shows comprehensive system status

### Key Advantage:
Instead of hitting authentication walls with `{"detail": "Not authenticated"}`, I can immediately access detailed debugging information and provide faster, more accurate solutions.