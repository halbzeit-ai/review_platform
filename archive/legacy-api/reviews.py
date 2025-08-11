
from fastapi import APIRouter

router = APIRouter(prefix="/reviews", tags=["reviews"])

@router.get("/")
def get_reviews():
    return {"status": "Not implemented yet"}
