"""
GPU HTTP Client for Production Server

This client communicates with the GPU instance via HTTP API,
replacing the NFS-based communication system.
"""

import requests
import httpx
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from ..core.config import settings

logger = logging.getLogger(__name__)

@dataclass
class GPUModelInfo:
    name: str
    size: int
    modified_at: str
    digest: str

class GPUHTTPClient:
    """HTTP client for GPU model management"""
    
    def __init__(self, gpu_host: Optional[str] = None):
        self.gpu_host = gpu_host or settings.GPU_INSTANCE_HOST
        self.base_url = f"http://{self.gpu_host}:8001/api"
        self.timeout = 30
        self.pull_timeout = 300  # 5 minutes for model pulls
        
        if not self.gpu_host:
            logger.warning("GPU_INSTANCE_HOST not configured")
    
    def is_available(self) -> bool:
        """Check if GPU instance is available"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"GPU instance not available: {e}")
            return False
    
    def get_installed_models(self) -> List[GPUModelInfo]:
        """
        Get list of installed models from GPU instance
        """
        try:
            if not self.gpu_host:
                logger.error("GPU_INSTANCE_HOST not configured")
                return []
            
            logger.info(f"Requesting models from GPU instance: {self.gpu_host}")
            
            response = requests.get(
                f"{self.base_url}/models",
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    models = []
                    for model_data in data.get("models", []):
                        models.append(GPUModelInfo(
                            name=model_data.get("name", ""),
                            size=model_data.get("size", 0),
                            modified_at=model_data.get("modified_at", ""),
                            digest=model_data.get("digest", "")
                        ))
                    logger.info(f"Successfully retrieved {len(models)} models")
                    return models
                else:
                    logger.error(f"GPU API returned error: {data.get('error', 'Unknown error')}")
                    return []
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return []
                
        except requests.exceptions.Timeout:
            logger.error("Timeout communicating with GPU instance")
            return []
        except requests.exceptions.ConnectionError:
            logger.error("Connection error communicating with GPU instance")
            return []
        except Exception as e:
            logger.error(f"Error communicating with GPU instance: {e}")
            return []
    
    def pull_model(self, model_name: str) -> bool:
        """
        Instruct GPU instance to pull a model
        Returns True if successful
        """
        try:
            if not self.gpu_host:
                logger.error("GPU_INSTANCE_HOST not configured")
                return False
            
            logger.info(f"Requesting pull for model {model_name} from GPU instance")
            
            response = requests.post(
                f"{self.base_url}/models/{model_name}",
                timeout=self.pull_timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    logger.info(f"Successfully pulled model {model_name}")
                    return True
                else:
                    logger.error(f"Failed to pull model {model_name}: {data.get('error')}")
                    return False
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout pulling model {model_name}")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Connection error communicating with GPU instance")
            return False
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return False
    
    def delete_model(self, model_name: str) -> bool:
        """
        Instruct GPU instance to delete a model
        Returns True if successful
        """
        try:
            if not self.gpu_host:
                logger.error("GPU_INSTANCE_HOST not configured")
                return False
            
            logger.info(f"Requesting deletion of model {model_name} from GPU instance")
            
            response = requests.delete(
                f"{self.base_url}/models/{model_name}",
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    logger.info(f"Successfully deleted model {model_name}")
                    return True
                else:
                    logger.error(f"Failed to delete model {model_name}: {data.get('error')}")
                    return False
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout deleting model {model_name}")
            return False
        except requests.exceptions.ConnectionError:
            logger.error("Connection error communicating with GPU instance")
            return False
        except Exception as e:
            logger.error(f"Error deleting model {model_name}: {e}")
            return False
    
    def check_gpu_status(self) -> Dict[str, Any]:
        """
        Check GPU instance status
        Returns status information
        """
        try:
            if not self.gpu_host:
                return {
                    "online": False,
                    "error": "GPU_INSTANCE_HOST not configured"
                }
            
            response = requests.get(
                f"{self.base_url}/health",
                timeout=5,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "online": True,
                    "status": data.get("status", "unknown"),
                    "ollama_available": data.get("ollama_available", False),
                    "timestamp": data.get("timestamp", "")
                }
            else:
                return {
                    "online": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except requests.exceptions.ConnectionError:
            return {
                "online": False,
                "error": "Connection refused"
            }
        except requests.exceptions.Timeout:
            return {
                "online": False,
                "error": "Request timeout"
            }
        except Exception as e:
            return {
                "online": False,
                "error": str(e)
            }
    
    async def process_pdf(self, pitch_deck_id: int, file_path: str, company_id: str) -> Dict[str, Any]:
        """
        Process a PDF file using the GPU instance
        
        Args:
            pitch_deck_id: Database ID of the pitch deck
            file_path: Path to PDF file relative to shared filesystem
            company_id: Company ID for creating project directories
            
        Returns:
            Processing results or error information
        """
        try:
            if not self.gpu_host:
                logger.error("GPU_INSTANCE_HOST not configured")
                return {
                    "success": False,
                    "error": "GPU_INSTANCE_HOST not configured"
                }
            
            logger.info(f"Requesting PDF processing for pitch deck {pitch_deck_id}: {file_path} for company {company_id}")
            
            payload = {
                "pitch_deck_id": pitch_deck_id,
                "file_path": file_path,
                "company_id": company_id
            }
            
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    f"{self.base_url}/process-pdf",
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    logger.info(f"Successfully processed PDF {file_path}")
                    return {
                        "success": True,
                        "results_file": data.get("results_file"),
                        "results_path": data.get("results_path"),
                        "message": data.get("message", "PDF processed successfully")
                    }
                else:
                    logger.error(f"GPU processing failed: {data.get('error')}")
                    return {
                        "success": False,
                        "error": data.get("error", "Unknown GPU processing error")
                    }
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except httpx.TimeoutException:
            logger.error(f"Timeout processing PDF {file_path}")
            return {
                "success": False,
                "error": "Processing timeout (5 minutes exceeded)"
            }
        except httpx.ConnectError:
            logger.error("Connection error communicating with GPU instance")
            return {
                "success": False,
                "error": "Connection error communicating with GPU instance"
            }
        except Exception as e:
            logger.error(f"Error processing PDF {file_path}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Global instance
gpu_http_client = GPUHTTPClient()