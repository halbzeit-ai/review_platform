#!/usr/bin/env python3
"""
GPU HTTP Server for Model Management

This server runs on the GPU instance and provides HTTP endpoints
for model management operations, replacing the NFS-based communication.
"""

import logging
import ollama
from flask import Flask, request, jsonify
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class GPUHTTPServer:
    """HTTP server for GPU model management"""
    
    def __init__(self):
        self.app = app
        self.setup_routes()
    
    def setup_routes(self):
        """Setup HTTP routes"""
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            try:
                # Test if Ollama is accessible
                ollama.list()
                return jsonify({
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "ollama_available": True
                })
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return jsonify({
                    "status": "unhealthy",
                    "timestamp": datetime.now().isoformat(),
                    "ollama_available": False,
                    "error": str(e)
                }), 503
        
        @self.app.route('/api/models', methods=['GET'])
        def list_models():
            """List installed models"""
            try:
                logger.info("Listing models via HTTP API")
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
                
                response = {
                    "success": True,
                    "models": models,
                    "timestamp": datetime.now().isoformat()
                }
                logger.info(f"Successfully listed {len(models)} models")
                return jsonify(response)
                
            except Exception as e:
                logger.error(f"Error listing models: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/models/<model_name>', methods=['POST'])
        def pull_model(model_name: str):
            """Pull a model"""
            try:
                if not model_name:
                    return jsonify({
                        "success": False,
                        "error": "Model name is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                logger.info(f"Starting pull for model: {model_name}")
                
                # Use ollama.pull() to download the model
                # This is a blocking operation that may take time
                def pull_sync():
                    try:
                        for response in ollama.pull(model_name, stream=True):
                            if 'status' in response:
                                logger.info(f"Pull progress: {response['status']}")
                        return True
                    except Exception as e:
                        logger.error(f"Error during pull: {e}")
                        return False
                
                # For now, run synchronously (could be made async later)
                success = pull_sync()
                
                if success:
                    logger.info(f"Successfully pulled model: {model_name}")
                    return jsonify({
                        "success": True,
                        "message": f"Successfully pulled model {model_name}",
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    logger.error(f"Failed to pull model: {model_name}")
                    return jsonify({
                        "success": False,
                        "error": f"Failed to pull model {model_name}",
                        "timestamp": datetime.now().isoformat()
                    }), 500
                    
            except Exception as e:
                logger.error(f"Error pulling model {model_name}: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/models/<model_name>', methods=['DELETE'])
        def delete_model(model_name: str):
            """Delete a model"""
            try:
                if not model_name:
                    return jsonify({
                        "success": False,
                        "error": "Model name is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                logger.info(f"Deleting model: {model_name}")
                
                # Use ollama.delete() to remove the model
                ollama.delete(model_name)
                
                logger.info(f"Successfully deleted model: {model_name}")
                return jsonify({
                    "success": True,
                    "message": f"Successfully deleted model {model_name}",
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error deleting model {model_name}: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
    
    def run(self, host: str = '0.0.0.0', port: int = 8001):
        """Run the HTTP server"""
        logger.info(f"Starting GPU HTTP server on {host}:{port}")
        self.app.run(host=host, port=port, debug=False)

def main():
    """Main entry point"""
    server = GPUHTTPServer()
    server.run()

if __name__ == "__main__":
    main()