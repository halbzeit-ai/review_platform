
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text
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
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

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
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")

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
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    documents = relationship("ProjectDocument", back_populates="project")
    stages = relationship("ProjectStage", back_populates="project")
    interactions = relationship("ProjectInteraction", back_populates="project")

class ProjectStage(Base):
    __tablename__ = "project_stages"
    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"))
    stage_name = Column(String)  # User-defined funding process stages
    stage_order = Column(Integer)  # Order in the funding process
    status = Column(String, default="pending")  # pending, active, completed, skipped
    stage_metadata = Column(Text, nullable=True)  # JSON for stage-specific data
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="stages")

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
