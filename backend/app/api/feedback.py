"""
Slide Feedback API Endpoints
Provides API endpoints for managing AI-generated slide feedback
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from ..db.database import get_db
from ..db.models import User, SlideFeedback, PitchDeck, Project
from ..api.auth import get_current_user

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
    ).order_by(SlideFeedback.slide_number).all()
    
    # Format response
    feedback_data = []
    for feedback in feedback_list:
        feedback_data.append({
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
            "total_slides": len(feedback_data),
            "slides_with_issues": len([f for f in feedback_data if f["has_issues"]]),
            "slides_ok": len([f for f in feedback_data if not f["has_issues"]]),
            "feedback": feedback_data
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