# Production Deployment Plan

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