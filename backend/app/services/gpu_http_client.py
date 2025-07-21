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
            
            async with httpx.AsyncClient(timeout=1800.0) as client:  # 30 minutes timeout
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
                "error": "Processing timeout (30 minutes exceeded)"
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
    
    async def run_visual_analysis_for_extraction_testing(self, deck_ids: List[int], vision_model: str, analysis_prompt: str, file_paths: List[str]) -> Dict[str, Any]:
        """
        Run visual analysis for extraction testing on multiple decks
        
        Args:
            deck_ids: List of pitch deck IDs
            vision_model: Vision model to use for analysis
            analysis_prompt: Custom prompt for visual analysis
            file_paths: List of PDF file paths relative to shared filesystem
            
        Returns:
            Batch processing results
        """
        try:
            if not self.gpu_host:
                logger.error("GPU_INSTANCE_HOST not configured")
                return {
                    "success": False,
                    "error": "GPU_INSTANCE_HOST not configured"
                }
            
            logger.info(f"Requesting visual analysis batch for {len(deck_ids)} decks using {vision_model}")
            
            payload = {
                "deck_ids": deck_ids,
                "vision_model": vision_model,
                "analysis_prompt": analysis_prompt,
                "file_paths": file_paths,
                "extraction_testing": True
            }
            
            async with httpx.AsyncClient(timeout=3600.0) as client:  # 1 hour timeout for batch processing
                response = await client.post(
                    f"{self.base_url}/run-visual-analysis-batch",
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    logger.info(f"Successfully processed visual analysis batch")
                    return {
                        "success": True,
                        "processed_decks": data.get("processed_decks", []),
                        "results": data.get("results", {}),
                        "message": data.get("message", "Visual analysis batch completed")
                    }
                else:
                    logger.error(f"GPU visual analysis batch failed: {data.get('error')}")
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
            logger.error(f"Timeout processing visual analysis batch")
            return {
                "success": False,
                "error": "Processing timeout (1 hour exceeded)"
            }
        except httpx.ConnectError:
            logger.error("Connection error communicating with GPU instance")
            return {
                "success": False,
                "error": "Connection error communicating with GPU instance"
            }
        except Exception as e:
            logger.error(f"Error processing visual analysis batch: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_offering_extraction(self, deck_ids: List[int], text_model: str, extraction_prompt: str, use_cached_visual: bool = True) -> Dict[str, Any]:
        """
        Run company offering extraction for multiple decks using text model
        
        Args:
            deck_ids: List of pitch deck IDs  
            text_model: Text model to use for extraction
            extraction_prompt: Custom prompt for extraction
            use_cached_visual: Whether to use cached visual analysis
            
        Returns:
            Extraction results for all decks
        """
        try:
            if not self.gpu_host:
                logger.error("GPU_INSTANCE_HOST not configured")
                return {
                    "success": False,
                    "error": "GPU_INSTANCE_HOST not configured"
                }
            
            logger.info(f"Requesting offering extraction for {len(deck_ids)} decks using {text_model}")
            
            payload = {
                "deck_ids": deck_ids,
                "text_model": text_model,
                "extraction_prompt": extraction_prompt,
                "use_cached_visual": use_cached_visual
            }
            
            async with httpx.AsyncClient(timeout=3600.0) as client:  # 1 hour timeout
                response = await client.post(
                    f"{self.base_url}/run-offering-extraction",
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    logger.info(f"Successfully completed offering extraction")
                    return {
                        "success": True,
                        "extraction_results": data.get("extraction_results", []),
                        "message": data.get("message", "Offering extraction completed")
                    }
                else:
                    logger.error(f"GPU offering extraction failed: {data.get('error')}")
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
            logger.error(f"Timeout processing offering extraction")
            return {
                "success": False,
                "error": "Processing timeout (1 hour exceeded)"
            }
        except httpx.ConnectError:
            logger.error("Connection error communicating with GPU instance")
            return {
                "success": False,
                "error": "Connection error communicating with GPU instance"
            }
        except Exception as e:
            logger.error(f"Error processing offering extraction: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_classification(self, model_name: str, prompt: str) -> Dict[str, Any]:
        """
        Run classification using the GPU instance
        
        Args:
            model_name: Name of the model to use for classification
            prompt: Classification prompt
            
        Returns:
            Classification results or error information
        """
        try:
            if not self.gpu_host:
                logger.error("GPU_INSTANCE_HOST not configured")
                return {
                    "success": False,
                    "error": "GPU_INSTANCE_HOST not configured"
                }
            
            logger.info(f"Requesting classification using model {model_name}")
            
            payload = {
                "model": model_name,
                "prompt": prompt,
                "options": {
                    "num_ctx": 32768,
                    "temperature": 0.3
                }
            }
            
            async with httpx.AsyncClient(timeout=300.0) as client:  # 5 minute timeout
                response = await client.post(
                    f"{self.base_url}/run-classification",
                    json=payload,
                    headers={'Content-Type': 'application/json'}
                )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    logger.info("Successfully completed classification")
                    return {
                        "success": True,
                        "response": data.get("response", ""),
                        "message": data.get("message", "Classification completed")
                    }
                else:
                    logger.error(f"GPU classification failed: {data.get('error')}")
                    return {
                        "success": False,
                        "error": data.get("error", "Unknown GPU classification error")
                    }
            else:
                logger.error(f"HTTP error {response.status_code}: {response.text}")
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except httpx.TimeoutException:
            logger.error("Timeout processing classification")
            return {
                "success": False,
                "error": "Classification timeout (5 minutes exceeded)"
            }
        except httpx.ConnectError:
            logger.error("Connection error communicating with GPU instance")
            return {
                "success": False,
                "error": "Connection error communicating with GPU instance"
            }
        except Exception as e:
            logger.error(f"Error processing classification: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def get_processing_progress(self, pitch_deck_id: int) -> Dict[str, Any]:
        """
        Get processing progress for a specific pitch deck
        
        Args:
            pitch_deck_id: Database ID of the pitch deck
            
        Returns:
            Progress information or error
        """
        try:
            if not self.gpu_host:
                return {
                    "success": False,
                    "error": "GPU_INSTANCE_HOST not configured"
                }
            
            response = requests.get(
                f"{self.base_url}/processing-progress/{pitch_deck_id}",
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "progress": data.get("progress", {}),
                    "status": data.get("status", "unknown"),
                    "current_step": data.get("current_step", ""),
                    "estimated_completion": data.get("estimated_completion", "")
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                
        except Exception as e:
            logger.error(f"Error getting processing progress for pitch deck {pitch_deck_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

# Global instance
gpu_http_client = GPUHTTPClient()