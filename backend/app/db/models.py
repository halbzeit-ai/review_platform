
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
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
