"""
Slide Feedback API Endpoints
Provides API endpoints for managing AI-generated slide feedback
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from ..db.database import get_db
from ..db.models import User, SlideFeedback, ProjectDocument, Project
from ..api.auth import get_current_user

class ManualFeedbackRequest(BaseModel):
    feedback_text: str
    feedback_type: str  # 'gp_feedback' or 'startup_feedback'

router = APIRouter(prefix="/feedback", tags=["feedback"])

@router.get("/projects/{company_id}/decks/{deck_id}/slide-feedback")
async def get_slide_feedback(
    company_id: str,
    deck_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all slide feedback for a specific deck"""
    
    # Verify deck exists and user has access
    deck = db.query(PitchDeck).filter(
        PitchDeck.id == deck_id,
        PitchDeck.company_id == company_id
    ).first()
    
    if not deck:
        raise HTTPException(status_code=404, detail="Pitch deck not found")
    
    # Check user access permissions
    # Startup users can only access their own decks, GPs can access all
    if current_user.role == "startup":
        # For startups, check if they own this deck/project
        from ..api.projects import get_company_id_from_user
        user_company_id = get_company_id_from_user(current_user)
        if company_id != user_company_id:
            raise HTTPException(status_code=403, detail="Access denied to this project")
    
    # Get all slide feedback for this deck
    feedback_list = db.query(SlideFeedback).filter(
        SlideFeedback.pitch_deck_id == deck_id
    ).order_by(SlideFeedback.slide_number, SlideFeedback.created_at).all()
    
    # Group feedback by slide number
    feedback_by_slide = {}
    for feedback in feedback_list:
        slide_num = feedback.slide_number
        if slide_num not in feedback_by_slide:
            feedback_by_slide[slide_num] = []
        
        feedback_by_slide[slide_num].append({
            "id": feedback.id,
            "slide_number": feedback.slide_number,
            "slide_filename": feedback.slide_filename,
            "feedback_text": feedback.feedback_text,
            "feedback_type": feedback.feedback_type,
            "has_issues": feedback.has_issues,
            "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
            "updated_at": feedback.updated_at.isoformat() if feedback.updated_at else None
        })
    
    return JSONResponse(
        status_code=200,
        content={
            "deck_id": deck_id,
            "company_id": company_id,
            "total_slides": len(set(f.slide_number for f in feedback_list)),
            "total_feedback_entries": len(feedback_list),
            "feedback": feedback_by_slide
        }
    )

@router.get("/projects/{company_id}/decks/{deck_id}/slides/{slide_number}/feedback")
async def get_slide_specific_feedback(
    company_id: str,
    deck_id: int,
    slide_number: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get feedback for a specific slide"""
    
    # Verify deck exists and user has access
    deck = db.query(PitchDeck).filter(
        PitchDeck.id == deck_id,
        PitchDeck.company_id == company_id
    ).first()
    
    if not deck:
        raise HTTPException(status_code=404, detail="Pitch deck not found")
    
    # Check user access permissions
    if current_user.role == "startup":
        from ..api.projects import get_company_id_from_user
        user_company_id = get_company_id_from_user(current_user)
        if company_id != user_company_id:
            raise HTTPException(status_code=403, detail="Access denied to this project")
    
    # Get feedback for specific slide
    feedback = db.query(SlideFeedback).filter(
        SlideFeedback.pitch_deck_id == deck_id,
        SlideFeedback.slide_number == slide_number
    ).first()
    
    if not feedback:
        raise HTTPException(status_code=404, detail=f"No feedback found for slide {slide_number}")
    
    return JSONResponse(
        status_code=200,
        content={
            "deck_id": deck_id,
            "company_id": company_id,
            "slide_number": feedback.slide_number,
            "slide_filename": feedback.slide_filename,
            "feedback_text": feedback.feedback_text,
            "feedback_type": feedback.feedback_type,
            "has_issues": feedback.has_issues,
            "created_at": feedback.created_at.isoformat() if feedback.created_at else None,
            "updated_at": feedback.updated_at.isoformat() if feedback.updated_at else None
        }
    )

@router.get("/projects/{company_id}/decks/{deck_id}/feedback-summary")
async def get_deck_feedback_summary(
    company_id: str,
    deck_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a summary of all feedback for a deck"""
    
    # Verify deck exists and user has access
    deck = db.query(PitchDeck).filter(
        PitchDeck.id == deck_id,
        PitchDeck.company_id == company_id
    ).first()
    
    if not deck:
        raise HTTPException(status_code=404, detail="Pitch deck not found")
    
    # Check user access permissions
    if current_user.role == "startup":
        from ..api.projects import get_company_id_from_user
        user_company_id = get_company_id_from_user(current_user)
        if company_id != user_company_id:
            raise HTTPException(status_code=403, detail="Access denied to this project")
    
    # Get feedback statistics
    from sqlalchemy import func
    
    feedback_stats = db.query(
        func.count(SlideFeedback.id).label('total_slides'),
        func.count(SlideFeedback.id).filter(SlideFeedback.has_issues == True).label('slides_with_issues'),
        func.count(SlideFeedback.id).filter(SlideFeedback.has_issues == False).label('slides_ok')
    ).filter(
        SlideFeedback.pitch_deck_id == deck_id
    ).first()
    
    return JSONResponse(
        status_code=200,
        content={
            "deck_id": deck_id,
            "company_id": company_id,
            "deck_name": deck.file_name,
            "total_slides": feedback_stats.total_slides or 0,
            "slides_with_issues": feedback_stats.slides_with_issues or 0,
            "slides_ok": feedback_stats.slides_ok or 0,
            "feedback_coverage": (feedback_stats.total_slides / 100.0) if feedback_stats.total_slides else 0.0,
            "last_generated": None  # TODO: Add timestamp from latest feedback
        }
    )

@router.post("/projects/{company_id}/decks/{deck_id}/slides/{slide_number}/feedback")
async def add_manual_feedback(
    company_id: str,
    deck_id: int,
    slide_number: int,
    feedback_request: ManualFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add manual feedback for a specific slide"""
    
    # Verify deck exists and user has access
    deck = db.query(PitchDeck).filter(
        PitchDeck.id == deck_id,
        PitchDeck.company_id == company_id
    ).first()
    
    if not deck:
        raise HTTPException(status_code=404, detail="Pitch deck not found")
    
    # Check user access permissions
    if current_user.role == "startup":
        from ..api.projects import get_company_id_from_user
        user_company_id = get_company_id_from_user(current_user)
        if company_id != user_company_id:
            raise HTTPException(status_code=403, detail="Access denied to this project")
    
    # Create new manual feedback entry
    try:
        new_feedback = SlideFeedback(
            pitch_deck_id=deck_id,
            slide_number=slide_number,
            slide_filename=f"slide_{slide_number:03d}.jpg",  # Standard filename format
            feedback_text=feedback_request.feedback_text,
            feedback_type=feedback_request.feedback_type,
            has_issues=True,  # Manual feedback always indicates something worth noting
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_feedback)
        db.commit()
        db.refresh(new_feedback)
        
        return JSONResponse(
            status_code=201,
            content={
                "message": "Feedback added successfully",
                "feedback": {
                    "id": new_feedback.id,
                    "deck_id": deck_id,
                    "company_id": company_id,
                    "slide_number": new_feedback.slide_number,
                    "slide_filename": new_feedback.slide_filename,
                    "feedback_text": new_feedback.feedback_text,
                    "feedback_type": new_feedback.feedback_type,
                    "has_issues": new_feedback.has_issues,
                    "created_at": new_feedback.created_at.isoformat(),
                    "updated_at": new_feedback.updated_at.isoformat()
                }
            }
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to add feedback: {str(e)}")