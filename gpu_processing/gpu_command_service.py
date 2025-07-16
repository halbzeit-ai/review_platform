#!/usr/bin/env python3
"""
GPU Command Service

This service runs on the GPU instance and monitors the shared filesystem
for commands from the production server. It executes Ollama commands
and writes responses back to the shared filesystem.
"""

import os
import json
import time
import logging
import asyncio
import ollama
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Reduce verbosity of HTTP libraries
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

class GPUCommandService:
    """Service that monitors for commands and executes them on GPU instance"""
    
    def __init__(self, shared_fs_path: str = "/mnt/CPU-GPU"):
        self.shared_fs_path = shared_fs_path
        self.commands_path = f"{shared_fs_path}/gpu_commands"
        self.status_path = f"{shared_fs_path}/gpu_status"
        
        # Ensure directories exist
        os.makedirs(self.commands_path, exist_ok=True)
        os.makedirs(self.status_path, exist_ok=True)
        
        # Track processed commands to avoid duplicates
        self.processed_commands = set()
        
        logger.info(f"GPU Command Service initialized. Monitoring: {self.commands_path}")
    
    async def start_monitoring(self):
        """Start monitoring for commands"""
        logger.info("Starting GPU command monitoring service...")
        
        while True:
            try:
                # Check for new command files
                await self.process_pending_commands()
                
                # Update status
                await self.update_status()
                
                # Wait before next check
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(10)  # Wait longer on error
    
    async def process_pending_commands(self):
        """Process any pending command files"""
        try:
            if not os.path.exists(self.commands_path):
                logger.warning(f"Commands path does not exist: {self.commands_path}")
                return
            
            # Get all command files
            command_files = [f for f in os.listdir(self.commands_path) if f.endswith('.json')]
            logger.info(f"Found {len(command_files)} command files: {command_files}")
            
            for command_file in command_files:
                command_path = os.path.join(self.commands_path, command_file)
                
                # Skip if already processed
                if command_file in self.processed_commands:
                    # Try to clean up old processed command file
                    try:
                        os.remove(command_path)
                        logger.info(f"Cleaned up old command file: {command_file}")
                    except OSError:
                        pass  # File might not exist or be removable
                    continue
                
                try:
                    # Read command
                    with open(command_path, 'r') as f:
                        command_data = json.load(f)
                    
                    logger.info(f"Processing command: {command_data.get('command', 'unknown')}")
                    
                    # Execute command
                    response = await self.execute_command(command_data)
                    
                    # Write response
                    await self.write_response(command_data.get('command_id'), response)
                    
                    # Mark as processed
                    self.processed_commands.add(command_file)
                    
                    # Clean up the command file after processing
                    try:
                        os.remove(command_path)
                        logger.info(f"Cleaned up processed command file: {command_file}")
                    except OSError:
                        pass  # File might not exist or be removable
                    
                    # Clean up old processed commands (keep last 100)
                    if len(self.processed_commands) > 100:
                        self.processed_commands = set(list(self.processed_commands)[-50:])
                    
                except Exception as e:
                    logger.error(f"Error processing command {command_file}: {e}")
                    
                    # Write error response
                    if 'command_data' in locals():
                        error_response = {
                            "success": False,
                            "error": str(e),
                            "timestamp": datetime.now().isoformat()
                        }
                        await self.write_response(command_data.get('command_id'), error_response)
        
        except Exception as e:
            logger.error(f"Error in process_pending_commands: {e}")
    
    async def execute_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a command and return response"""
        command = command_data.get('command')
        
        try:
            if command == 'list_models':
                return await self.list_models()
            elif command == 'pull_model':
                return await self.pull_model(command_data.get('model_name'))
            elif command == 'delete_model':
                return await self.delete_model(command_data.get('model_name'))
            else:
                return {
                    "success": False,
                    "error": f"Unknown command: {command}",
                    "timestamp": datetime.now().isoformat()
                }
        
        except Exception as e:
            logger.error(f"Error executing command {command}: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def list_models(self) -> Dict[str, Any]:
        """List installed models"""
        try:
            # Use ollama.list() to get installed models
            models_response = ollama.list()
            
            models = []
            for model in models_response.get('models', []):
                # Handle both dict and Model object formats
                if hasattr(model, 'model'):
                    # Model object format (newer Ollama versions)
                    model_name = str(model.model)
                    model_size = int(model.size)
                    model_digest = str(model.digest)
                    modified_at = model.modified_at.isoformat() if hasattr(model.modified_at, 'isoformat') else str(model.modified_at)
                else:
                    # Dict format (older versions)
                    model_name = str(model.get('name', '') or model.get('model', ''))
                    model_size = int(model.get('size', 0))
                    model_digest = str(model.get('digest', ''))
                    modified_at = model.get('modified_at', '')
                    if hasattr(modified_at, 'isoformat'):
                        modified_at = modified_at.isoformat()
                    elif modified_at is None:
                        modified_at = ''
                    else:
                        modified_at = str(modified_at)
                
                models.append({
                    "name": model_name,
                    "size": model_size,
                    "modified_at": modified_at,
                    "digest": model_digest
                })
            
            return {
                "success": True,
                "models": models,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def pull_model(self, model_name: str) -> Dict[str, Any]:
        """Pull a model"""
        try:
            if not model_name:
                return {
                    "success": False,
                    "error": "Model name is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            logger.info(f"Starting pull for model: {model_name}")
            
            # Use ollama.pull() to download the model
            # This is a blocking operation but we'll run it in background
            def pull_sync():
                try:
                    for response in ollama.pull(model_name, stream=True):
                        if 'status' in response:
                            logger.info(f"Pull progress: {response['status']}")
                    return True
                except Exception as e:
                    logger.error(f"Error during pull: {e}")
                    return False
            
            # Start pull in background (don't wait for completion)
            import threading
            pull_thread = threading.Thread(target=pull_sync)
            pull_thread.start()
            
            return {
                "success": True,
                "message": f"Started pulling model {model_name}",
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error pulling model {model_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def delete_model(self, model_name: str) -> Dict[str, Any]:
        """Delete a model"""
        try:
            if not model_name:
                return {
                    "success": False,
                    "error": "Model name is required",
                    "timestamp": datetime.now().isoformat()
                }
            
            logger.info(f"Deleting model: {model_name}")
            
            # Use ollama.delete() to remove the model
            ollama.delete(model_name)
            
            return {
                "success": True,
                "message": f"Successfully deleted model {model_name}",
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error deleting model {model_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def write_response(self, command_id: str, response: Dict[str, Any]):
        """Write response to shared filesystem"""
        try:
            if not command_id:
                return
            
            response_file = f"{self.status_path}/{command_id}_response.json"
            
            # Ensure response is JSON serializable
            try:
                json_str = json.dumps(response, indent=2, default=str)
            except (TypeError, ValueError) as e:
                logger.error(f"JSON serialization error for command {command_id}: {e}")
                # Write error response instead
                error_response = {
                    "success": False,
                    "error": f"JSON serialization failed: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }
                json_str = json.dumps(error_response, indent=2)
            
            with open(response_file, 'w') as f:
                f.write(json_str)
            
            logger.info(f"Wrote response for command {command_id}")
        
        except Exception as e:
            logger.error(f"Error writing response for {command_id}: {e}")
    
    async def update_status(self):
        """Update GPU status file"""
        try:
            status_data = {
                "timestamp": datetime.now().isoformat(),
                "status": "running",
                "processed_commands": len(self.processed_commands),
                "ollama_available": self.check_ollama_available()
            }
            
            status_file = f"{self.status_path}/gpu_status.json"
            
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
        
        except Exception as e:
            logger.error(f"Error updating status: {e}")
    
    def check_ollama_available(self) -> bool:
        """Check if Ollama is available"""
        try:
            ollama.list()
            return True
        except Exception:
            return False

async def main():
    """Main entry point"""
    service = GPUCommandService()
    await service.start_monitoring()

if __name__ == "__main__":
    asyncio.run(main())