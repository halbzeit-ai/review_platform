#!/bin/bash

# Simple script to export production database schema
# Run this first to get the production schema before full setup

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

# Production server IP (from your screenshot)
PRODUCTION_CPU="65.108.32.168"
PROD_DB_NAME="review-platform"

echo "🔍 Exporting Production Database Schema"
echo "======================================="
echo "Production Server: $PRODUCTION_CPU"
echo "Database: $PROD_DB_NAME"
echo ""

# Create schemas directory
mkdir -p schemas

log_info "Connecting to production server to export schema..."

# Export schema from production (you'll need to adjust the connection details)
ssh -o StrictHostKeyChecking=no root@"$PRODUCTION_CPU" "pg_dump --schema-only --no-owner --no-privileges postgresql://review_user:review_password@localhost:5432/$PROD_DB_NAME" > schemas/production_schema.sql

if [ $? -eq 0 ]; then
    log_success "Production schema exported successfully!"
    echo ""
    echo "📁 Schema exported to: schemas/production_schema.sql"
    echo "📊 File size: $(du -h schemas/production_schema.sql | cut -f1)"
    echo ""
    echo "📋 Quick schema overview:"
    echo "Tables found:"
    grep -c "CREATE TABLE" schemas/production_schema.sql || echo "0"
    echo ""
    echo "Table names:"
    grep "CREATE TABLE" schemas/production_schema.sql | sed 's/CREATE TABLE /- /' | sed 's/ (.*$//' || echo "None found"
    echo ""
    log_info "You can now review the schema file and proceed with development setup"
else
    log_error "Failed to export production schema"
    log_error "Please check:"
    log_error "1. SSH access to production server"
    log_error "2. PostgreSQL credentials"
    log_error "3. Database name and connection"
    exit 1
fi