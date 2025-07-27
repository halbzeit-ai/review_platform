-- Create new project-centric database tables
-- Migration: Deck Analysis → Multi-Project Funding Management

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id TEXT NOT NULL,
    project_name TEXT NOT NULL,
    funding_round TEXT,
    current_stage_id INTEGER,
    funding_sought TEXT,
    healthcare_sector_id INTEGER,
    company_offering TEXT,
    project_metadata TEXT, -- JSON
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (current_stage_id) REFERENCES project_stages(id)
);

CREATE INDEX IF NOT EXISTS idx_projects_company_id ON projects(company_id);
CREATE INDEX IF NOT EXISTS idx_projects_funding_round ON projects(funding_round);

-- Create project_stages table (flexible structure for user-defined stages)
CREATE TABLE IF NOT EXISTS project_stages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    stage_name TEXT NOT NULL,
    stage_order INTEGER NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, active, completed, skipped
    stage_metadata TEXT, -- JSON for stage-specific data
    started_at DATETIME,
    completed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_stages_project_id ON project_stages(project_id);
CREATE INDEX IF NOT EXISTS idx_project_stages_order ON project_stages(project_id, stage_order);

-- Create project_documents table (replaces pitch_decks concept)
CREATE TABLE IF NOT EXISTS project_documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    document_type TEXT NOT NULL, -- pitch_deck, financial_report, publication, legal_doc, etc.
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    original_filename TEXT,
    file_size INTEGER,
    processing_status TEXT DEFAULT 'pending', -- pending, processing, completed, failed
    extracted_data TEXT, -- JSON for document-specific extractions
    analysis_results_path TEXT,
    uploaded_by INTEGER NOT NULL,
    upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_project_documents_project_id ON project_documents(project_id);
CREATE INDEX IF NOT EXISTS idx_project_documents_type ON project_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_project_documents_uploaded_by ON project_documents(uploaded_by);

-- Create project_interactions table (broader than reviews)
CREATE TABLE IF NOT EXISTS project_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    interaction_type TEXT NOT NULL, -- review, comment, question, meeting_note, etc.
    title TEXT,
    content TEXT NOT NULL,
    document_id INTEGER, -- Link to specific document if relevant
    created_by INTEGER NOT NULL,
    status TEXT DEFAULT 'active', -- active, archived
    interaction_metadata TEXT, -- JSON for interaction-specific data
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES project_documents(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_project_interactions_project_id ON project_interactions(project_id);
CREATE INDEX IF NOT EXISTS idx_project_interactions_type ON project_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_project_interactions_created_by ON project_interactions(created_by);

-- Add triggers to update projects.updated_at when related data changes
CREATE TRIGGER IF NOT EXISTS update_project_timestamp 
AFTER UPDATE ON projects
BEGIN
    UPDATE projects SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;