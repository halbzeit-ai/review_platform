-- URGENT FIX: Reset the users table sequence to the correct value

-- Find the maximum user ID and set the sequence to the next value
SELECT setval('users_id_seq', (SELECT MAX(id) FROM users) + 1);

-- Verify the fix
SELECT 
    'Current max user ID: ' || MAX(id) as current_max,
    'Next ID will be: ' || (SELECT last_value FROM users_id_seq) as next_id
FROM users;