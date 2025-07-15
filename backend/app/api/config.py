from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import requests
import json
import logging
import os

from ..db.models import User, ModelConfig
from ..db.database import get_db
from .auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])

class ModelConfigRequest(BaseModel):
    model_name: str

class ModelConfigResponse(BaseModel):
    models: List[dict]
    active_model: Optional[str]

class AvailableModelsResponse(BaseModel):
    models: List[dict]

# Ollama API base URL (assuming it's running on the GPU instance)
OLLAMA_API_BASE = "http://127.0.0.1:11434/api"

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
        # Get installed models from Ollama
        response = requests.get(f"{OLLAMA_API_BASE}/tags", timeout=10)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch models from Ollama")
        
        ollama_data = response.json()
        models = []
        
        if "models" in ollama_data:
            for model in ollama_data["models"]:
                models.append({
                    "name": model.get("name", "Unknown"),
                    "size": model.get("size", 0),
                    "modified_at": model.get("modified_at", ""),
                    "digest": model.get("digest", "")
                })
        
        # Get active model from database
        active_model_config = db.query(ModelConfig).filter(
            ModelConfig.is_active == True
        ).first()
        
        active_model = active_model_config.model_name if active_model_config else None
        
        return ModelConfigResponse(
            models=models,
            active_model=active_model
        )
        
    except requests.RequestException as e:
        logger.error(f"Error connecting to Ollama API: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to Ollama API")
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch models")

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
        # Verify the model exists in Ollama
        response = requests.get(f"{OLLAMA_API_BASE}/tags", timeout=10)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to verify model existence")
        
        ollama_data = response.json()
        model_exists = False
        
        if "models" in ollama_data:
            for model in ollama_data["models"]:
                if model.get("name") == request.model_name:
                    model_exists = True
                    break
        
        if not model_exists:
            raise HTTPException(status_code=404, detail="Model not found in Ollama")
        
        # Deactivate all current active models
        db.query(ModelConfig).update({"is_active": False})
        
        # Set the new active model
        existing_config = db.query(ModelConfig).filter(
            ModelConfig.model_name == request.model_name
        ).first()
        
        if existing_config:
            existing_config.is_active = True
        else:
            new_config = ModelConfig(
                model_name=request.model_name,
                is_active=True
            )
            db.add(new_config)
        
        db.commit()
        
        return {"message": f"Successfully set {request.model_name} as active model"}
        
    except requests.RequestException as e:
        logger.error(f"Error connecting to Ollama API: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to Ollama API")
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
        # Start pulling the model
        pull_data = {"name": request.model_name}
        
        response = requests.post(
            f"{OLLAMA_API_BASE}/pull",
            json=pull_data,
            timeout=30  # Pulling can take time, but we'll start it async
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to start model pull")
        
        return {"message": f"Started pulling model {request.model_name}"}
        
    except requests.RequestException as e:
        logger.error(f"Error connecting to Ollama API: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to Ollama API")
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
        # Delete the model from Ollama
        delete_data = {"name": request.model_name}
        
        response = requests.delete(
            f"{OLLAMA_API_BASE}/delete",
            json=delete_data,
            timeout=10
        )
        
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to delete model")
        
        # Remove from database if it was the active model
        db.query(ModelConfig).filter(
            ModelConfig.model_name == request.model_name
        ).delete()
        
        db.commit()
        
        return {"message": f"Successfully deleted model {request.model_name}"}
        
    except requests.RequestException as e:
        logger.error(f"Error connecting to Ollama API: {e}")
        raise HTTPException(status_code=500, detail="Failed to connect to Ollama API")
    except Exception as e:
        logger.error(f"Error deleting model: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete model")