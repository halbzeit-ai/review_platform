#!/bin/bash

# Simple script to clean up test users directly
set -e

echo "Cleaning test users and data..."

sudo -u postgres psql review-platform << 'EOF'
-- Delete test users and let cascade handle dependencies
DELETE FROM users WHERE email IN (
    'test-startup@example.com',
    'test-gp@example.com', 
    'test-gp-workflow@example.com',
    'test-startup-workflow@example.com',
    'testuser@startup.com'
);

-- Show remaining users
SELECT 'Remaining users:' as status;
SELECT id, email, role, company_name FROM users ORDER BY id;

-- Clean up any orphaned data
DELETE FROM projects WHERE owner_id NOT IN (SELECT id FROM users);
DELETE FROM project_documents WHERE uploaded_by NOT IN (SELECT id FROM users);

-- Show final counts
SELECT 'Final counts:' as status;
SELECT 
    (SELECT COUNT(*) FROM users) as total_users,
    (SELECT COUNT(*) FROM projects) as total_projects,
    (SELECT COUNT(*) FROM project_documents) as total_documents;
EOF

echo "✅ Cleanup complete"