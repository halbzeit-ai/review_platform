# Deployment & System Management Checklist

This document provides systematic checklists for deployment, system management, and troubleshooting. **Follow these checklists to avoid deployment issues and service conflicts.**

## Pre-Deployment Checks

### Environment Detection (MANDATORY FIRST STEP)
```bash
# ALWAYS run this first to understand your server capabilities
./scripts/detect-claude-environment.sh

# Expected outputs and capabilities:
# dev_cpu (65.108.32.143) - Full development access
# prod_cpu (135.181.63.224) - Production management access  
# dev_gpu (135.181.71.17) - AI development and testing
# prod_gpu (135.181.63.133) - AI processing management
# local - Developer workstation
```

### System Health Verification
```bash
# 1. Check all services are running
sudo systemctl status review-platform.service --no-pager
sudo systemctl status gpu-http-server.service --no-pager

# 2. Verify API connectivity
curl -s http://localhost:8000/api/health
curl -s http://localhost:8001/health  # GPU service

# 3. Check database connectivity
./scripts/debug-api.sh health

# 4. Verify shared filesystem access
ls -la /mnt/dev-shared/  # Development
ls -la /mnt/CPU-GPU/     # Production
```

## Frontend Deployment

### Development Environment
```bash
# Location: /opt/review-platform-dev/frontend (on dev_cpu)
cd /opt/review-platform-dev/frontend

# Standard build and test cycle:
npm install                    # Only if package.json changed
npm run build                 # Creates build/ directory
npm test --watchAll=false     # Optional: run tests

# Local testing (development server):
DANGEROUSLY_DISABLE_HOST_CHECK=true npm start  # Port 3000

# No deployment to nginx needed in development
```

### Production Environment  
```bash
# Location: /opt/review-platform/frontend (on prod_cpu)
cd /opt/review-platform/frontend

# Zero-downtime deployment process:
npm install                           # Only if package.json changed
npm run build                        # Build optimized version
sudo cp -r build/* /var/www/html/build/  # Deploy to nginx

# Verification:
curl -s http://localhost/ | grep -o 'main\.[a-f0-9]*\.js'
ls -la /var/www/html/build/static/js/main.*.js

# Should see matching filenames indicating successful deployment
```

### Frontend Troubleshooting
```bash
# Issue: Browser shows old version
# Check 1: Verify deployed files match built files
diff -q build/index.html /var/www/html/build/index.html

# Check 2: Hard refresh browser (Ctrl+Shift+R / Cmd+Shift+R)
# Check 3: Check nginx caching headers
curl -I http://localhost/static/js/main.*.js | grep -E "Cache-Control|Expires"

# Issue: Build fails
# Check 1: Node version and dependencies
node --version
npm --version
npm ci  # Clean install

# Check 2: Check for TypeScript/ESLint errors
npm run build 2>&1 | grep -E "error|Error"
```

## Backend Deployment

### Service Management (CRITICAL: Use systemctl, not manual processes)

```bash
# CORRECT: Use systemd services
sudo systemctl restart review-platform.service
sudo systemctl status review-platform.service --no-pager -l

# INCORRECT: Manual uvicorn (creates conflicts)
# ❌ uvicorn app.main:app --host 0.0.0.0 --port 8000
# This creates port conflicts with the systemd service
```

### Environment Configuration Deployment

```bash
# MANDATORY: Use centralized environment management
cd /opt/review-platform

# Deploy environment configuration:
./environments/deploy-environment.sh development  # or production
# This updates all .env files across components

# Restart services to load new configuration:
sudo systemctl restart review-platform.service
sudo systemctl restart gpu-http-server.service

# Verification:
sudo systemctl status review-platform.service
curl -s http://localhost:8000/api/health
```

### Database Migrations

```bash
# Development database operations:
./claude-dev-helper.sh migrate migrations/filename.sql
./claude-dev-helper.sh db-check

# Production database operations (prod_cpu only):
cd /opt/review-platform/backend
python scripts/create_production_schema_final.py  # Full schema setup
sudo -u postgres psql -d review-platform -f scripts/pipeline_prompts_production.sql
```

### Backend Troubleshooting

```bash
# Issue: Service won't start
sudo journalctl -f -u review-platform.service
# Check for port conflicts, environment issues, database connectivity

# Issue: Database connection errors  
./scripts/debug-api.sh health
# Check DATABASE_HOST, credentials, PostgreSQL service status

# Issue: Environment variables not loading
grep "EnvironmentFile" /etc/systemd/system/review-platform.service
sudo systemctl daemon-reload
sudo systemctl restart review-platform.service
```

## GPU Processing Deployment

### GPU Service Management

```bash
# Check GPU service status:
sudo systemctl status gpu-http-server.service --no-pager -l

# Restart GPU processing:
sudo systemctl restart gpu-http-server.service

# Check GPU connectivity (from CPU servers):
curl -s http://GPU_SERVER_IP:8001/health

# Environment variables for GPU:
# Development GPU: 135.181.71.17
# Production GPU: 135.181.63.133
```

### Shared Filesystem Verification

```bash
# Development shared storage:
ls -la /mnt/dev-shared/uploads/
ls -la /mnt/dev-shared/results/
ls -la /mnt/dev-shared/logs/

# Production shared storage:
ls -la /mnt/CPU-GPU/uploads/
ls -la /mnt/CPU-GPU/results/  
ls -la /mnt/CPU-GPU/logs/

# Check permissions:
touch /mnt/dev-shared/test.txt && rm /mnt/dev-shared/test.txt
```

## Complete System Deployment

### Full Production Deployment (from dev to prod)

```bash
# 1. On development server (dev_cpu):
git add -A
git commit -m "Feature description

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 2. On production server (prod_cpu):  
cd /opt/review-platform
git pull origin main

# 3. Deploy environment configuration:
./environments/deploy-environment.sh production

# 4. Deploy database changes (if any):
python scripts/create_production_schema_final.py

# 5. Deploy frontend:
cd frontend
npm install  # Only if package.json changed
npm run build
sudo cp -r build/* /var/www/html/build/

# 6. Restart services:
sudo systemctl daemon-reload
sudo systemctl restart review-platform.service
sudo systemctl restart gpu-http-server.service

# 7. Verify deployment:
curl http://localhost:8000/api/health
curl http://localhost/ | grep -o 'main\.[a-f0-9]*\.js'
```

### Rollback Procedure

```bash
# 1. Revert to previous git commit:
git log --oneline -n 5  # Find previous commit
git checkout PREVIOUS_COMMIT_HASH

# 2. Redeploy with previous version:
./environments/deploy-environment.sh production
cd frontend && npm run build && sudo cp -r build/* /var/www/html/build/
sudo systemctl restart review-platform.service

# 3. Database rollback (if needed):
# Restore from backup or manually revert schema changes
```

## Monitoring & Verification

### Health Check Commands

```bash
# Complete system health check:
./scripts/debug-api.sh health              # Overall system
curl -s http://localhost:8000/api/health   # Backend API
curl -s http://localhost/                  # Frontend serving
sudo systemctl status review-platform.service gpu-http-server.service

# Check processing capabilities:
curl -s "http://localhost:8000/api/debug/environment"

# Check database connectivity:
./scripts/debug-api.sh tables
```

### Log Monitoring

```bash
# Shared filesystem logs (accessible from any server):
tail -f /mnt/dev-shared/logs/backend.log          # Development
tail -f /mnt/dev-shared/logs/gpu_http_server.log  # Development
tail -f /mnt/CPU-GPU/logs/backend.log            # Production  
tail -f /mnt/CPU-GPU/logs/gpu_http_server.log     # Production

# Service logs:
sudo journalctl -f -u review-platform.service
sudo journalctl -f -u gpu-http-server.service

# Error pattern search:
grep -i "error\|exception\|failed" /mnt/*/logs/*.log | tail -20
```

### Performance Monitoring

```bash
# Check system resources:
htop
df -h  # Disk space
free -h  # Memory usage

# Check service performance:
curl -w "@curl-format.txt" -s "http://localhost:8000/api/health"

# Database performance:
./scripts/debug-api.sh health | grep -E "database|connection|query"
```

## Security Considerations

### SSL/HTTPS Verification

```bash
# Check SSL certificate status:
openssl x509 -in /etc/letsencrypt/live/halbzeit.ai/fullchain.pem -text -noout

# Verify HTTPS is working:
curl -I https://halbzeit.ai/

# Check nginx SSL configuration:
nginx -t
grep -A10 -B5 "ssl_certificate" /etc/nginx/sites-enabled/review-platform
```

### Environment Security

```bash
# Verify no secrets in code:
grep -r "password\|secret\|key" . --exclude-dir=node_modules --exclude-dir=.git

# Check environment file permissions:
ls -la /opt/review-platform/backend/.env
ls -la /environments/.env.*

# Verify systemd environment loading:
grep "EnvironmentFile" /etc/systemd/system/*.service
```

## Emergency Procedures

### Service Recovery

```bash
# Complete service restart:
sudo systemctl stop review-platform.service gpu-http-server.service
sudo systemctl daemon-reload  
sudo systemctl start review-platform.service gpu-http-server.service

# Check if recovery successful:
sleep 10
curl -s http://localhost:8000/api/health
```

### Database Recovery

```bash
# Check database connectivity:
./scripts/debug-api.sh health

# If database is corrupted or inaccessible:
# Contact system administrator for backup restoration
# Do not attempt manual database repairs
```

### Filesystem Issues

```bash
# Check shared filesystem connectivity:
ls -la /mnt/dev-shared/ /mnt/CPU-GPU/

# If mount issues:
sudo mount -a  # Remount all filesystems
systemctl restart review-platform.service gpu-http-server.service
```

## Development vs Production Checklist

### Environment-Specific Configurations

| Aspect | Development | Production |
|--------|-------------|------------|
| Frontend URL | http://65.108.32.143:3000 | https://halbzeit.ai |
| Backend URL | http://65.108.32.143:8000 | https://halbzeit.ai/api |
| Database | review_dev@dev_cpu | review-platform@prod_cpu |
| Shared Storage | /mnt/dev-shared/ | /mnt/CPU-GPU/ |
| GPU Server | 135.181.71.17 | 135.181.63.133 |
| SSL | Not required | Required |
| Caching | Disabled/minimal | Optimized |

### Pre-Production Checklist

- [ ] All tests pass in development environment
- [ ] Environment configuration deployed via script
- [ ] Database migrations tested and ready
- [ ] Frontend build completed without errors
- [ ] SSL certificates are valid and up-to-date
- [ ] Shared filesystem permissions are correct
- [ ] GPU server connectivity verified
- [ ] Backup procedures verified
- [ ] Monitoring and alerting configured
- [ ] Rollback plan prepared

This checklist ensures systematic deployments and reduces the risk of service disruptions or configuration issues.