
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
        # Use the same company_id generation logic as in projects.py
        from .projects import get_company_id_from_user
        user_company_id = get_company_id_from_user(current_user)
        print(f"[DEBUG] User {current_user.email} (ID: {current_user.id}) looking for decks with company_id: {user_company_id}")
        
        decks = db.query(PitchDeck).filter(
            (PitchDeck.company_id == user_company_id) | 
            (PitchDeck.user_id == current_user.id)
        ).all()
        
        print(f"[DEBUG] Found {len(decks)} decks for user {current_user.email}")
        for deck in decks:
            print(f"[DEBUG] Deck {deck.id}: user_id={deck.user_id}, company_id={deck.company_id}, file_name={deck.file_name}")
            # Check if the user_id still exists
            user_exists = db.query(User).filter(User.id == deck.user_id).first()
            if not user_exists:
                print(f"[DEBUG] ORPHANED: Deck {deck.id} references non-existent user_id {deck.user_id}")
                
        # Filter out orphaned records (where user_id doesn't exist)
        valid_decks = []
        for deck in decks:
            user_exists = db.query(User).filter(User.id == deck.user_id).first()
            if user_exists:
                valid_decks.append(deck)
            else:
                print(f"[DEBUG] Filtering out orphaned deck {deck.id}")
        
        decks = valid_decks
    
    # Include user info for GPs
    result = []
    for deck in decks:
        deck_data = {
            "id": deck.id,
            "file_name": deck.file_name,
            "filename": deck.file_name,  # Add filename alias for compatibility
            "file_path": deck.file_path,
            "results_file_path": deck.results_file_path,
            "company_id": deck.company_id,
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
    from .projects import get_company_id_from_user
    user_company_id = get_company_id_from_user(current_user)
    if (deck.user_id != current_user.id and 
        deck.company_id != user_company_id and 
        current_user.role != "gp"):
        raise HTTPException(status_code=403, detail="Access denied")
    
    return deck

@router.delete("/cleanup-orphaned")
def cleanup_orphaned_decks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Clean up orphaned pitch deck records (GP only)"""
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Only GPs can cleanup orphaned records")
    
    # Find all pitch decks with non-existent user_ids
    all_decks = db.query(PitchDeck).all()
    orphaned_decks = []
    
    for deck in all_decks:
        user_exists = db.query(User).filter(User.id == deck.user_id).first()
        if not user_exists:
            orphaned_decks.append(deck)
    
    print(f"[DEBUG] Found {len(orphaned_decks)} orphaned deck records")
    
    # Delete orphaned records
    deleted_count = 0
    for deck in orphaned_decks:
        print(f"[DEBUG] Deleting orphaned deck {deck.id}: {deck.file_name}")
        db.delete(deck)
        deleted_count += 1
    
    db.commit()
    
    return {
        "message": f"Cleanup completed. Deleted {deleted_count} orphaned records.",
        "deleted_count": deleted_count
    }
