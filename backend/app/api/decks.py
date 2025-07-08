
from fastapi import APIRouter

router = APIRouter(prefix="/decks", tags=["decks"])

@router.get("/")
def get_decks():
    return {"status": "Not implemented yet"}
