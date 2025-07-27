-- Create new project-centric database tables
-- Migration: Deck Analysis → Multi-Project Funding Management

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id SERIAL PRIMARY KEY,
    company_id VARCHAR(255) NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    funding_round VARCHAR(100),
    current_stage_id INTEGER,
    funding_sought TEXT,
    healthcare_sector_id INTEGER,
    company_offering TEXT,
    project_metadata JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_projects_company_id ON projects(company_id);
CREATE INDEX IF NOT EXISTS idx_projects_funding_round ON projects(funding_round);

-- Create project_stages table (flexible structure for user-defined stages)
CREATE TABLE IF NOT EXISTS project_stages (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    stage_name VARCHAR(255) NOT NULL,
    stage_order INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    stage_metadata JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_project_stages_project_id ON project_stages(project_id);
CREATE INDEX IF NOT EXISTS idx_project_stages_order ON project_stages(project_id, stage_order);

-- Create project_documents table (replaces pitch_decks concept)
CREATE TABLE IF NOT EXISTS project_documents (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    original_filename VARCHAR(255),
    file_size BIGINT,
    processing_status VARCHAR(50) DEFAULT 'pending',
    extracted_data JSONB,
    analysis_results_path TEXT,
    uploaded_by INTEGER NOT NULL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_project_documents_project_id ON project_documents(project_id);
CREATE INDEX IF NOT EXISTS idx_project_documents_type ON project_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_project_documents_uploaded_by ON project_documents(uploaded_by);

-- Create project_interactions table (broader than reviews)
CREATE TABLE IF NOT EXISTS project_interactions (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL,
    interaction_type VARCHAR(100) NOT NULL,
    title VARCHAR(255),
    content TEXT NOT NULL,
    document_id INTEGER,
    created_by INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    interaction_metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES project_documents(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_project_interactions_project_id ON project_interactions(project_id);
CREATE INDEX IF NOT EXISTS idx_project_interactions_type ON project_interactions(interaction_type);
CREATE INDEX IF NOT EXISTS idx_project_interactions_created_by ON project_interactions(created_by);