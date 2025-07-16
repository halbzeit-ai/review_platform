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

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 5001 --reload
```

### Frontend
```bash
cd frontend
npm install
npm start        # Development server
npm run build    # Production build
npm test         # Run tests
```

### Type Checking
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

---

# SESSION LOG: 2025-07-10 - Deployment & Bug Fixes

## Major Issues Resolved Today

### 1. Frontend API Configuration Issue ✅
**Problem:** Frontend making requests to hardcoded `0.0.0.0:5001` instead of nginx proxy `/api`
**Root Cause:** Individual React components had hardcoded URLs instead of using centralized API service
**Files Fixed:**
- `frontend/src/pages/StartupDashboard.js` - Fixed upload and deck fetching
- `frontend/src/pages/GPDashboard.js` - Fixed deck fetching and role updates  
- `frontend/src/pages/Login.js` - Fixed login endpoint
- `frontend/src/pages/Register.js` - Fixed registration endpoint
- `frontend/src/services/api.js` - Updated and added missing API methods

**Solution:** Refactored all components to use centralized API service with proper baseURL configuration.

### 2. Database Schema Mismatch ✅  
**Problem:** SQLite database missing `file_path` column causing upload failures
**Error:** `sqlalchemy.exc.OperationalError: no such column: pitch_decks.file_path`
**Solution:** 
- Created `backend/migrate_db.py` migration script
- Created `fix_database.sh` deployment script
- Successfully migrated database schema on server

### 3. File Upload Size Limits ✅
**Problem:** Large PDF files (4.5MB) failing, only 31KB files working
**Root Cause:** Default nginx `client_max_body_size` limit (1MB)
**Solution:**
- Updated nginx config to allow 50MB uploads (`client_max_body_size 50M`)
- Added proxy timeouts for file uploads
- Created `fix_upload_size.sh` for server deployment

### 4. User Experience Improvements ✅
**Added Features:**
- Client-side file validation (size + type checking)
- Better error messages with specific file size information
- Clear UI instructions about upload requirements
- Improved error handling for different HTTP status codes

## Current System Status (Production Ready)

**Infrastructure:** Datacrunch.io CPU.4V.16G instance (Ubuntu 24.04)
**Deployment Path:** `/opt/review-platform/`
**Shared Storage:** NFS mounted at `/mnt/shared` 
- Endpoint: `nfs.fin-01.datacrunch.io:/SFS-3H6ebwA1-b0cbae8b`
- Mount Command: `mount -t nfs nfs.fin-01.datacrunch.io:/SFS-3H6ebwA1-b0cbae8b /mnt/shared`
- Structure: `{uploads,results,temp}/`

**Services Running:**
- ✅ Backend API (port 8000, systemd service: `review-platform`)
- ✅ Nginx reverse proxy (port 80, frontend + `/api` routing)
- ✅ Database (SQLite with correct schema)

**Working Features:**
- ✅ User registration/login (startup/GP roles)
- ✅ PDF upload validation and storage (up to 50MB)
- ✅ Dashboard navigation and file listing
- ✅ Centralized API communication
- ✅ Proper error handling and user feedback

**Pending Implementation:**
- ⏳ GPU processing workflow  
- ⏳ AI review generation
- ⏳ Results display system
- ⏳ Email notifications

## Key Configuration Files

**Backend Environment:** `/opt/review-platform/backend/.env`
```
DATACRUNCH_SHARED_FILESYSTEM_ID=7cc261b3-b9ad-45be-8633-9f09c56a26c3
SHARED_FILESYSTEM_MOUNT_PATH=/mnt/shared
```

**Nginx Config:** 50MB upload limit, proper proxy timeouts
**Frontend:** Production build uses `/api` baseURL via nginx proxy

## Deployment Commands Reference

**Service Management:**
```bash
sudo systemctl status review-platform
sudo journalctl -f -u review-platform
sudo systemctl restart nginx
```

**Code Updates (CRITICAL - Always rebuild frontend!):**
```bash
cd /opt/review-platform
git pull origin main
cd frontend && NODE_ENV=production npm run build  # ⚠️ NEVER FORGET THIS STEP!
```

**⚠️ DEPLOYMENT REMINDER:**
After any `git pull` in production, you MUST rebuild the frontend! The React app needs to be recompiled to include new components like VerifyEmail page.

**Troubleshooting Scripts:**
```bash
./fix_database.sh      # Fix database schema issues
./fix_upload_size.sh   # Update nginx upload limits
```

This session successfully established a working production deployment with proper file upload functionality and user-friendly error handling.

---

# SESSION LOG: 2025-07-16 - Project Organization & Deck Viewer Implementation

## Major Feature Implementation: Project-Based Dashboard System

### 1. **Configurable AI Pipeline System** ✅
**Implementation:** Complete prompt configuration system for AI analysis pipeline
**Files Modified:**
- `backend/migrations/create_pipeline_prompts.sql` - Database schema for configurable prompts
- `backend/app/api/pipeline.py` - API endpoints for prompt management (GET/PUT with GP-only access)
- `frontend/src/pages/TemplateManagement.js` - Pipeline Settings tab with real-time prompt editor
- `gpu_processing/utils/pitch_deck_analyzer.py` - Modified to fetch prompts from database

**Key Features:**
- Real-time character count and save/reset functionality
- Database-driven prompt configuration replacing hardcoded values
- GP-only access control for prompt modification
- Foundation for all AI processing steps including healthcare templating

### 2. **Complete Project-Based Architecture** ✅
**Problem Solved:** Replaced single-file upload view with comprehensive project organization
**Architecture Changes:**
- **Login Redirect**: Startups now land directly on project dashboard (`/project/{companyId}`)
- **Route Structure**: `/project/{companyId}/deck-viewer/{deckId}` and `/project/{companyId}/results/{deckId}`
- **Database Schema**: Added `company_id` and `results_file_path` columns to `pitch_decks` table
- **Access Control**: Company-based permissions with GP override capabilities

**Files Created/Modified:**
- `backend/migrations/add_company_id_and_results_path.sql` - Database migration
- `backend/app/api/projects.py` - Complete project-based API endpoints
- `frontend/src/pages/ProjectDashboard.js` - Main project dashboard with tabs
- `frontend/src/components/StartupDashboardRedirect.js` - Automatic redirection
- `frontend/src/components/DashboardRedirect.js` - Smart role-based routing

### 3. **Slide-by-Slide Deck Viewer** ✅
**Purpose:** Verification system to ensure prompt changes affect AI analysis output
**Implementation:** Full-featured deck viewer with image navigation and AI analysis display

**Files Created:**
- `frontend/src/pages/DeckViewer.js` - Complete slide viewer component
- `frontend/src/components/ProjectResults.js` - Reusable results component
- `frontend/src/pages/ProjectResultsPage.js` - Standalone results page

**Key Features:**
- **Navigation**: Previous/next slide controls with thumbnail navigation
- **Image Display**: Zoom controls (50%-300%) with smooth transitions
- **AI Analysis**: Side-by-side view of slide images and generated descriptions
- **Breadcrumb Navigation**: Proper routing back to project dashboard
- **Responsive Design**: Works across all screen sizes

### 4. **File Management System Overhaul** ✅
**Problem Solved:** Replaced bulky card-based upload UI with lean, information-dense list
**Before**: Large tile cards with minimal information
**After**: Compact rows showing filename, size, page count, and upload date/time

**Files Modified:**
- `frontend/src/components/ProjectUploads.js` - Complete rewrite with upload functionality
- `backend/app/api/projects.py` - Enhanced to extract page count from analysis results

**Features Implemented:**
- **Lean Design**: Compact rows instead of bulky tiles
- **Essential Information**: Filename, size, pages, full date/time
- **Upload Functionality**: Drag-and-drop with validation (50MB PDF limit)
- **Real-time Status**: Shows "Processing...", "Analyzed", or page count
- **Error Handling**: Client-side validation with specific error messages

### 5. **Configuration Management & Path Standardization** ✅
**Problem Solved:** Eliminated hardcoded filesystem paths throughout the application
**Before**: Hardcoded `/mnt/shared` and `/mnt/CPU-GPU` paths scattered across files
**After**: Centralized configuration using `settings.SHARED_FILESYSTEM_MOUNT_PATH`

**Files Fixed:**
- `backend/app/api/projects.py` - Now uses `settings.SHARED_FILESYSTEM_MOUNT_PATH`
- `backend/app/services/gpu_communication.py` - Removed hardcoded paths
- `backend/app/core/config.py` - Single source of truth for filesystem paths

**Environment Configuration:**
```bash
SHARED_FILESYSTEM_MOUNT_PATH=/mnt/CPU-GPU
```

### 6. **Database Schema Evolution** ✅
**Migration Scripts Created:**
- `backend/migrations/add_company_id_and_results_path.sql` - Added company_id and results_file_path columns
- `backend/fix_database_schema.sh` - Automated migration deployment
- `backend/fix_completed_decks.py` - Fixed processing status for existing decks
- `backend/fix_results_paths.py` - Corrected results file path references

**Schema Changes:**
```sql
ALTER TABLE pitch_decks ADD COLUMN company_id VARCHAR;
ALTER TABLE pitch_decks ADD COLUMN results_file_path VARCHAR;
CREATE INDEX idx_pitch_decks_company_id ON pitch_decks(company_id);
```

### 7. **API Architecture Improvements** ✅
**New Endpoints:**
- `GET /api/projects/{company_id}/deck-analysis/{deck_id}` - Slide-by-slide analysis
- `GET /api/projects/{company_id}/results/{deck_id}` - Analysis results
- `GET /api/projects/{company_id}/uploads` - File uploads with metadata
- `GET /api/projects/{company_id}/slide-image/{deck_name}/{filename}` - Image serving
- `GET/PUT /api/pipeline/prompts/{stage_name}` - Prompt configuration

**Enhanced Data Models:**
```python
class ProjectUpload(BaseModel):
    filename: str
    file_path: str
    file_size: int
    upload_date: str
    file_type: str
    pages: Optional[int] = None
    processing_status: str = "pending"
```

### 8. **User Experience Enhancements** ✅
**Navigation Flow:**
1. **Login** → Automatic redirect to project dashboard
2. **Project Dashboard** → Three tabs: Overview, All Decks, Uploads
3. **Deck Viewer** → Slide-by-slide analysis with AI descriptions
4. **Results** → Comprehensive analysis results display

**UI Improvements:**
- **Breadcrumb Navigation**: Clear path back to dashboard
- **Status Indicators**: Visual chips showing processing state
- **File Validation**: Real-time size and type checking
- **Error Handling**: User-friendly error messages with specific guidance

## Current System Architecture (Production Ready)

**Frontend Routes:**
- `/project/{companyId}` - Main project dashboard
- `/project/{companyId}/deck-viewer/{deckId}` - Slide viewer
- `/project/{companyId}/results/{deckId}` - Analysis results
- `/dashboard/startup` - Redirects to project dashboard
- `/dashboard` - Smart redirect based on user role

**Backend Services:**
- **Project API** - Company-based access control and file management
- **Pipeline API** - Configurable prompt system
- **GPU Communication** - Model management and processing triggers
- **Authentication** - JWT-based with role-based access

**Database Structure:**
- **Users**: Role-based access (startup/GP)
- **Pitch Decks**: Company-based organization with results tracking
- **Pipeline Prompts**: Configurable AI analysis prompts
- **Model Configs**: GPU model management

**File Organization:**
```
/mnt/CPU-GPU/
├── uploads/          # Original uploaded files
├── results/          # Analysis results (JSON)
├── projects/         # Project-based slide images
└── gpu_commands/     # GPU communication
```

## Technical Achievements

**1. Scalable Architecture**: Project-based organization supporting multiple companies
**2. Configurable AI Pipeline**: Database-driven prompt system for customizable analysis
**3. Real-time Processing**: Background GPU processing with status tracking
**4. Comprehensive Verification**: Slide-by-slide viewer to verify prompt effectiveness
**5. Production-Ready**: Environment-based configuration and proper error handling

## Deployment Status

**✅ Working Features:**
- Complete project organization and navigation
- Slide-by-slide deck viewer with AI analysis
- Configurable AI prompts through UI
- File upload with validation and status tracking
- Company-based access control
- Real-time processing status updates

**🔧 Production Commands:**
```bash
# Database Migration
cd /opt/review-platform/backend
./fix_database_schema.sh

# Frontend Build
cd /opt/review-platform/frontend
NODE_ENV=production npm run build

# Service Restart
sudo systemctl restart review-platform
```

This implementation establishes a complete project management system with verification capabilities for AI prompt effectiveness, replacing the simple upload interface with a comprehensive analysis platform.