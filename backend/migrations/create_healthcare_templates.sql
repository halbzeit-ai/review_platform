-- Healthcare-Focused Analysis Templates Database Schema
-- Created: 2025-07-16

-- Healthcare sector classifications
CREATE TABLE healthcare_sectors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    display_name VARCHAR(255) NOT NULL,
    description TEXT,
    keywords TEXT NOT NULL, -- JSON array of keywords
    subcategories TEXT NOT NULL, -- JSON array of subcategories
    confidence_threshold REAL DEFAULT 0.75,
    regulatory_requirements TEXT, -- JSON object with FDA, HIPAA, etc.
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Analysis templates for each healthcare sector
CREATE TABLE analysis_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    healthcare_sector_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_version VARCHAR(50) DEFAULT '1.0',
    specialized_analysis TEXT, -- JSON array of specialized analysis types
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    created_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (healthcare_sector_id) REFERENCES healthcare_sectors(id)
);

-- Analysis chapters within templates
CREATE TABLE template_chapters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    chapter_id VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    weight REAL DEFAULT 1.0,
    order_index INTEGER DEFAULT 0,
    is_required BOOLEAN DEFAULT TRUE,
    enabled BOOLEAN DEFAULT TRUE,
    chapter_prompt_template TEXT,
    scoring_prompt_template TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES analysis_templates(id),
    UNIQUE(template_id, chapter_id)
);

-- Questions within each chapter
CREATE TABLE chapter_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chapter_id INTEGER NOT NULL,
    question_id VARCHAR(100) NOT NULL,
    question_text TEXT NOT NULL,
    weight REAL DEFAULT 1.0,
    order_index INTEGER DEFAULT 0,
    enabled BOOLEAN DEFAULT TRUE,
    scoring_criteria TEXT,
    healthcare_focus TEXT, -- Why this matters in healthcare
    question_prompt_template TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chapter_id) REFERENCES template_chapters(id),
    UNIQUE(chapter_id, question_id)
);

-- Startup classifications (results of classification process)
CREATE TABLE startup_classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pitch_deck_id INTEGER NOT NULL,
    company_offering TEXT NOT NULL,
    primary_sector_id INTEGER,
    subcategory VARCHAR(255),
    confidence_score REAL,
    classification_reasoning TEXT,
    secondary_sector_id INTEGER,
    keywords_matched TEXT, -- JSON array
    template_used INTEGER,
    manual_override BOOLEAN DEFAULT FALSE,
    manual_override_reason TEXT,
    classified_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pitch_deck_id) REFERENCES pitch_decks(id),
    FOREIGN KEY (primary_sector_id) REFERENCES healthcare_sectors(id),
    FOREIGN KEY (secondary_sector_id) REFERENCES healthcare_sectors(id),
    FOREIGN KEY (template_used) REFERENCES analysis_templates(id)
);

-- Results for individual questions
CREATE TABLE question_analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pitch_deck_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    raw_response TEXT,
    structured_response TEXT, -- JSON parsed response
    score INTEGER CHECK (score >= 0 AND score <= 7),
    confidence_score REAL,
    processing_time REAL,
    model_used VARCHAR(100),
    prompt_used TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pitch_deck_id) REFERENCES pitch_decks(id),
    FOREIGN KEY (question_id) REFERENCES chapter_questions(id)
);

-- Chapter-level aggregated results
CREATE TABLE chapter_analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pitch_deck_id INTEGER NOT NULL,
    chapter_id INTEGER NOT NULL,
    chapter_response TEXT,
    average_score REAL,
    weighted_score REAL,
    total_questions INTEGER,
    answered_questions INTEGER,
    processing_time REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pitch_deck_id) REFERENCES pitch_decks(id),
    FOREIGN KEY (chapter_id) REFERENCES template_chapters(id)
);

-- Specialized analysis results (scientific hypothesis, regulatory analysis, etc.)
CREATE TABLE specialized_analysis_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pitch_deck_id INTEGER NOT NULL,
    analysis_type VARCHAR(100) NOT NULL, -- scientific_hypothesis, regulatory_analysis, etc.
    analysis_result TEXT,
    structured_result TEXT, -- JSON parsed result
    confidence_score REAL,
    model_used VARCHAR(100),
    processing_time REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pitch_deck_id) REFERENCES pitch_decks(id)
);

-- Template performance tracking
CREATE TABLE template_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    template_id INTEGER NOT NULL,
    pitch_deck_id INTEGER NOT NULL,
    total_processing_time REAL,
    successful_questions INTEGER,
    failed_questions INTEGER,
    average_confidence REAL,
    gp_rating INTEGER CHECK (gp_rating >= 1 AND gp_rating <= 5),
    gp_feedback TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES analysis_templates(id),
    FOREIGN KEY (pitch_deck_id) REFERENCES pitch_decks(id)
);

-- GP customizations of templates
CREATE TABLE gp_template_customizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    gp_email VARCHAR(255) NOT NULL,
    base_template_id INTEGER NOT NULL,
    customization_name VARCHAR(255),
    customized_chapters TEXT, -- JSON with chapter modifications
    customized_questions TEXT, -- JSON with question modifications
    customized_weights TEXT, -- JSON with weight modifications
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (base_template_id) REFERENCES analysis_templates(id)
);

-- Classification performance tracking
CREATE TABLE classification_performance (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    classification_id INTEGER NOT NULL,
    was_accurate BOOLEAN,
    manual_correction_from VARCHAR(255),
    manual_correction_to VARCHAR(255),
    correction_reason TEXT,
    corrected_by VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (classification_id) REFERENCES startup_classifications(id)
);

-- Indexes for performance
CREATE INDEX idx_pitch_deck_classification ON startup_classifications(pitch_deck_id);
CREATE INDEX idx_question_results_pitch_deck ON question_analysis_results(pitch_deck_id);
CREATE INDEX idx_chapter_results_pitch_deck ON chapter_analysis_results(pitch_deck_id);
CREATE INDEX idx_specialized_results_pitch_deck ON specialized_analysis_results(pitch_deck_id);
CREATE INDEX idx_template_performance_template ON template_performance(template_id);
CREATE INDEX idx_gp_customizations_gp ON gp_template_customizations(gp_email);
CREATE INDEX idx_classification_performance_classification ON classification_performance(classification_id);