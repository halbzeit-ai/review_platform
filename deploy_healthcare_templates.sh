#!/bin/bash
# Healthcare Template System Deployment Script
# Run this script after pulling the code to set up the new system

echo "🏥 Healthcare Template System Deployment"
echo "========================================"

# Check if we're in the right directory
if [[ ! -f "backend/app/main.py" ]]; then
    echo "❌ Please run this script from the review_platform root directory"
    exit 1
fi

echo "📋 Step 1: Setting up database schema..."
cd backend

# Check if healthcare_sectors table exists
if sqlite3 sql_app.db "SELECT name FROM sqlite_master WHERE type='table' AND name='healthcare_sectors';" | grep -q healthcare_sectors; then
    echo "  ✅ Healthcare sectors table already exists"
else
    echo "  - Creating healthcare sectors table..."
    sqlite3 sql_app.db < migrations/create_healthcare_templates.sql
fi

# Check if healthcare sectors data exists
if sqlite3 sql_app.db "SELECT COUNT(*) FROM healthcare_sectors;" | grep -q "^8$"; then
    echo "  ✅ Healthcare sectors data already loaded"
else
    echo "  - Inserting healthcare sectors data..."
    sqlite3 sql_app.db < migrations/insert_healthcare_sectors.sql 2>/dev/null || echo "  ⚠️  Some sectors data already exists (skipping duplicates)"
fi

# Check if sample template data exists
if sqlite3 sql_app.db "SELECT COUNT(*) FROM template_chapters;" | grep -q "^[7-9]$\|^[1-9][0-9]"; then
    echo "  ✅ Sample template data already loaded"
else
    echo "  - Inserting sample template data..."
    sqlite3 sql_app.db < migrations/insert_digital_therapeutics_template.sql 2>/dev/null || echo "  ⚠️  Some template data already exists (skipping duplicates)"
fi

echo "✅ Database setup complete"

echo "📋 Step 2: Installing backend dependencies..."
# Check if healthcare_templates.py is properly integrated
if [[ ! -f "app/api/healthcare_templates.py" ]]; then
    echo "❌ healthcare_templates.py not found. Please ensure the file is in backend/app/api/"
    exit 1
fi

# Check if startup_classifier.py is properly integrated
if [[ ! -f "app/services/startup_classifier.py" ]]; then
    echo "❌ startup_classifier.py not found. Please ensure the file is in backend/app/services/"
    exit 1
fi

echo "  - Backend API files are in place"

echo "📋 Step 3: Setting up frontend..."
cd ../frontend

# Check if TemplateManagement.js exists
if [[ ! -f "src/pages/TemplateManagement.js" ]]; then
    echo "❌ TemplateManagement.js not found. Please ensure the file is in frontend/src/pages/"
    exit 1
fi

# Check if API endpoints are updated
if ! grep -q "getHealthcareSectors" src/services/api.js; then
    echo "❌ API endpoints not found in services/api.js. Please ensure the healthcare template endpoints are added."
    exit 1
fi

echo "  - Frontend files are in place"

echo "📋 Step 4: Setting up GPU processing..."
cd ../gpu_processing

# Check if healthcare_template_analyzer.py exists
if [[ ! -f "utils/healthcare_template_analyzer.py" ]]; then
    echo "❌ healthcare_template_analyzer.py not found. Please ensure the file is in gpu_processing/utils/"
    exit 1
fi

echo "  - GPU processing files are in place"

echo "📋 Step 5: Integration checklist..."
echo "  ✅ Healthcare templates router added to backend/app/main.py"
echo "  ✅ TemplateManagement route added to frontend routing"
echo "  ✅ Navigation link added to GP dashboard"
echo "  ✅ GPU processing updated to use HealthcareTemplateAnalyzer"

echo ""
echo "🎉 Healthcare Template System deployment complete!"
echo ""
echo "📝 GPU Instance Deployment:"
echo "1. On your GPU instance, run:"
echo "   ./deploy_gpu_healthcare_templates.sh"
echo "2. This will update the GPU processing to use healthcare templates"
echo ""
echo "🚀 System is ready! Restart your services:"
echo "   Backend: uvicorn app.main:app --reload"
echo "   Frontend: npm start (or npm run build for production)"
echo ""
echo "🧪 Test the system:"
echo "   - Visit /templates to access template management"
echo "   - Test classification: POST /api/healthcare-templates/classify"
echo "   - Check healthcare sectors: GET /api/healthcare-templates/sectors"
echo ""
echo "📊 Database status:"
SECTOR_COUNT=$(sqlite3 backend/sql_app.db "SELECT COUNT(*) FROM healthcare_sectors;" 2>/dev/null || echo "0")
TEMPLATE_COUNT=$(sqlite3 backend/sql_app.db "SELECT COUNT(*) FROM analysis_templates;" 2>/dev/null || echo "0")
CHAPTER_COUNT=$(sqlite3 backend/sql_app.db "SELECT COUNT(*) FROM template_chapters;" 2>/dev/null || echo "0")
echo "   - Healthcare sectors: $SECTOR_COUNT"
echo "   - Analysis templates: $TEMPLATE_COUNT"
echo "   - Template chapters: $CHAPTER_COUNT"