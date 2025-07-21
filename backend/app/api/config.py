from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict
import asyncio
import json
import logging
import os
from datetime import datetime

from ..db.models import User, ModelConfig
from ..db.database import get_db
from .auth import get_current_user
from ..services.gpu_http_client import gpu_http_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])

class ModelConfigRequest(BaseModel):
    model_name: str
    model_type: str  # 'vision', 'text', 'scoring', 'science'

class ModelConfigResponse(BaseModel):
    models: List[dict]
    active_models: Dict[str, Optional[str]]  # model_type -> model_name

class AvailableModelsResponse(BaseModel):
    models: List[dict]

# GPU instance communication - we need to implement this properly
# For now, we'll return mock data until GPU communication is implemented
OLLAMA_API_BASE = "http://127.0.0.1:11434/api"  # This won't work from production server

@router.get("/models", response_model=ModelConfigResponse)
async def get_models(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all installed models and the active model"""
    
    # Only GPs can access model configuration
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Only GPs can access model configuration")
    
    try:
        # Get installed models from GPU instance via HTTP
        gpu_models = gpu_http_client.get_installed_models()
        models = []
        
        for model in gpu_models:
            models.append({
                "name": model.name,
                "size": model.size,
                "modified_at": model.modified_at,
                "digest": model.digest
            })
        
        # Get active models by type from database
        active_model_configs = db.query(ModelConfig).filter(
            ModelConfig.is_active == True
        ).all()
        
        active_models = {}
        for config in active_model_configs:
            active_models[config.model_type] = config.model_name
        
        return ModelConfigResponse(
            models=models,
            active_models=active_models
        )
        
    except Exception as e:
        logger.error(f"Error communicating with GPU instance: {e}")
        # Return empty response when GPU is not available
        return ModelConfigResponse(
            models=[],
            active_models={}
        )

@router.get("/available-models", response_model=AvailableModelsResponse)
async def get_available_models(
    current_user: User = Depends(get_current_user)
):
    """Get available models that can be pulled from Ollama"""
    
    # Only GPs can access model configuration
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Only GPs can access model configuration")
    
    # Popular models that work well for text analysis
    popular_models = [
        {
            "name": "llama3.1",
            "description": "Meta's Llama 3.1 - excellent for text analysis and reasoning",
            "size": "~4.7GB"
        },
        {
            "name": "gemma2",
            "description": "Google's Gemma 2 - fast and efficient for analysis tasks",
            "size": "~1.6GB"
        },
        {
            "name": "phi3",
            "description": "Microsoft's Phi-3 - compact but powerful model",
            "size": "~2.3GB"
        },
        {
            "name": "qwen2",
            "description": "Alibaba's Qwen2 - strong multilingual capabilities",
            "size": "~4.4GB"
        },
        {
            "name": "mistral",
            "description": "Mistral AI's model - good balance of performance and speed",
            "size": "~4.1GB"
        },
        {
            "name": "codellama",
            "description": "Meta's Code Llama - specialized for code and technical analysis",
            "size": "~3.8GB"
        }
    ]
    
    return AvailableModelsResponse(models=popular_models)

@router.post("/set-active-model")
async def set_active_model(
    request: ModelConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set the active model for processing"""
    
    # Only GPs can access model configuration
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Only GPs can access model configuration")
    
    try:
        # Verify the model exists on GPU instance
        gpu_models = gpu_http_client.get_installed_models()
        model_exists = any(model.name == request.model_name for model in gpu_models)
        
        if not model_exists:
            raise HTTPException(status_code=404, detail="Model not found on GPU instance")
        
        # Deactivate all current active models of the same type
        db.query(ModelConfig).filter(
            ModelConfig.model_type == request.model_type
        ).update({"is_active": False})
        db.flush()  # Flush to ensure deactivation is committed
        
        # Set the new active model
        existing_config = db.query(ModelConfig).filter(
            ModelConfig.model_name == request.model_name,
            ModelConfig.model_type == request.model_type
        ).first()
        
        if existing_config:
            logger.info(f"Activating existing model config: {existing_config.id}")
            existing_config.is_active = True
            existing_config.updated_at = datetime.utcnow()
        else:
            logger.info(f"Creating new model config for {request.model_name} ({request.model_type})")
            new_config = ModelConfig(
                model_name=request.model_name,
                model_type=request.model_type,
                is_active=True
            )
            db.add(new_config)
        
        db.commit()
        
        return {"message": f"Successfully set {request.model_name} as active {request.model_type} model"}
        
    except Exception as e:
        logger.error(f"Error setting active model: {e}")
        raise HTTPException(status_code=500, detail="Failed to set active model")

@router.post("/pull-model")
async def pull_model(
    request: ModelConfigRequest,
    current_user: User = Depends(get_current_user)
):
    """Pull a new model from Ollama"""
    
    # Only GPs can access model configuration
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Only GPs can access model configuration")
    
    try:
        # Send pull command to GPU instance
        success = gpu_http_client.pull_model(request.model_name)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send pull command to GPU instance")
        
        return {"message": f"Started pulling model {request.model_name} on GPU instance"}
        
    except Exception as e:
        logger.error(f"Error pulling model: {e}")
        raise HTTPException(status_code=500, detail="Failed to pull model")

@router.delete("/delete-model")
async def delete_model(
    request: ModelConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a model from Ollama"""
    
    # Only GPs can access model configuration
    if current_user.role != "gp":
        raise HTTPException(status_code=403, detail="Only GPs can access model configuration")
    
    try:
        # Send delete command to GPU instance
        success = gpu_http_client.delete_model(request.model_name)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to send delete command to GPU instance")
        
        # Remove from database if it was an active model
        db.query(ModelConfig).filter(
            ModelConfig.model_name == request.model_name
        ).delete()
        
        db.commit()
        
        return {"message": f"Successfully deleted model {request.model_name} from GPU instance"}
        
    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete model")