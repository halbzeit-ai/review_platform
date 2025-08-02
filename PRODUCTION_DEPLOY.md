# Production Deployment Plan

## ✅ COMPLETED - GPU Server Fixes (2025-08-02)

### Database Authentication Issues Resolved
- ✅ **Fixed malformed DATABASE_URL**: Added missing host:port to centralized environment configuration
- ✅ **Updated**: `/opt/review-platform/environments/.env.backend.production`
- ✅ **From**: `postgresql://review_user:simpleprod2024@/review-platform`
- ✅ **To**: `postgresql://review_user:simpleprod2024@localhost:5432/review-platform`
- ✅ **Verified**: Database connection from GPU server (135.181.63.133) to production CPU (65.108.32.168)
- ✅ **Deployed**: Production environment using centralized system `./environments/deploy-environment.sh production`
- ✅ **Restarted**: GPU HTTP server service with corrected configuration
- ✅ **Committed**: Changes in commit `5bb12f9`

### Production GPU Server Status
- ✅ **Service**: `gpu-http-server.service` active and healthy
- ✅ **Database**: All 29 tables verified, PostgreSQL 16.9 operational
- ✅ **API**: Health endpoint responding correctly
- ✅ **Environment**: Production configuration active

---

## 🔧 URGENT - GPU Database Connection Issue (2025-08-02 10:50)

### Problem Status
**GPU server still getting authentication failures after restart:**
```
connection to server at "65.108.32.168", port 5432 failed: FATAL: password authentication failed for user "review_user"
```

### Completed CPU-Side Fixes ✅
- ✅ **Database Password**: Reset `review_user` password to `simpleprod2024`
- ✅ **pg_hba.conf**: Added entries for both GPU (135.181.63.133/32) and CPU (65.108.32.168/32) 
- ✅ **Environment**: Deployed production environment with correct DATABASE_URL
- ✅ **Backend Service**: Restarted with fixed configuration
- ✅ **Connectivity**: Verified connection works from production CPU using exact GPU connection string

### Completed GPU-Side Actions ✅  
- ✅ **Code Update**: `git pull origin main` on GPU server
- ✅ **Environment**: `./environments/deploy-environment.sh production` on GPU
- ✅ **Service Restart**: `sudo systemctl restart gpu-http-server.service`

### Remaining Issue ❌
GPU service still cannot connect to database despite all configurations being correct.

## 🎯 GPU SERVER DEBUGGING TASKS

**Move to GPU server (135.181.63.133) to debug directly:**

### 1. Pull Latest Code and Deploy Environment
```bash
# Get latest environment configuration fixes
cd /opt/review-platform
git pull origin main

# Deploy production environment (creates gpu_processing/.env)
./environments/deploy-environment.sh production
```

### 2. Environment File Verification  
```bash
# CRITICAL: Verify standard .env file exists (not .env.gpu or .env.production)
ls -la /opt/review-platform/gpu_processing/.env

# Check DATABASE_HOST is correct production CPU IP
grep "DATABASE_HOST" /opt/review-platform/gpu_processing/.env
# Expected: DATABASE_HOST=65.108.32.168 (NOT localhost)

# Verify no legacy environment files exist
find /opt/review-platform -name ".env.*" -not -path "./environments/*" -type f
# Should only show: ./backend/.env.example

# Check systemd service references correct .env file
sudo systemctl cat gpu-http-server.service | grep EnvironmentFile
# Expected: EnvironmentFile=/opt/gpu_processing/.env (NOT .env.gpu)
```

### 3. Code Verification (Critical Architecture Compliance)
```bash
# Verify GPU code reads standard .env files only
grep -r "\.env\." /opt/review-platform/gpu_processing/ --include="*.py"
# Should show NO references to .env.gpu, .env.production, etc.

# Check specific files are fixed:
grep "load_dotenv" /opt/review-platform/gpu_processing/utils/pitch_deck_analyzer.py
grep "load_dotenv" /opt/review-platform/gpu_processing/config/processing_config.py
# Both should reference .env, not .env.gpu
```

### 4. Database Connection Testing
```bash
# Test direct connection from GPU server
export PGPASSWORD=simpleprod2024
psql -h 65.108.32.168 -p 5432 -U review_user -d review-platform -c "SELECT version();"

# Test Python connection (same as service uses)
python3 -c "
import psycopg2
conn = psycopg2.connect(
    host='65.108.32.168',
    port=5432,
    database='review-platform', 
    user='review_user',
    password='simpleprod2024'
)
print('✅ Connection successful!')
conn.close()
"
```

### 5. Service Restart and Verification
```bash
# Restart GPU service with new environment configuration
sudo systemctl restart gpu-http-server.service

# Check service status
sudo systemctl status gpu-http-server.service

# Monitor logs for database connection success
sudo journalctl -u gpu-http-server.service --since "1 minute ago" -f
# Look for: "Database connection successful" or similar
# Should NOT see: "password authentication failed"
```

### 6. Service Environment Investigation  
```bash
# Check if service is reading environment correctly
sudo journalctl -u gpu-http-server.service --since "5 minutes ago" | grep -i database

# Check service process environment
sudo cat /proc/$(pgrep -f gpu_http_server)/environ | tr '\0' '\n' | grep -i database
```

### 7. Alternative Solutions (If Still Failing)
```bash
# If environment file issues persist, try direct environment variables in systemd:
sudo systemctl edit gpu-http-server.service
# Add:
# [Service]
# Environment="DATABASE_URL=postgresql://review_user:simpleprod2024@65.108.32.168:5432/review-platform"
```

### 8. Expected Resolution
After following these steps, GPU service should:
- ✅ Read from correct `/opt/gpu_processing/.env` file
- ✅ Connect to production database successfully (DATABASE_HOST=65.108.32.168)
- ✅ Load proper prompts from `pipeline_prompts` table
- ✅ Stop using fallback default prompts
- ✅ Complete visual analysis workflow without authentication errors

### 9. Verification Commands Summary
```bash
# Quick verification checklist:
grep "DATABASE_HOST" /opt/review-platform/gpu_processing/.env
sudo systemctl cat gpu-http-server.service | grep EnvironmentFile
find /opt/review-platform -name ".env.*" -not -path "./environments/*" -type f
grep -c ".env.gpu\|.env.production" /opt/review-platform/gpu_processing/*.py /opt/review-platform/gpu_processing/**/*.py
```

**Success Indicators:**
- `DATABASE_HOST=65.108.32.168` ✅
- `EnvironmentFile=/opt/gpu_processing/.env` ✅  
- Only `./backend/.env.example` in legacy files ✅
- Zero references to `.env.gpu` or `.env.production` in Python code ✅

---

## 🚀 COMPLETED - Production CPU Server Tasks

### Critical Tasks for Production CPU (65.108.32.168)

1. **Pull Latest Changes**
   ```bash
   cd /opt/review-platform
   git pull origin main
   ```

2. **Deploy Fixed Environment**
   ```bash
   ./environments/deploy-environment.sh production
   ```

3. **Restart Backend Services**
   ```bash
   sudo systemctl restart review-platform.service
   sudo systemctl status review-platform.service
   ```

4. **Verify Database Connection**
   ```bash
   # Test backend can connect to local PostgreSQL
   python3 -c "from backend.app.core.config import settings; print('DB URL:', settings.DATABASE_URL)"
   ```

5. **Test API Health**
   ```bash
   curl -X GET "http://localhost:8000/api/health"
   ```

6. **Verify GPU Communication**
   ```bash
   # Test connection to GPU server
   curl -X GET "http://135.181.63.133:8001/api/health"
   ```

7. **Frontend Deployment** (if needed)
   ```bash
   cd frontend
   npm run build
   # Update nginx configuration to serve build/ directory
   ```

### Additional Verification Tasks

8. **Database Schema Check**
   ```bash
   # Verify all 29 tables exist on production CPU
   python3 scripts/test_complete_schema.py
   ```

9. **User Authentication Test**
   ```bash
   # Test user login functionality
   curl -X POST "http://localhost:8000/api/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com","password":"test"}'
   ```

10. **End-to-End Processing Test**
    ```bash
    # Test complete dojo pipeline if possible
    # This requires uploading a test file and monitoring processing
    ```

---

## Step 1: Environment Configuration

### 1.1 Backend Environment (.env)
```bash
# Copy and update backend environment
cp backend/.env backend/.env.production
```

Update `backend/.env.production`:
```env
ENVIRONMENT=production
DATABASE_URL=postgresql://review_user:SECURE-PASSWORD@localhost:5432/review-platform
GPU_DEVELOPMENT=135.181.71.17
GPU_PRODUCTION=135.181.63.133
FRONTEND_URL=https://your-production-domain.com
PROJECT_NAME=HALBZEIT Review Platform
SECRET_KEY=CHANGE-THIS-TO-SECURE-PRODUCTION-SECRET-KEY
API_V1_STR=/api
ACCESS_TOKEN_EXPIRE_MINUTES=11520
SHARED_FILESYSTEM_MOUNT_PATH=/mnt/CPU-GPU
UPLOAD_PATH=/mnt/CPU-GPU/uploads
BACKEND_PRODUCTION=http://65.108.32.168:8000
```

### 1.2 GPU Processing Environment
```bash
# Copy GPU environment
cp gpu_processing/.env.development gpu_processing/.env.production
```

Update `gpu_processing/.env.production`:
```env
# Production environment configuration for GPU processing
SHARED_FILESYSTEM_MOUNT_PATH=/mnt/CPU-GPU

# Database connection - use production database
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=review-platform
DATABASE_USER=review_user
DATABASE_PASSWORD=SECURE-PASSWORD
DATABASE_URL=postgresql://review_user:SECURE-PASSWORD@localhost:5432/review-platform

# Backend server URLs
BACKEND_DEVELOPMENT=http://65.108.32.143:8000
BACKEND_PRODUCTION=http://65.108.32.168:8000

# Processing configuration
PROCESSING_DEVICE=cuda
MAX_PROCESSING_TIME=300
INCLUDE_DEBUG_INFO=false
```

### 1.3 Frontend Environment
Update `frontend/.env.production`:
```env
REACT_APP_API_URL=/api
```

## Step 2: Database Schema Migration

### 2.1 Backup Existing Users
```sql
-- On production server, backup existing users
sudo -u postgres pg_dump review-platform -t users > /tmp/production_users_backup.sql
```

### 2.2 Drop and Recreate Database
```sql
-- Connect as postgres superuser
sudo -u postgres psql

-- Drop existing database (CAREFUL!)
DROP DATABASE IF EXISTS "review-platform";

-- Create fresh database
CREATE DATABASE "review-platform" OWNER review_user;
\q
```

### 2.3 Initialize New Schema
```bash
# On production server, copy schema from development
cd /path/to/production/backend

# Run database initialization (creates all tables)
python -c "
from app.db.database import engine, Base
from app.db import models
import os
os.environ['DATABASE_URL'] = 'postgresql://review_user:SECURE-PASSWORD@localhost:5432/review-platform'
Base.metadata.create_all(bind=engine)
print('All tables created successfully')
"
```

### 2.4 Restore Users
```sql
-- Restore backed up users
sudo -u postgres psql review-platform < /tmp/production_users_backup.sql
```

## Step 3: Code Deployment

### 3.1 Deploy Code to Production Server
```bash
# On production server (65.108.32.168)
cd /root/review-platform-dev
git pull origin main

# Copy production environment files
cp backend/.env.production backend/.env
cp gpu_processing/.env.production gpu_processing/.env.development
```

### 3.2 Deploy Code to GPU Server
```bash
# On GPU server (135.181.63.133)
cd /root/review-platform-dev  
git pull origin main

# Copy GPU production environment
cp gpu_processing/.env.production gpu_processing/.env.development
```

## Step 4: Service Configuration

### 4.1 Backend Service Restart
```bash
# On production server
./dev-services-improved.sh stop
./dev-services-improved.sh start

# Verify services
./dev-services-improved.sh status
```

### 4.2 Frontend Build and Deploy
```bash
# On production server
cd frontend
npm run build

# Configure nginx/apache to serve build/ directory
# Update proxy to point to localhost:8000 instead of external IP
```

## Step 5: Post-Deployment Verification

### 5.1 Database Verification
```bash
# Verify all tables exist
python -c "
from app.db.database import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT table_name FROM information_schema.tables WHERE table_schema = \\'public\\' ORDER BY table_name'))
    tables = [row[0] for row in result.fetchall()]
    expected_tables = [
        'analysis_templates', 'answers', 'chapter_analysis_results', 'chapter_questions',
        'classification_performance', 'extraction_experiments', 'gp_template_customizations',
        'healthcare_sectors', 'model_configs', 'pipeline_prompts', 'pitch_decks',
        'questions', 'reviews', 'template_chapters', 'users', 'visual_analysis_cache'
    ]
    missing = set(expected_tables) - set(tables)
    if missing:
        print(f'Missing tables: {missing}')
    else:
        print('All required tables present')
"
```

### 5.2 API Verification
```bash
# Test backend API
curl -X GET "http://localhost:8000/api/health" 

# Test auth endpoints
curl -X GET "http://localhost:8000/api/users/me" -H "Authorization: Bearer TOKEN"
```

### 5.3 GPU Communication Test
```bash
# Test GPU server connectivity
curl -X POST "http://135.181.63.133:5000/api/health"

# Test dojo functionality with small sample
```

## Step 6: DNS and Domain Configuration

### 6.1 Update DNS Records
- Point production domain to 65.108.32.168
- Configure SSL certificates
- Update CORS settings in backend

### 6.2 Environment-Specific Settings
```bash
# Update backend config for production
# Set ENVIRONMENT=production in .env
# This will automatically:
# - Use GPU_PRODUCTION for GPU calls
# - Use BACKEND_PRODUCTION for callbacks
# - Use production database
```

## Critical Success Factors

1. **Database**: Ensure all 29 tables from development are created in production
2. **Environment Variables**: All server IPs and paths must match production infrastructure  
3. **GPU Communication**: Verify GPU server can connect back to production backend
4. **File Paths**: Ensure `/mnt/CPU-GPU` is properly mounted and accessible
5. **User Data**: Preserve existing GP and startup users during database recreation

## Rollback Plan

If deployment fails:
1. Restore database from `/tmp/production_users_backup.sql`
2. Revert environment files to previous versions
3. Restart services with old configuration
4. Update DNS to point back to old version if needed

## Post-Deployment Testing Checklist

- [ ] User login works for existing users
- [ ] New user registration works
- [ ] PDF upload and processing works
- [ ] Dojo Step 2 (Visual Analysis) works
- [ ] Dojo Step 3 (Extractions) works  
- [ ] Dojo Step 4 (Template Processing) works
- [ ] Progress bars display correctly
- [ ] GPU server logs show successful processing
- [ ] Email notifications work (if configured)
- [ ] All API endpoints return correct responses

---

## 🛠️ Troubleshooting Common Issues

### Database Connection Problems
```bash
# If DATABASE_URL is malformed, check centralized environment
cat /opt/review-platform/environments/.env.backend.production

# Redeploy environment if needed
./environments/deploy-environment.sh production

# Test direct PostgreSQL connection
psql "postgresql://review_user:simpleprod2024@localhost:5432/review-platform" -c "SELECT version();"
```

### Service Startup Issues
```bash
# Check systemd service logs
sudo journalctl -f -u review-platform.service
sudo journalctl -f -u gpu-http-server.service

# Restart services in correct order
sudo systemctl stop review-platform.service
sudo systemctl start review-platform.service
```

### Environment Configuration Issues
```bash
# Verify environment is correctly deployed
./environments/deploy-environment.sh status

# Check backups if rollback needed
ls -la /opt/review-platform/environments/history/

# Restore from backup if necessary
cp /opt/review-platform/environments/history/backend.env.backup.TIMESTAMP /opt/review-platform/environments/.env.backend.production
```

### GPU Communication Problems
```bash
# Test GPU server health from production CPU
curl -X GET "http://135.181.63.133:8001/api/health"

# Check if GPU server can reach production CPU
# (Run this from GPU server)
curl -X GET "http://65.108.32.168:8000/api/health"

# Verify shared filesystem access
ls -la /mnt/CPU-GPU/
```

### Performance Monitoring
```bash
# Monitor system resources
htop
df -h /mnt/CPU-GPU/

# Check PostgreSQL performance
sudo -u postgres psql -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Monitor API response times
curl -w "@-" -o /dev/null -s "http://localhost:8000/api/health" <<< 'time_total: %{time_total}\n'
```

---

## 📝 Notes for Production CPU Tasks

### Prerequisites
- Ensure you're on the production CPU server (65.108.32.168)
- Have sudo access for systemd service management
- PostgreSQL is running and accessible
- Shared filesystem `/mnt/CPU-GPU` is properly mounted

### Critical Environment Variables to Verify
- `ENVIRONMENT=production`
- `DATABASE_URL=postgresql://review_user:simpleprod2024@localhost:5432/review-platform`
- `GPU_PRODUCTION=135.181.63.133`
- `BACKEND_PRODUCTION=http://65.108.32.168:8000`
- `SHARED_FILESYSTEM_MOUNT_PATH=/mnt/CPU-GPU`

### Success Indicators
- ✅ Backend API responding on port 8000
- ✅ Database connection successful
- ✅ GPU server can reach backend
- ✅ All 29 database tables present
- ✅ Environment variables correctly set
- ✅ Systemd services active and stable