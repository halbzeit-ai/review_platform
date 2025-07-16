#!/bin/bash

# Script to fix database schema issues
# Add missing results_file_path column to pitch_decks table

echo "Adding results_file_path column to pitch_decks table..."

# Navigate to backend directory
cd /opt/review-platform/backend

# Apply the migration
sqlite3 sql_app.db < migrations/add_results_file_path.sql

# Verify the schema was updated
echo "Updated pitch_decks table schema:"
sqlite3 sql_app.db ".schema pitch_decks"

echo "Migration completed successfully!"