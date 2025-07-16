#!/bin/bash

# Script to fix database schema issues
# Add missing company_id and results_file_path columns to pitch_decks table

echo "Adding company_id and results_file_path columns to pitch_decks table..."

# Navigate to backend directory
cd /opt/review-platform/backend

# Apply the migration
sqlite3 sql_app.db < migrations/add_company_id_and_results_path.sql

# Verify the schema was updated
echo "Updated pitch_decks table schema:"
sqlite3 sql_app.db ".schema pitch_decks"

echo ""
echo "Verifying data migration:"
sqlite3 sql_app.db "SELECT id, company_id, file_name, results_file_path FROM pitch_decks LIMIT 3;"

echo ""
echo "Migration completed successfully!"