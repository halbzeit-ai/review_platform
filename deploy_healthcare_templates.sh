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

# Run database migrations
echo "  - Creating healthcare sectors table..."
sqlite3 sql_app.db < migrations/create_healthcare_templates.sql

echo "  - Inserting healthcare sectors data..."
sqlite3 sql_app.db < migrations/insert_healthcare_sectors.sql

echo "  - Inserting sample template data..."
sqlite3 sql_app.db < migrations/insert_digital_therapeutics_template.sql

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
echo "  ⚠️  TODO: Add healthcare_templates router to backend/app/main.py"
echo "  ⚠️  TODO: Add TemplateManagement route to frontend routing"
echo "  ⚠️  TODO: Update GPU processing to use HealthcareTemplateAnalyzer"
echo "  ⚠️  TODO: Add navigation links to template management"

echo ""
echo "🎉 Healthcare Template System files are ready!"
echo ""
echo "📝 Manual integration steps needed:"
echo "1. Add healthcare_templates router to backend/app/main.py:"
echo "   from .api import healthcare_templates"
echo "   app.include_router(healthcare_templates.router)"
echo ""
echo "2. Add TemplateManagement route to frontend App.js:"
echo "   <Route path='/templates' element={<TemplateManagement />} />"
echo ""
echo "3. Update GPU processing to use new analyzer:"
echo "   Replace PitchDeckAnalyzer with HealthcareTemplateAnalyzer"
echo ""
echo "4. Add navigation link to template management in GP dashboard"
echo ""
echo "🚀 After completing these steps, restart backend and frontend servers"
echo "   Backend: uvicorn app.main:app --reload"
echo "   Frontend: npm start"