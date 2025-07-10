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
- Endpoint: `nfs.fin-01.datacrunch.io:/SFS-5gkKcxHe-6721608d`
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

**Code Updates:**
```bash
cd /opt/review-platform
git pull origin main
cd frontend && NODE_ENV=production npm run build
```

**Troubleshooting Scripts:**
```bash
./fix_database.sh      # Fix database schema issues
./fix_upload_size.sh   # Update nginx upload limits
```

This session successfully established a working production deployment with proper file upload functionality and user-friendly error handling.