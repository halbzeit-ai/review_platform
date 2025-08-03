-- Project invitations table for beta onboarding
CREATE TABLE IF NOT EXISTS project_invitations (
    id SERIAL PRIMARY KEY,
    invitation_token VARCHAR(255) UNIQUE NOT NULL,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    invited_by_id INTEGER NOT NULL REFERENCES users(id),
    status VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'expired', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accepted_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    
    -- Track who accepted (might be different email if forwarded)
    accepted_by_id INTEGER REFERENCES users(id),
    
    -- Index for lookups
    UNIQUE(project_id, email, status)
);

-- Index for faster token lookups
CREATE INDEX idx_invitation_token ON project_invitations(invitation_token);
CREATE INDEX idx_invitation_email ON project_invitations(email);
CREATE INDEX idx_invitation_status ON project_invitations(status);

-- Add owner_id to projects table if not exists
DO $$ 
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                   WHERE table_name='projects' AND column_name='owner_id') THEN
        ALTER TABLE projects ADD COLUMN owner_id INTEGER REFERENCES users(id);
        -- Set current users as owners of their projects based on pitch_decks
        UPDATE projects p 
        SET owner_id = pd.user_id 
        FROM pitch_decks pd 
        WHERE p.company_id = pd.company_id 
        AND p.owner_id IS NULL
        AND pd.user_id IS NOT NULL;
    END IF;
END $$;

-- Project members table for tracking who has access
CREATE TABLE IF NOT EXISTS project_members (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member' CHECK (role IN ('owner', 'member', 'viewer')),
    added_by_id INTEGER REFERENCES users(id),
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(project_id, user_id)
);

-- Index for faster lookups
CREATE INDEX idx_project_members_project ON project_members(project_id);
CREATE INDEX idx_project_members_user ON project_members(user_id);

-- Migrate existing project owners to members table
INSERT INTO project_members (project_id, user_id, role, added_at)
SELECT DISTINCT p.id, pd.user_id, 'owner', NOW()
FROM projects p
JOIN pitch_decks pd ON p.company_id = pd.company_id
WHERE pd.user_id IS NOT NULL
ON CONFLICT (project_id, user_id) DO NOTHING;