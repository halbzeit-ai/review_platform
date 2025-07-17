
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
