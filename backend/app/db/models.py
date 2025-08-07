
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text, Numeric, UniqueConstraint, Index
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import relationship, DeclarativeBase
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.orm import Mapped

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    company_name = Column(String)
    role = Column(String)  # "startup" or "gp"
    preferred_language = Column(String, default="de")  # "de" or "en", German default
    is_verified = Column(Boolean, default=False)
    verification_token = Column(String, nullable=True, index=True)
    verification_token_expires = Column(DateTime, nullable=True)
    must_change_password = Column(Boolean, default=False)  # Force password change on next login
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    owned_projects = relationship("Project", back_populates="owner", foreign_keys="Project.owner_id")

class PitchDeck(Base):
    __tablename__ = "pitch_decks"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    company_id = Column(String, index=True)  # Company identifier for project-based access
    file_name = Column(String)
    file_path = Column(String)  # Relative path in shared volume
    results_file_path = Column(String)  # Path to analysis results file
    s3_url = Column(String)  # Legacy field, kept for compatibility
    processing_status = Column(String, default="pending")  # pending, processing, completed, failed
    ai_analysis_results = Column(Text, nullable=True)  # JSON string of AI analysis results
    ai_extracted_startup_name = Column(String, nullable=True)  # AI-extracted startup name from pitch deck content
    data_source = Column(String, default="startup")  # Source: 'startup' or 'dojo'
    zip_filename = Column(String, nullable=True)  # Original ZIP filename for dojo files
    current_processing_task_id = Column(Integer, ForeignKey("processing_queue.id"), nullable=True)  # Reference to current processing task
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")
    current_processing_task = relationship("ProcessingQueue", foreign_keys=[current_processing_task_id], post_update=True)

class Review(Base):
    __tablename__ = "reviews"
    id = Column(Integer, primary_key=True, index=True)
    pitch_deck_id = Column(Integer, ForeignKey("pitch_decks.id"))
    review_data = Column(Text)
    s3_review_url = Column(String)
    status = Column(String)  # "pending", "in_review", "completed"
    created_at = Column(DateTime, default=datetime.utcnow)
    pitch_deck = relationship("PitchDeck")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"))
    question_text = Column(Text)
    asked_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    review = relationship("Review")
    user = relationship("User")

class ModelConfig(Base):
    __tablename__ = "model_configs"
    id = Column(Integer, primary_key=True, index=True)
    model_name = Column(String, index=True)
    model_type = Column(String, index=True)  # 'vision', 'text', 'scoring', 'science'
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Answer(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"))
    answer_text = Column(Text)
    answered_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    question = relationship("Question")
    user = relationship("User")

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String, index=True)  # Derived from company name
    project_name = Column(String)  # e.g., "Series A Funding", "Series B Funding"
    funding_round = Column(String)  # e.g., "seed", "series_a", "series_b"
    current_stage_id = Column(Integer, ForeignKey("project_stages.id"), nullable=True)
    funding_sought = Column(String, nullable=True)  # Extracted from initial pitch deck
    healthcare_sector_id = Column(Integer, nullable=True)  # Classification result
    company_offering = Column(Text, nullable=True)  # Description of what company offers
    project_metadata = Column(Text, nullable=True)  # JSON for additional project data
    tags = Column(Text, nullable=True)  # JSON for project tags
    is_test = Column(Boolean, default=False)  # Flag for test/dojo data
    is_active = Column(Boolean, default=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Project owner
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = relationship("ProjectDocument", back_populates="project")
    stages = relationship("ProjectStage", back_populates="project", foreign_keys="ProjectStage.project_id")
    owner = relationship("User", back_populates="owned_projects", foreign_keys=[owner_id])
    interactions = relationship("ProjectInteraction", back_populates="project")
    current_stage = relationship("ProjectStage", foreign_keys=[current_stage_id], post_update=True)

class ProjectProgress(Base):
    __tablename__ = "project_progress"
    project_id = Column(Integer, primary_key=True)  # Use project_id as primary key for SQLAlchemy
    company_id = Column(String)
    project_name = Column(String)
    funding_round = Column(String)
    total_stages = Column(Integer)
    completed_stages = Column(Integer)
    active_stages = Column(Integer)
    pending_stages = Column(Integer)
    completion_percentage = Column(Numeric)
    current_stage_name = Column(String)
    current_stage_order = Column(Integer)

class ProjectStage(Base):
    __tablename__ = "project_stages"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    stage_template_id = Column(Integer, nullable=True)  # Reference to stage template
    stage_name = Column(String)  # User-defined funding process stages
    stage_code = Column(String(50), nullable=True)  # Stage code for identification
    stage_order = Column(Integer)  # Order in the funding process
    status = Column(String, default="pending")  # pending, active, completed, skipped
    stage_metadata = Column(Text, nullable=True)  # JSON for stage-specific data
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="stages", foreign_keys=[project_id])

class ProjectDocument(Base):
    __tablename__ = "project_documents"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    document_type = Column(String)  # pitch_deck, financial_report, publication, legal_doc, etc.
    file_name = Column(String)
    file_path = Column(String)  # Relative path in shared volume
    original_filename = Column(String, nullable=True)  # Original uploaded filename
    file_size = Column(Integer, nullable=True)
    processing_status = Column(String, default="pending")  # pending, processing, completed, failed
    extracted_data = Column(Text, nullable=True)  # JSON for document-specific extractions
    analysis_results_path = Column(String, nullable=True)  # Path to analysis results file
    uploaded_by = Column(Integer, ForeignKey("users.id"))
    upload_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    project = relationship("Project", back_populates="documents")
    uploader = relationship("User")

class ProjectInteraction(Base):
    __tablename__ = "project_interactions"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    interaction_type = Column(String)  # review, comment, question, meeting_note, etc.
    title = Column(String, nullable=True)
    content = Column(Text)
    document_id = Column(Integer, ForeignKey("project_documents.id"), nullable=True)  # Link to specific document if relevant
    created_by = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="active")  # active, archived
    interaction_metadata = Column(Text, nullable=True)  # JSON for interaction-specific data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="interactions")
    document = relationship("ProjectDocument")
    creator = relationship("User")

class PipelinePrompt(Base):
    __tablename__ = "pipeline_prompts"
    id = Column(Integer, primary_key=True, index=True)
    stage_name = Column(String, nullable=False, index=True)
    prompt_text = Column(Text, nullable=False)
    is_active = Column(Boolean, default=True, index=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class VisualAnalysisCache(Base):
    __tablename__ = "visual_analysis_cache"
    id = Column(Integer, primary_key=True, index=True)
    pitch_deck_id = Column(Integer, ForeignKey("pitch_decks.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_result_json = Column(Text, nullable=False)  # Store full visual analysis JSON
    vision_model_used = Column(String(255), nullable=False)  # e.g., "gemma3:12b"
    prompt_used = Column(Text, nullable=False)  # Store the prompt used for visual analysis
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    pitch_deck = relationship("PitchDeck")

class ExtractionExperiment(Base):
    __tablename__ = "extraction_experiments"
    id = Column(Integer, primary_key=True, index=True)
    experiment_name = Column(String(255), nullable=False, index=True)
    pitch_deck_ids = Column(Text, nullable=False)  # PostgreSQL array of deck IDs in sample
    extraction_type = Column(String(50), nullable=False, default='company_offering')
    text_model_used = Column(String(255), nullable=False)  # Model used for extraction
    extraction_prompt = Column(Text, nullable=False)  # Custom prompt for extraction
    results_json = Column(Text, nullable=False)  # Store all extraction results
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Step 3.2: Classification
    classification_enabled = Column(Boolean, default=False)
    classification_results_json = Column(Text)
    classification_model_used = Column(String(255))
    classification_completed_at = Column(DateTime)
    
    # Step 3.3: Company Name
    company_name_results_json = Column(Text)
    company_name_completed_at = Column(DateTime)
    
    # Step 3.4: Funding Amount
    funding_amount_results_json = Column(Text)
    funding_amount_completed_at = Column(DateTime)
    
    # Step 3.5: Deck Date
    deck_date_results_json = Column(Text)
    deck_date_completed_at = Column(DateTime)
    
    # Step 4: Template Processing
    template_processing_results_json = Column(Text)
    template_processing_completed_at = Column(DateTime)


# Generated SQLAlchemy models for previously missing tables
# These were created from actual database schema to fix code vs database drift

class AnalysisTemplate(Base):
    __tablename__ = "analysis_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    healthcare_sector_id = Column(Integer, nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    template_version = Column(String(50))
    specialized_analysis = Column(Text)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    usage_count = Column(Integer)
    created_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow)
    analysis_prompt = Column(Text)

class ChapterAnalysisResult(Base):
    __tablename__ = "chapter_analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    pitch_deck_id = Column(Integer, ForeignKey("pitch_decks.id"), nullable=False, index=True)
    chapter_id = Column(Integer, nullable=False, index=True)
    chapter_response = Column(Text)
    average_score = Column(Numeric)
    weighted_score = Column(Numeric)
    total_questions = Column(Integer)
    answered_questions = Column(Integer)
    processing_time = Column(Numeric)
    created_at = Column(DateTime, default=datetime.utcnow)

class ChapterQuestion(Base):
    __tablename__ = "chapter_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    chapter_id = Column(Integer, nullable=False, index=True)
    question_id = Column(String(100), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    weight = Column(Numeric)
    order_index = Column(Integer)
    enabled = Column(Boolean, default=True)
    scoring_criteria = Column(Text)
    healthcare_focus = Column(Text)
    question_prompt_template = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow)

class ClassificationPerformance(Base):
    __tablename__ = "classification_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    classification_id = Column(Integer, nullable=False, index=True)
    was_accurate = Column(Boolean)
    manual_correction_from = Column(String(255))
    manual_correction_to = Column(String(255))
    correction_reason = Column(Text)
    corrected_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

class GPTemplateCustomization(Base):
    __tablename__ = "gp_template_customizations"
    
    id = Column(Integer, primary_key=True, index=True)
    gp_email = Column(String(255), nullable=False)
    base_template_id = Column(Integer, ForeignKey("analysis_templates.id"), nullable=False, index=True)
    customization_name = Column(String(255))
    customized_chapters = Column(Text)
    customized_questions = Column(Text)
    customized_weights = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow)

class HealthcareSector(Base):
    __tablename__ = "healthcare_sectors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    keywords = Column(Text, nullable=False)
    subcategories = Column(Text, nullable=False)
    confidence_threshold = Column(Numeric)
    regulatory_requirements = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow)

class HealthcareTemplateDeprecated(Base):
    __tablename__ = "healthcare_templates_deprecated"
    
    id = Column(Integer, primary_key=True, index=True)
    template_name = Column(String(255), nullable=False)
    analysis_prompt = Column(Text, nullable=False)
    description = Column(Text)
    healthcare_sector_id = Column(Integer, ForeignKey("healthcare_sectors.id"), index=True)
    is_active = Column(Boolean, default=True)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class ProductionProject(Base):
    __tablename__ = "production_projects"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String(255), index=True)
    project_name = Column(String(255))
    funding_round = Column(String(100))
    current_stage_id = Column(Integer, index=True)
    funding_sought = Column(Text)
    healthcare_sector_id = Column(Integer, ForeignKey("healthcare_sectors.id"), index=True)
    company_offering = Column(Text)
    project_metadata = Column(postgresql.JSONB)
    is_active = Column(Boolean)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    tags = Column(postgresql.JSONB)
    is_test = Column(Boolean)

# ProjectProgress is a database VIEW, not a table - no SQLAlchemy model needed
# Views are created with separate SQL statements

class QuestionAnalysisResult(Base):
    __tablename__ = "question_analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    pitch_deck_id = Column(Integer, ForeignKey("pitch_decks.id"), nullable=False, index=True)
    question_id = Column(Integer, nullable=False, index=True)
    raw_response = Column(Text)
    structured_response = Column(Text)
    score = Column(Integer)
    confidence_score = Column(Numeric)
    processing_time = Column(Numeric)
    model_used = Column(String(100))
    prompt_used = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class SpecializedAnalysisResult(Base):
    __tablename__ = "specialized_analysis_results"
    
    id = Column(Integer, primary_key=True, index=True)
    pitch_deck_id = Column(Integer, ForeignKey("pitch_decks.id"), nullable=False, index=True)
    analysis_type = Column(String(100), nullable=False)
    analysis_result = Column(Text)
    structured_result = Column(Text)
    confidence_score = Column(Numeric)
    model_used = Column(String(100))
    processing_time = Column(Numeric)
    created_at = Column(DateTime, default=datetime.utcnow)

class StageTemplate(Base):
    __tablename__ = "stage_templates"
    
    id = Column(Integer, primary_key=True, index=True)
    stage_name = Column(String(255), nullable=False, index=True)
    stage_code = Column(String(100), nullable=False)
    description = Column(Text)
    stage_order = Column(Integer, nullable=False)
    is_required = Column(Boolean, default=True)
    estimated_duration_days = Column(Integer)
    stage_metadata = Column(postgresql.JSONB)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class StartupClassification(Base):
    __tablename__ = "startup_classifications"
    
    id = Column(Integer, primary_key=True, index=True)
    pitch_deck_id = Column(Integer, ForeignKey("pitch_decks.id"), nullable=False, index=True)
    company_offering = Column(Text, nullable=False)
    primary_sector_id = Column(Integer, ForeignKey("healthcare_sectors.id"), index=True)
    subcategory = Column(String(255))
    confidence_score = Column(Numeric)
    classification_reasoning = Column(Text)
    secondary_sector_id = Column(Integer, ForeignKey("healthcare_sectors.id"), index=True)
    keywords_matched = Column(Text)
    template_used = Column(Integer)
    manual_override = Column(Boolean, default=False)
    manual_override_reason = Column(Text)
    classified_by = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

class TemplateChapter(Base):
    __tablename__ = "template_chapters"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("analysis_templates.id"), nullable=False, index=True)
    chapter_id = Column(String(100), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    weight = Column(Numeric)
    order_index = Column(Integer)
    is_required = Column(Boolean, default=True)
    enabled = Column(Boolean, default=True)
    chapter_prompt_template = Column(Text)
    scoring_prompt_template = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.utcnow)
    analysis_template_id = Column(Integer, ForeignKey("analysis_templates.id"), index=True)

class TemplatePerformance(Base):
    __tablename__ = "template_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("analysis_templates.id"), nullable=False, index=True)
    pitch_deck_id = Column(Integer, ForeignKey("pitch_decks.id"), nullable=False, index=True)
    total_processing_time = Column(Numeric)
    successful_questions = Column(Integer)
    failed_questions = Column(Integer)
    average_confidence = Column(Numeric)
    gp_rating = Column(Integer)
    gp_feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class TestProject(Base):
    __tablename__ = "test_projects"
    
    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(String(255), index=True)
    project_name = Column(String(255))
    funding_round = Column(String(100))
    current_stage_id = Column(Integer, index=True)
    funding_sought = Column(Text)
    healthcare_sector_id = Column(Integer, ForeignKey("healthcare_sectors.id"), index=True)
    company_offering = Column(Text)
    project_metadata = Column(postgresql.JSONB)
    is_active = Column(Boolean)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    tags = Column(postgresql.JSONB)
    is_test = Column(Boolean)

class ProjectInvitation(Base):
    __tablename__ = "project_invitations"
    
    id = Column(Integer, primary_key=True, index=True)
    invitation_token = Column(String(255), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    invited_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="pending", index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    accepted_at = Column(DateTime)
    expires_at = Column(DateTime, nullable=False)
    accepted_by_id = Column(Integer, ForeignKey("users.id"))
    
    # Relationships
    project = relationship("Project", backref="invitations")
    invited_by = relationship("User", foreign_keys=[invited_by_id])
    accepted_by = relationship("User", foreign_keys=[accepted_by_id])

class ProjectMember(Base):
    __tablename__ = "project_members"
    
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default="member")
    added_by_id = Column(Integer, ForeignKey("users.id"))
    added_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", backref="members")
    user = relationship("User", foreign_keys=[user_id], backref="project_memberships")
    added_by = relationship("User", foreign_keys=[added_by_id])

class SlideFeedback(Base):
    __tablename__ = "slide_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    pitch_deck_id = Column(Integer, ForeignKey("pitch_decks.id", ondelete="CASCADE"), nullable=False, index=True)
    slide_number = Column(Integer, nullable=False)
    slide_filename = Column(String(255), nullable=False)
    feedback_text = Column(Text)
    feedback_type = Column(String(50), default="ai_analysis")
    has_issues = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    pitch_deck = relationship("PitchDeck", backref="slide_feedback")
    
    # Unique constraint
    __table_args__ = (UniqueConstraint('pitch_deck_id', 'slide_number'),)


class ProcessingQueue(Base):
    __tablename__ = "processing_queue"
    
    id = Column(Integer, primary_key=True, index=True)
    pitch_deck_id = Column(Integer, ForeignKey("pitch_decks.id", ondelete="CASCADE"), nullable=False, index=True)
    task_type = Column(String(50), nullable=False, default="pdf_analysis")
    status = Column(String(20), nullable=False, default="queued")  # queued, processing, completed, failed, retry
    priority = Column(Integer, nullable=False, default=1)  # 1=normal, 2=high, 3=urgent
    
    # Task parameters
    file_path = Column(Text, nullable=False)
    company_id = Column(String(255), nullable=False)
    processing_options = Column(postgresql.JSONB, default={})
    
    # Progress tracking
    progress_percentage = Column(Integer, default=0)
    current_step = Column(String(255))
    progress_message = Column(Text)
    
    # Timing and retry logic
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    next_retry_at = Column(DateTime)
    
    # Error handling
    last_error = Column(Text)
    error_count = Column(Integer, default=0)
    
    # Locking mechanism for concurrent processing
    locked_by = Column(String(255))  # server instance identifier
    locked_at = Column(DateTime)
    lock_expires_at = Column(DateTime)
    
    # Results
    results_file_path = Column(Text)
    processing_metadata = Column(postgresql.JSONB, default={})
    
    # Relationships
    pitch_deck = relationship("PitchDeck", foreign_keys=[pitch_deck_id], backref="processing_tasks")
    progress_steps = relationship("ProcessingProgress", back_populates="processing_task", cascade="all, delete-orphan")
    dependent_tasks = relationship("TaskDependency", foreign_keys="TaskDependency.depends_on_task_id", back_populates="depends_on_task")
    dependency_tasks = relationship("TaskDependency", foreign_keys="TaskDependency.dependent_task_id", back_populates="dependent_task")
    
    # Indexes for efficient queue processing
    __table_args__ = (
        Index('idx_processing_queue_status_priority', 'status', 'priority', 'created_at'),
        Index('idx_processing_queue_pitch_deck', 'pitch_deck_id'),
        Index('idx_processing_queue_retry', 'status', 'next_retry_at'),
        Index('idx_processing_queue_lock', 'locked_by', 'lock_expires_at'),
    )


class ProcessingProgress(Base):
    __tablename__ = "processing_progress"
    
    id = Column(Integer, primary_key=True, index=True)
    processing_queue_id = Column(Integer, ForeignKey("processing_queue.id", ondelete="CASCADE"), nullable=False, index=True)
    step_name = Column(String(255), nullable=False)
    step_status = Column(String(20), nullable=False)  # started, completed, failed
    progress_percentage = Column(Integer, default=0)
    message = Column(Text)
    step_data = Column(postgresql.JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    processing_task = relationship("ProcessingQueue", back_populates="progress_steps")
    
    # Index for better query performance
    __table_args__ = (
        Index('idx_processing_progress_queue', 'processing_queue_id', 'created_at'),
    )


class ProcessingServer(Base):
    __tablename__ = "processing_servers"
    
    id = Column(String(255), primary_key=True)  # server identifier (hostname + process_id)
    server_type = Column(String(50), nullable=False)  # 'cpu', 'gpu'
    status = Column(String(20), nullable=False, default="active")  # active, inactive, maintenance
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    capabilities = Column(postgresql.JSONB, default={})
    current_load = Column(Integer, default=0)
    max_concurrent_tasks = Column(Integer, default=5)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class TaskDependency(Base):
    __tablename__ = "task_dependencies"
    
    id = Column(Integer, primary_key=True, index=True)
    dependent_task_id = Column(Integer, ForeignKey("processing_queue.id", ondelete="CASCADE"), nullable=False)
    depends_on_task_id = Column(Integer, ForeignKey("processing_queue.id", ondelete="CASCADE"), nullable=False)
    dependency_type = Column(String(50), default="completion")  # completion, success_only
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    dependent_task = relationship("ProcessingQueue", foreign_keys=[dependent_task_id], back_populates="dependency_tasks")
    depends_on_task = relationship("ProcessingQueue", foreign_keys=[depends_on_task_id], back_populates="dependent_tasks")
