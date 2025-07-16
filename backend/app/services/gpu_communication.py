"""
GPU Instance Communication Service

This service handles communication with the GPU instance for model management.
It uses the shared filesystem to trigger GPU operations and check status.
"""

import os
import json
import time
import logging
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@dataclass
class GPUModelInfo:
    name: str
    size: int
    modified_at: str
    digest: str

class GPUCommunicationService:
    """Service to communicate with GPU instance for model management"""
    
    def __init__(self):
        self.shared_fs_path = "/mnt/CPU-GPU"
        self.gpu_commands_path = f"{self.shared_fs_path}/gpu_commands"
        self.gpu_status_path = f"{self.shared_fs_path}/gpu_status"
        
        # Ensure command and status directories exist
        os.makedirs(self.gpu_commands_path, exist_ok=True)
        os.makedirs(self.gpu_status_path, exist_ok=True)
    
    async def get_installed_models(self) -> List[GPUModelInfo]:
        """
        Get list of installed models from GPU instance
        Uses shared filesystem to communicate with GPU
        """
        try:
            # Create command file for GPU to list models
            command_id = f"list_models_{int(time.time())}"
            command_file = f"{self.gpu_commands_path}/{command_id}.json"
            
            command_data = {
                "command": "list_models",
                "timestamp": datetime.now().isoformat(),
                "command_id": command_id
            }
            
            # Write command file
            with open(command_file, 'w') as f:
                json.dump(command_data, f)
            
            # Wait for response (with timeout)
            response_file = f"{self.gpu_status_path}/{command_id}_response.json"
            timeout = 30  # 30 second timeout
            start_time = time.time()
            
            while time.time() - start_time < timeout:
                if os.path.exists(response_file):
                    try:
                        with open(response_file, 'r') as f:
                            response_data = json.load(f)
                        
                        # Clean up files
                        os.remove(command_file)
                        os.remove(response_file)
                        
                        if response_data.get("success"):
                            models = []
                            for model_data in response_data.get("models", []):
                                models.append(GPUModelInfo(
                                    name=model_data.get("name", ""),
                                    size=model_data.get("size", 0),
                                    modified_at=model_data.get("modified_at", ""),
                                    digest=model_data.get("digest", "")
                                ))
                            return models
                        else:
                            logger.error(f"GPU command failed: {response_data.get('error', 'Unknown error')}")
                            return []
                    except Exception as e:
                        logger.error(f"Error reading GPU response: {e}")
                        return []
                
                await asyncio.sleep(1)
            
            # Timeout reached
            logger.warning(f"GPU command timed out: {command_id}")
            # Clean up command file
            if os.path.exists(command_file):
                os.remove(command_file)
            return []
            
        except Exception as e:
            logger.error(f"Error communicating with GPU instance: {e}")
            return []
    
    async def pull_model(self, model_name: str) -> bool:
        """
        Instruct GPU instance to pull a model
        Returns True if command was successfully sent
        """
        try:
            command_id = f"pull_model_{int(time.time())}"
            command_file = f"{self.gpu_commands_path}/{command_id}.json"
            
            command_data = {
                "command": "pull_model",
                "model_name": model_name,
                "timestamp": datetime.now().isoformat(),
                "command_id": command_id
            }
            
            # Write command file
            with open(command_file, 'w') as f:
                json.dump(command_data, f)
            
            logger.info(f"Sent pull command for model {model_name} to GPU instance")
            return True
            
        except Exception as e:
            logger.error(f"Error sending pull command to GPU: {e}")
            return False
    
    async def delete_model(self, model_name: str) -> bool:
        """
        Instruct GPU instance to delete a model
        Returns True if command was successfully sent
        """
        try:
            command_id = f"delete_model_{int(time.time())}"
            command_file = f"{self.gpu_commands_path}/{command_id}.json"
            
            command_data = {
                "command": "delete_model",
                "model_name": model_name,
                "timestamp": datetime.now().isoformat(),
                "command_id": command_id
            }
            
            # Write command file
            with open(command_file, 'w') as f:
                json.dump(command_data, f)
            
            logger.info(f"Sent delete command for model {model_name} to GPU instance")
            return True
            
        except Exception as e:
            logger.error(f"Error sending delete command to GPU: {e}")
            return False
    
    async def check_gpu_status(self) -> Dict:
        """
        Check if GPU instance is responsive
        Returns status information
        """
        try:
            # Check if there are recent status files
            status_files = []
            if os.path.exists(self.gpu_status_path):
                for file in os.listdir(self.gpu_status_path):
                    if file.endswith('_status.json'):
                        file_path = os.path.join(self.gpu_status_path, file)
                        mtime = os.path.getmtime(file_path)
                        status_files.append((file_path, mtime))
            
            # Find most recent status file
            if status_files:
                latest_status_file = max(status_files, key=lambda x: x[1])
                if time.time() - latest_status_file[1] < 300:  # 5 minutes
                    try:
                        with open(latest_status_file[0], 'r') as f:
                            status_data = json.load(f)
                        return {
                            "online": True,
                            "last_seen": datetime.fromtimestamp(latest_status_file[1]).isoformat(),
                            "status": status_data
                        }
                    except Exception as e:
                        logger.error(f"Error reading GPU status: {e}")
            
            return {
                "online": False,
                "last_seen": None,
                "status": None
            }
            
        except Exception as e:
            logger.error(f"Error checking GPU status: {e}")
            return {
                "online": False,
                "last_seen": None,
                "status": None,
                "error": str(e)
            }

# Global instance
gpu_service = GPUCommunicationService()