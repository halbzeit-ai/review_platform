# Quick Debug Guide

This guide provides 5-minute checklists for common issues in the startup review platform. **Always start here before diving deep into code.**

## Universal Debugging Steps (2 minutes)

### 1. Environment Detection
```bash
# ALWAYS run this first to understand your capabilities
./scripts/detect-claude-environment.sh

# Outputs: dev_cpu, prod_cpu, dev_gpu, prod_gpu, or local
# This determines what you can and cannot do
```

### 2. System Health Check
```bash
# Backend health
curl -s http://localhost:8000/api/health

# Services status
sudo systemctl status review-platform.service --no-pager -l
sudo systemctl status gpu-http-server.service --no-pager -l

# Database connectivity
./scripts/debug-api.sh health
```

## Common Issue Checklists

### Data Not Showing (5 minutes)

**Symptoms**: User reports missing data, empty sections, "No results" messages

```bash
# Step 1: Identify the exact page (30 seconds)
echo "❓ What is the exact URL or page title you're looking at?"
# Common pages: /startup (StartupDashboard), /dojo (DojoManagement), /project (ProjectDashboard)

# Step 2: Find the component (1 minute)
grep -r "unique text from page" frontend/src/pages/
# Or use key phrases like "Extraction Results", "Individual Results", etc.

# Step 3: Check API endpoint (2 minutes)
# Find API call in component:
grep -n "fetch\|api\." frontend/src/pages/ComponentName.js
# Test the actual API:
curl -s "http://localhost:8000/api/endpoint" | head -20

# Step 4: Check data structure (1.5 minutes)
# Compare what API returns vs what frontend expects:
grep -A5 -B5 "fieldname" frontend/src/pages/ComponentName.js
# Look for mismatched field names, null values, wrong data types
```

### Authentication Issues (3 minutes)

**Symptoms**: "Not authenticated", "403 Forbidden", login loops

```bash
# Step 1: Check if user is actually logged in
# Browser: localStorage.getItem('user')
# Backend logs: grep -i "auth\|token" /mnt/*/logs/backend.log | tail -10

# Step 2: Verify endpoint authentication requirements
grep -A5 "current_user.*Depends" backend/app/api/*.py | grep -B5 -A5 "endpoint-path"

# Step 3: Use debug endpoints instead
# Many endpoints have /api/debug/ or /api/internal/ alternatives that don't require auth
./scripts/debug-api.sh <command>
```

### UI Not Updating (4 minutes)

**Symptoms**: Changes made but browser shows old content, build seems cached

```bash
# Step 1: Verify what's actually deployed (1 minute)
# Check nginx-served version:
curl -s http://localhost/ | grep -o 'main\.[a-f0-9]*\.js'
# Check filesystem version:
ls -la /var/www/html/build/static/js/main.*.js

# Step 2: Check if it's a caching issue (30 seconds)
# Open browser dev tools -> Network tab -> Hard refresh (Ctrl+Shift+R)
# Check if files are returning 304 (cached) or 200 (fresh)

# Step 3: Force rebuild and deploy (2 minutes)
cd /opt/review-platform/frontend
rm -rf build
npm run build
sudo cp -r build/* /var/www/html/build/

# Step 4: Verify deployment (30 seconds)
curl -s http://localhost/ | grep -o 'main\.[a-f0-9]*\.js'
# Should match the file you just deployed
```

### Database/Processing Issues (4 minutes)

**Symptoms**: Processing stuck, data inconsistencies, SQL errors

```bash
# Step 1: Check processing queue (1 minute)
./scripts/debug-api.sh health
# Look for queue_size, failed_jobs, processing_errors

# Step 2: Check specific deck status (1 minute)
./scripts/debug-api.sh deck DECK_ID
# Shows processing status, file existence, table relationships

# Step 3: Check recent logs (2 minutes)
# Backend logs:
tail -f /mnt/*/logs/backend.log | grep -i "error\|exception\|failed"
# GPU processing logs:
tail -f /mnt/*/logs/gpu_http_server.log | grep -i "error\|exception"
```

### Service Management Issues (3 minutes)

**Symptoms**: Services won't start, port conflicts, permission errors

```bash
# Step 1: Check service status (30 seconds)
sudo systemctl status review-platform.service gpu-http-server.service

# Step 2: Check port conflicts (30 seconds)
lsof -i :8000 :8001 :3000
# Kill conflicting processes if needed:
sudo kill -9 PID

# Step 3: Restart services properly (1 minute)
sudo systemctl restart review-platform.service
sudo systemctl restart gpu-http-server.service

# Step 4: Check logs for errors (1 minute)
sudo journalctl -f -u review-platform.service
sudo journalctl -f -u gpu-http-server.service
```

## Emergency Fixes

### Reset Everything (5 minutes)
```bash
# Nuclear option when everything is broken:
sudo systemctl stop review-platform.service gpu-http-server.service
sudo systemctl daemon-reload
sudo systemctl start review-platform.service gpu-http-server.service
curl -s http://localhost:8000/api/health
```

### Database Connection Issues
```bash
# Test database connectivity:
./scripts/debug-api.sh health
# If database is down, check connection settings in .env files
```

### Environment Issues
```bash
# Redeploy environment configuration:
cd /opt/review-platform
./environments/deploy-environment.sh production  # or development
sudo systemctl restart review-platform.service
```

## Red Flags to Avoid

❌ **Don't assume deployment issues first** - Check if data exists in database
❌ **Don't edit .env files directly** - Use `/environments/` deployment script
❌ **Don't start services manually** - Use systemctl for production services
❌ **Don't skip environment detection** - Your capabilities depend on which server you're on
❌ **Don't hardcode paths** - Use environment variables and relative paths

## When to Escalate

If any checklist takes longer than the stated time limit, or if you encounter:
- Database corruption or schema mismatches  
- SSL certificate issues
- Network connectivity problems between servers
- Filesystem permission errors

These require deeper investigation beyond quick debugging.