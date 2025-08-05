-- Add must_change_password column to users table
-- This forces users to change their password on next login (for invited users)

ALTER TABLE users ADD COLUMN must_change_password BOOLEAN DEFAULT FALSE;

-- Set must_change_password to TRUE for all existing GP users (except primary admin)
-- This ensures all current GPs must change their passwords
UPDATE users 
SET must_change_password = TRUE 
WHERE role = 'gp' AND email != 'ramin@halbzeit.ai';

-- Comment for future reference
COMMENT ON COLUMN users.must_change_password IS 'Forces user to change password on next login - used for invited users';