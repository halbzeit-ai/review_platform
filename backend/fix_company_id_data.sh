#!/bin/bash

# Script to fix company_id data migration
# Update existing records to populate company_id properly

echo "Fixing company_id data migration..."

# Navigate to backend directory
cd /opt/review-platform/backend

# Apply the data fix
sqlite3 sql_app.db < fix_company_id_data.sql

echo ""
echo "Verifying updated data:"
sqlite3 sql_app.db "SELECT pd.id, pd.company_id, pd.file_name, pd.results_file_path, u.email FROM pitch_decks pd JOIN users u ON pd.user_id = u.id LIMIT 5;"

echo ""
echo "Company ID data migration completed successfully!"