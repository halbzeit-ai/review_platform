#!/bin/bash

# Script to clean up test users and all their associated data
# This will remove test users and any projects they created

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Helper functions
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }
log_section() { echo -e "\n${CYAN}═══════════════════════════════════════════════${NC}\n${CYAN}► $1${NC}\n${CYAN}═══════════════════════════════════════════════${NC}"; }

# Main cleanup function
cleanup_test_data() {
    log_section "Cleaning Test Users and Projects"
    
    # Define test user emails to remove
    TEST_USERS=(
        "test-startup@example.com"
        "test-gp@example.com"
        "test-gp-workflow@example.com"
        "testuser@startup.com"
    )
    
    log_info "Cleaning data for test users..."
    
    # Execute cleanup via PostgreSQL
    sudo -u postgres psql review-platform << EOF
-- Start transaction for atomic cleanup
BEGIN;

-- Get IDs of test users
CREATE TEMP TABLE test_user_ids AS
SELECT id, email FROM users 
WHERE email IN ('test-startup@example.com', 'test-gp@example.com', 
                'test-gp-workflow@example.com', 'testuser@startup.com');

-- Show users to be deleted
SELECT 'Users to delete:' as status;
SELECT id, email, role FROM users WHERE id IN (SELECT id FROM test_user_ids);

-- Delete all related data in correct order (respecting foreign keys)

-- 1. Delete project-related data
DELETE FROM project_stages WHERE project_id IN 
    (SELECT id FROM projects WHERE owner_id IN (SELECT id FROM test_user_ids));
    
DELETE FROM project_invitations WHERE project_id IN 
    (SELECT id FROM projects WHERE owner_id IN (SELECT id FROM test_user_ids));
    
DELETE FROM project_members WHERE project_id IN 
    (SELECT id FROM projects WHERE owner_id IN (SELECT id FROM test_user_ids));
    
DELETE FROM project_members WHERE user_id IN (SELECT id FROM test_user_ids);

DELETE FROM project_interactions WHERE project_id IN 
    (SELECT id FROM projects WHERE owner_id IN (SELECT id FROM test_user_ids));

-- 2. Delete processing and analysis data
DELETE FROM processing_progress WHERE processing_queue_id IN 
    (SELECT pq.id FROM processing_queue pq 
     JOIN project_documents pd ON pq.document_id = pd.id
     WHERE pd.uploaded_by IN (SELECT id FROM test_user_ids));

DELETE FROM processing_queue WHERE document_id IN 
    (SELECT id FROM project_documents WHERE uploaded_by IN (SELECT id FROM test_user_ids));

DELETE FROM visual_analysis_cache WHERE document_id IN 
    (SELECT id FROM project_documents WHERE uploaded_by IN (SELECT id FROM test_user_ids));

DELETE FROM extraction_experiments WHERE document_ids::text LIKE ANY(
    SELECT '%' || id || '%' FROM project_documents WHERE uploaded_by IN (SELECT id FROM test_user_ids)
);

DELETE FROM specialized_analysis_results WHERE document_id IN 
    (SELECT id FROM project_documents WHERE uploaded_by IN (SELECT id FROM test_user_ids));

-- Skip slide_feedback if it doesn't have document_id column
-- DELETE FROM slide_feedback WHERE document_id IN 
--     (SELECT id FROM project_documents WHERE uploaded_by IN (SELECT id FROM test_user_ids));

DELETE FROM reviews WHERE document_id IN 
    (SELECT id FROM project_documents WHERE uploaded_by IN (SELECT id FROM test_user_ids));

DELETE FROM answers WHERE user_id IN (SELECT id FROM test_user_ids);

DELETE FROM chapter_analysis_results WHERE document_id IN 
    (SELECT id FROM project_documents WHERE uploaded_by IN (SELECT id FROM test_user_ids));

DELETE FROM question_analysis_results WHERE document_id IN 
    (SELECT id FROM project_documents WHERE uploaded_by IN (SELECT id FROM test_user_ids));

-- 3. Delete documents
DELETE FROM project_documents WHERE uploaded_by IN (SELECT id FROM test_user_ids);
DELETE FROM project_documents WHERE project_id IN 
    (SELECT id FROM projects WHERE owner_id IN (SELECT id FROM test_user_ids));

-- 4. Delete projects
DELETE FROM projects WHERE owner_id IN (SELECT id FROM test_user_ids);

-- 5. Finally delete the test users
DELETE FROM users WHERE id IN (SELECT id FROM test_user_ids);

-- Show final results
SELECT 'Cleanup Summary:' as status;
SELECT 
    (SELECT COUNT(*) FROM users WHERE email LIKE '%test%') as remaining_test_users,
    (SELECT COUNT(*) FROM projects) as remaining_projects,
    (SELECT COUNT(*) FROM project_documents) as remaining_documents,
    (SELECT COUNT(*) FROM processing_queue) as remaining_queue_items;

-- Commit the transaction
COMMIT;

-- Show all remaining users
SELECT 'Remaining users in system:' as status;
SELECT id, email, role, company_name FROM users ORDER BY id;
EOF

    if [[ $? -eq 0 ]]; then
        log_success "Test users and all associated data cleaned successfully"
    else
        log_error "Failed to clean test users"
        return 1
    fi
}

# Reset sequences function
reset_sequences() {
    log_section "Resetting Auto-increment Sequences"
    
    sudo -u postgres psql review-platform << EOF
-- Reset sequences to start from appropriate values
SELECT setval('projects_id_seq', COALESCE((SELECT MAX(id) FROM projects), 0) + 1, false);
SELECT setval('project_documents_id_seq', COALESCE((SELECT MAX(id) FROM project_documents), 0) + 1, false);
SELECT setval('processing_queue_id_seq', COALESCE((SELECT MAX(id) FROM processing_queue), 0) + 1, false);

SELECT 'Sequences reset to:' as status;
SELECT 
    nextval('projects_id_seq') - 1 as next_project_id,
    nextval('project_documents_id_seq') - 1 as next_document_id,
    nextval('processing_queue_id_seq') - 1 as next_queue_id;
EOF

    log_success "Sequences reset successfully"
}

# Main execution
main() {
    log_section "Test User and Project Cleanup Script"
    log_warning "This will permanently delete all test users and their associated data"
    
    # Show current state
    log_info "Current database state:"
    sudo -u postgres psql review-platform -t -c "
        SELECT 
            'Test users: ' || COUNT(*) 
        FROM users 
        WHERE email IN ('test-startup@example.com', 'test-gp@example.com', 
                        'test-gp-workflow@example.com', 'testuser@startup.com');"
    
    echo ""
    read -p "Do you want to proceed with cleanup? (yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        log_warning "Cleanup cancelled"
        exit 0
    fi
    
    cleanup_test_data
    reset_sequences
    
    log_section "Cleanup Complete"
    log_success "Database is now clean and ready for fresh testing"
}

# Run main function
main "$@"