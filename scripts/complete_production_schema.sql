-- Complete production database schema
-- Generated from development database

-- Table: analysis_templates
CREATE TABLE IF NOT EXISTS analysis_templates (
    id INTEGER NOT NULL,
    healthcare_sector_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_version VARCHAR(50) DEFAULT '1.0'::character varying,
    specialized_analysis TEXT,
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    usage_count INTEGER DEFAULT 0,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_prompt TEXT
);

ALTER TABLE analysis_templates ADD PRIMARY KEY (id);

-- Table: answers
CREATE TABLE IF NOT EXISTS answers (
    id INTEGER NOT NULL,
    question_id INTEGER,
    answer_text TEXT,
    answered_by INTEGER,
    created_at TIMESTAMP
);

ALTER TABLE answers ADD PRIMARY KEY (id);

-- Table: chapter_analysis_results
CREATE TABLE IF NOT EXISTS chapter_analysis_results (
    id INTEGER NOT NULL,
    pitch_deck_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    chapter_response TEXT,
    average_score REAL,
    weighted_score REAL,
    total_questions INTEGER,
    answered_questions INTEGER,
    processing_time REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE chapter_analysis_results ADD PRIMARY KEY (id);

-- Table: chapter_questions
CREATE TABLE IF NOT EXISTS chapter_questions (
    id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    question_id VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    order_index INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT true,
    scoring_criteria TEXT,
    healthcare_focus TEXT,
    question_prompt_template TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE chapter_questions ADD PRIMARY KEY (id);

-- Table: classification_performance
CREATE TABLE IF NOT EXISTS classification_performance (
    id INTEGER NOT NULL,
    classification_id INTEGER NOT NULL,
    was_accurate BOOLEAN,
    manual_correction_from VARCHAR(255),
    manual_correction_to VARCHAR(255),
    correction_reason TEXT,
    corrected_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE classification_performance ADD PRIMARY KEY (id);

-- Table: extraction_experiments
CREATE TABLE IF NOT EXISTS extraction_experiments (
    id INTEGER NOT NULL,
    experiment_name VARCHAR(255) NOT NULL,
    pitch_deck_ids INTEGER[] NOT NULL,
    extraction_type VARCHAR(50) NOT NULL DEFAULT 'company_offering'::character varying,
    text_model_used VARCHAR(255) NOT NULL,
    extraction_prompt TEXT NOT NULL,
    results_json TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    classification_enabled BOOLEAN DEFAULT false,
    classification_results_json TEXT,
    classification_model_used VARCHAR(255) DEFAULT NULL::character varying,
    classification_prompt_used TEXT,
    classification_completed_at TIMESTAMP,
    company_name_results_json TEXT,
    company_name_completed_at TIMESTAMP,
    funding_amount_results_json TEXT,
    funding_amount_completed_at TIMESTAMP,
    deck_date_results_json TEXT,
    deck_date_completed_at TIMESTAMP,
    template_processing_results_json TEXT,
    template_processing_completed_at TIMESTAMP
);

ALTER TABLE extraction_experiments ADD PRIMARY KEY (id);

-- Table: gp_template_customizations
CREATE TABLE IF NOT EXISTS gp_template_customizations (
    id INTEGER NOT NULL,
    gp_email VARCHAR(255) NOT NULL,
    base_template_id INTEGER NOT NULL,
    customization_name VARCHAR(255),
    customized_chapters TEXT,
    customized_questions TEXT,
    customized_weights TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE gp_template_customizations ADD PRIMARY KEY (id);

-- Table: healthcare_sectors
CREATE TABLE IF NOT EXISTS healthcare_sectors (
    id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    keywords TEXT NOT NULL,
    subcategories TEXT NOT NULL,
    confidence_threshold REAL DEFAULT 0.75,
    regulatory_requirements TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE healthcare_sectors ADD PRIMARY KEY (id);

-- Table: healthcare_templates_deprecated
CREATE TABLE IF NOT EXISTS healthcare_templates_deprecated (
    id INTEGER NOT NULL,
    template_name VARCHAR(255) NOT NULL,
    analysis_prompt TEXT NOT NULL,
    description TEXT,
    healthcare_sector_id INTEGER,
    is_active BOOLEAN DEFAULT true,
    is_default BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE healthcare_templates_deprecated ADD PRIMARY KEY (id);

-- Table: model_configs
CREATE TABLE IF NOT EXISTS model_configs (
    id INTEGER NOT NULL,
    model_name VARCHAR(255),
    model_type VARCHAR(255),
    is_active BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

ALTER TABLE model_configs ADD PRIMARY KEY (id);

-- Table: pipeline_prompts
CREATE TABLE IF NOT EXISTS pipeline_prompts (
    id INTEGER NOT NULL,
    stage_name TEXT NOT NULL,
    prompt_text TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    prompt_type VARCHAR(50),
    prompt_name VARCHAR(255),
    is_enabled BOOLEAN DEFAULT true
);

ALTER TABLE pipeline_prompts ADD PRIMARY KEY (id);

-- Table: pitch_decks
CREATE TABLE IF NOT EXISTS pitch_decks (
    id INTEGER NOT NULL,
    user_id INTEGER,
    company_id VARCHAR(255),
    file_name VARCHAR(255),
    file_path VARCHAR(255),
    results_file_path VARCHAR(255),
    s3_url VARCHAR(255),
    processing_status VARCHAR(255),
    ai_analysis_results TEXT,
    created_at TIMESTAMP,
    ai_extracted_startup_name VARCHAR(255) DEFAULT NULL::character varying,
    data_source VARCHAR(255) DEFAULT 'startup'::character varying,
    zip_filename VARCHAR(255)
);

ALTER TABLE pitch_decks ADD PRIMARY KEY (id);

-- Table: production_projects
CREATE TABLE IF NOT EXISTS production_projects (
    id INTEGER,
    company_id VARCHAR(255),
    project_name VARCHAR(255),
    funding_round VARCHAR(100),
    current_stage_id INTEGER,
    funding_sought TEXT,
    healthcare_sector_id INTEGER,
    company_offering TEXT,
    project_metadata JSONB,
    is_active BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    tags JSONB,
    is_test BOOLEAN
);

-- Table: project_documents
CREATE TABLE IF NOT EXISTS project_documents (
    id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    document_type VARCHAR(100) NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    original_filename VARCHAR(255),
    file_size BIGINT,
    processing_status VARCHAR(50) DEFAULT 'pending'::character varying,
    extracted_data JSONB,
    analysis_results_path TEXT,
    uploaded_by INTEGER NOT NULL,
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

ALTER TABLE project_documents ADD PRIMARY KEY (id);

-- Table: project_interactions
CREATE TABLE IF NOT EXISTS project_interactions (
    id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    interaction_type VARCHAR(100) NOT NULL,
    title VARCHAR(255),
    content TEXT NOT NULL,
    document_id INTEGER,
    created_by INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'active'::character varying,
    interaction_metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE project_interactions ADD PRIMARY KEY (id);

-- Table: project_progress
CREATE TABLE IF NOT EXISTS project_progress (
    project_id INTEGER,
    company_id VARCHAR(255),
    project_name VARCHAR(255),
    funding_round VARCHAR(100),
    total_stages BIGINT,
    completed_stages BIGINT,
    active_stages BIGINT,
    pending_stages BIGINT,
    completion_percentage NUMERIC,
    current_stage_name VARCHAR(255),
    current_stage_order INTEGER
);

-- Table: project_stages
CREATE TABLE IF NOT EXISTS project_stages (
    id INTEGER NOT NULL,
    project_id INTEGER NOT NULL,
    stage_name VARCHAR(255) NOT NULL,
    stage_order INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'pending'::character varying,
    stage_metadata JSONB,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    stage_template_id INTEGER,
    stage_code VARCHAR(100)
);

ALTER TABLE project_stages ADD PRIMARY KEY (id);

-- Table: projects
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER NOT NULL,
    company_id VARCHAR(255) NOT NULL,
    project_name VARCHAR(255) NOT NULL,
    funding_round VARCHAR(100),
    current_stage_id INTEGER,
    funding_sought TEXT,
    healthcare_sector_id INTEGER,
    company_offering TEXT,
    project_metadata JSONB,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags JSONB DEFAULT '[]'::jsonb,
    is_test BOOLEAN DEFAULT false
);

ALTER TABLE projects ADD PRIMARY KEY (id);

-- Table: question_analysis_results
CREATE TABLE IF NOT EXISTS question_analysis_results (
    id INTEGER NOT NULL,
    pitch_deck_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    raw_response TEXT,
    structured_response TEXT,
    score INTEGER,
    confidence_score REAL,
    processing_time REAL,
    model_used VARCHAR(100),
    prompt_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE question_analysis_results ADD PRIMARY KEY (id);

-- Table: questions
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER NOT NULL,
    review_id INTEGER,
    question_text TEXT,
    asked_by INTEGER,
    created_at TIMESTAMP
);

ALTER TABLE questions ADD PRIMARY KEY (id);

-- Table: reviews
CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER NOT NULL,
    pitch_deck_id INTEGER,
    review_data TEXT,
    s3_review_url VARCHAR(255),
    status VARCHAR(255),
    created_at TIMESTAMP
);

ALTER TABLE reviews ADD PRIMARY KEY (id);

-- Table: specialized_analysis_results
CREATE TABLE IF NOT EXISTS specialized_analysis_results (
    id INTEGER NOT NULL,
    pitch_deck_id INTEGER NOT NULL,
    analysis_type VARCHAR(100) NOT NULL,
    analysis_result TEXT,
    structured_result TEXT,
    confidence_score REAL,
    model_used VARCHAR(100),
    processing_time REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE specialized_analysis_results ADD PRIMARY KEY (id);

-- Table: stage_templates
CREATE TABLE IF NOT EXISTS stage_templates (
    id INTEGER NOT NULL,
    stage_name VARCHAR(255) NOT NULL,
    stage_code VARCHAR(100) NOT NULL,
    description TEXT,
    stage_order INTEGER NOT NULL,
    is_required BOOLEAN DEFAULT true,
    estimated_duration_days INTEGER,
    stage_metadata JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE stage_templates ADD PRIMARY KEY (id);

-- Table: startup_classifications
CREATE TABLE IF NOT EXISTS startup_classifications (
    id INTEGER NOT NULL,
    pitch_deck_id INTEGER NOT NULL,
    company_offering TEXT NOT NULL,
    primary_sector_id INTEGER,
    subcategory VARCHAR(255),
    confidence_score REAL,
    classification_reasoning TEXT,
    secondary_sector_id INTEGER,
    keywords_matched TEXT,
    template_used INTEGER,
    manual_override BOOLEAN DEFAULT false,
    manual_override_reason TEXT,
    classified_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE startup_classifications ADD PRIMARY KEY (id);

-- Table: template_chapters
CREATE TABLE IF NOT EXISTS template_chapters (
    id INTEGER NOT NULL,
    template_id INTEGER NOT NULL,
    chapter_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    weight REAL DEFAULT 1.0,
    order_index INTEGER DEFAULT 0,
    is_required BOOLEAN DEFAULT true,
    enabled BOOLEAN DEFAULT true,
    chapter_prompt_template TEXT,
    scoring_prompt_template TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    analysis_template_id INTEGER
);

ALTER TABLE template_chapters ADD PRIMARY KEY (id);

-- Table: template_performance
CREATE TABLE IF NOT EXISTS template_performance (
    id INTEGER NOT NULL,
    template_id INTEGER NOT NULL,
    pitch_deck_id INTEGER NOT NULL,
    total_processing_time REAL,
    successful_questions INTEGER,
    failed_questions INTEGER,
    average_confidence REAL,
    gp_rating INTEGER,
    gp_feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE template_performance ADD PRIMARY KEY (id);

-- Table: test_projects
CREATE TABLE IF NOT EXISTS test_projects (
    id INTEGER,
    company_id VARCHAR(255),
    project_name VARCHAR(255),
    funding_round VARCHAR(100),
    current_stage_id INTEGER,
    funding_sought TEXT,
    healthcare_sector_id INTEGER,
    company_offering TEXT,
    project_metadata JSONB,
    is_active BOOLEAN,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    tags JSONB,
    is_test BOOLEAN
);

-- Table: visual_analysis_cache
CREATE TABLE IF NOT EXISTS visual_analysis_cache (
    id INTEGER NOT NULL,
    pitch_deck_id INTEGER NOT NULL,
    analysis_result_json TEXT NOT NULL,
    vision_model_used VARCHAR(255) NOT NULL,
    prompt_used TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE visual_analysis_cache ADD PRIMARY KEY (id);

