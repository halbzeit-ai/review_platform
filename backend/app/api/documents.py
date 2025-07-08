
from fastapi import APIRouter, HTTPException, UploadFile, Depends
from ..core.storage import get_s3_client
from ..core.config import settings
from ..db.models import User
from .auth import get_current_user
import uuid

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload")
async def upload_document(
    file: UploadFile,
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "startup":
        raise HTTPException(status_code=403, detail="Only startups can upload documents")
    
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")
    
    try:
        # Generate unique filename
        file_id = str(uuid.uuid4())
        filename = f"{current_user.company_name}/{file_id}/{file.filename}"
        
        # Upload to DigitalOcean Spaces
        s3_client = get_s3_client()
        s3_client.upload_fileobj(
            file.file,
            settings.DO_SPACES_BUCKET,
            filename,
            ExtraArgs={'ACL': 'private', 'ContentType': 'application/pdf'}
        )
        
        return {
            "message": "Document uploaded successfully",
            "filename": filename
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
