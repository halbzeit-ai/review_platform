
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..db.database import get_db
from ..db.models import User, PitchDeck
from .auth import get_current_user

router = APIRouter(prefix="/decks", tags=["decks"])

@router.get("/")
def get_decks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get pitch decks based on user role"""
    if current_user.role == "gp":
        # GPs can see all pitch decks
        decks = db.query(PitchDeck).all()
    else:
        # Startups can only see their own pitch decks
        decks = db.query(PitchDeck).filter(PitchDeck.user_id == current_user.id).all()
    
    # Include user info for GPs
    result = []
    for deck in decks:
        deck_data = {
            "id": deck.id,
            "file_name": deck.file_name,
            "file_path": deck.file_path,
            "s3_url": deck.s3_url,
            "processing_status": deck.processing_status,
            "created_at": deck.created_at,
            "user_id": deck.user_id
        }
        if current_user.role == "gp":
            if deck.user:
                deck_data["user"] = {
                    "email": deck.user.email,
                    "company_name": deck.user.company_name
                }
            else:
                deck_data["user"] = {
                    "email": "Unknown",
                    "company_name": "Unknown"
                }
        result.append(deck_data)
    
    return {"decks": result}

@router.get("/{deck_id}")
def get_deck(deck_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get a specific pitch deck"""
    deck = db.query(PitchDeck).filter(PitchDeck.id == deck_id).first()
    if not deck:
        raise HTTPException(status_code=404, detail="Pitch deck not found")
    
    # Check if user owns this deck or is a GP
    if deck.user_id != current_user.id and current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Access denied")
    
    return deck
