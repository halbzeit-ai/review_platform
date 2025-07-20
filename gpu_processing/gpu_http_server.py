#!/usr/bin/env python3
"""
GPU HTTP Server for Model Management and PDF Processing

This server runs on the GPU instance and provides HTTP endpoints
for model management operations and PDF processing, replacing the NFS-based communication.
"""

import logging
import ollama
import os
import json
import asyncio
from flask import Flask, request, jsonify
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path

# Import PDF processing components
from main import PDFProcessor
from config.processing_config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class GPUHTTPServer:
    """HTTP server for GPU model management and PDF processing"""
    
    def __init__(self):
        self.app = app
        self.pdf_processor = PDFProcessor(mount_path=config.mount_path)
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
        
        @self.app.route('/api/process-pdf', methods=['POST'])
        def process_pdf():
            """Process a PDF file and generate AI review"""
            try:
                # Get request data
                data = request.get_json()
                if not data:
                    return jsonify({
                        "success": False,
                        "error": "No JSON data provided",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                # Extract required fields
                file_path = data.get('file_path')
                pitch_deck_id = data.get('pitch_deck_id')
                company_id = data.get('company_id')
                
                if not file_path:
                    return jsonify({
                        "success": False,
                        "error": "file_path is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                if not pitch_deck_id:
                    return jsonify({
                        "success": False,
                        "error": "pitch_deck_id is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                if not company_id:
                    return jsonify({
                        "success": False,
                        "error": "company_id is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                logger.info(f"Processing PDF: {file_path} for pitch deck {pitch_deck_id}")
                
                # Process the PDF using the existing PDFProcessor
                results = self.pdf_processor.process_pdf(file_path, company_id)
                
                # Save results to shared filesystem (using backend-expected naming pattern)
                import time
                timestamp = int(time.time())
                results_filename = f"job_{pitch_deck_id}_{timestamp}_results.json"
                results_path = config.results_path / results_filename
                
                # Ensure results directory exists
                os.makedirs(config.results_path, exist_ok=True)
                
                # Write results to file
                with open(str(results_path), 'w') as f:
                    json.dump(results, f, indent=2)
                
                logger.info(f"PDF processing completed successfully. Results saved to: {results_path}")
                
                # Update database with results file path
                self._update_database_with_results(pitch_deck_id, results_filename)
                
                return jsonify({
                    "success": True,
                    "message": f"Successfully processed PDF {file_path}",
                    "results_file": results_filename,
                    "results_path": str(results_path),
                    "timestamp": datetime.now().isoformat()
                })
                
            except FileNotFoundError as e:
                logger.error(f"PDF file not found: {e}")
                return jsonify({
                    "success": False,
                    "error": f"PDF file not found: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }), 404
                
            except Exception as e:
                logger.error(f"Error processing PDF: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Error processing PDF: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/run-visual-analysis-batch', methods=['POST'])
        def run_visual_analysis_batch():
            """Run visual analysis batch for extraction testing"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        "success": False,
                        "error": "No JSON data provided",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                deck_ids = data.get('deck_ids', [])
                vision_model = data.get('vision_model')
                analysis_prompt = data.get('analysis_prompt')
                file_paths = data.get('file_paths', [])
                
                if not deck_ids:
                    return jsonify({
                        "success": False,
                        "error": "deck_ids is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                if not vision_model:
                    return jsonify({
                        "success": False,
                        "error": "vision_model is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                if not analysis_prompt:
                    return jsonify({
                        "success": False,
                        "error": "analysis_prompt is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                logger.info(f"Starting visual analysis batch for {len(deck_ids)} decks using {vision_model}")
                
                # Process each deck
                batch_results = {}
                processed_decks = []
                
                for i, deck_id in enumerate(deck_ids):
                    try:
                        if i < len(file_paths):
                            file_path = file_paths[i]
                        else:
                            logger.error(f"No file path provided for deck {deck_id}")
                            continue
                        
                        logger.info(f"Processing deck {deck_id}: {file_path}")
                        
                        # Use the healthcare template analyzer for visual analysis
                        from utils.healthcare_template_analyzer import HealthcareTemplateAnalyzer
                        
                        # Create analyzer - it will use configured models and prompts from database
                        analyzer = HealthcareTemplateAnalyzer()
                        
                        # Override the vision model and prompt for this specific analysis
                        analyzer.vision_model = vision_model
                        analyzer.image_analysis_prompt = analysis_prompt
                        
                        # Full file path for processing
                        from pathlib import Path
                        full_pdf_path = str(Path(config.mount_path) / file_path)
                        
                        # Run visual analysis only
                        analyzer._analyze_visual_content(full_pdf_path, company_id="dojo")
                        
                        # Format results for caching
                        visual_results = {
                            "visual_analysis_results": analyzer.visual_analysis_results
                        }
                        
                        batch_results[str(deck_id)] = visual_results
                        processed_decks.append(deck_id)
                        
                        # Cache result immediately to backend
                        self._cache_visual_analysis_result(deck_id, visual_results, vision_model, analysis_prompt)
                        
                        logger.info(f"Completed visual analysis for deck {deck_id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing deck {deck_id}: {e}")
                        batch_results[str(deck_id)] = {"error": str(e)}
                        continue
                
                logger.info(f"Completed visual analysis batch: {len(processed_decks)}/{len(deck_ids)} successful")
                
                return jsonify({
                    "success": True,
                    "message": f"Visual analysis batch completed for {len(processed_decks)} decks",
                    "processed_decks": processed_decks,
                    "results": batch_results,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error in visual analysis batch: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Error in visual analysis batch: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/run-offering-extraction', methods=['POST'])
        def run_offering_extraction():
            """Run company offering extraction using text model"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        "success": False,
                        "error": "No JSON data provided",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                deck_ids = data.get('deck_ids', [])
                text_model = data.get('text_model')
                extraction_prompt = data.get('extraction_prompt')
                use_cached_visual = data.get('use_cached_visual', True)
                
                if not deck_ids:
                    return jsonify({
                        "success": False,
                        "error": "deck_ids is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                if not text_model:
                    return jsonify({
                        "success": False,
                        "error": "text_model is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                if not extraction_prompt:
                    return jsonify({
                        "success": False,
                        "error": "extraction_prompt is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                logger.info(f"Starting offering extraction for {len(deck_ids)} decks using {text_model}")
                
                # Process each deck for extraction
                extraction_results = []
                
                # Get cached visual analysis from production server
                cached_analysis = self._get_cached_visual_analysis(deck_ids) if use_cached_visual else {}
                
                for deck_id in deck_ids:
                    try:
                        logger.info(f"Extracting offering for deck {deck_id}")
                        
                        # Prepare visual analysis context
                        visual_context = ""
                        visual_used = False
                        
                        if use_cached_visual and deck_id in cached_analysis:
                            visual_data = cached_analysis[deck_id]
                            if visual_data.get("visual_analysis_results"):
                                # Format visual analysis for text extraction
                                visual_descriptions = []
                                for result in visual_data["visual_analysis_results"]:
                                    page_desc = f"Page {result.get('page_number', 'N/A')}: {result.get('description', 'No description')}"
                                    visual_descriptions.append(page_desc)
                                visual_context = "\n".join(visual_descriptions)
                                visual_used = True
                                logger.info(f"Using cached visual analysis for deck {deck_id} ({len(visual_descriptions)} pages)")
                        
                        if not visual_context:
                            visual_context = "[No visual analysis available for this pitch deck]"
                            logger.warning(f"No visual analysis available for deck {deck_id}")
                        
                        # Prepare full extraction prompt with visual context
                        full_extraction_prompt = f"""Based ONLY on the pitch deck visual analysis provided below, {extraction_prompt.lower()}

PITCH DECK VISUAL ANALYSIS:
{visual_context}

IMPORTANT: Base your answer ONLY on the visual analysis above. If no meaningful visual analysis is provided, respond with "No visual analysis available for extraction".

Company offering:"""
                        
                        # Use ollama to run text extraction
                        import ollama
                        
                        response = ollama.chat(
                            model=text_model,
                            messages=[
                                {
                                    'role': 'user', 
                                    'content': full_extraction_prompt
                                }
                            ]
                        )
                        
                        offering_result = response['message']['content']
                        
                        extraction_results.append({
                            "deck_id": deck_id,
                            "offering_extraction": offering_result,
                            "visual_analysis_used": visual_used,
                            "text_model_used": text_model
                        })
                        
                        logger.info(f"Completed extraction for deck {deck_id}")
                        
                    except Exception as e:
                        logger.error(f"Error extracting offering for deck {deck_id}: {e}")
                        extraction_results.append({
                            "deck_id": deck_id,
                            "offering_extraction": f"Error: {str(e)}",
                            "visual_analysis_used": False,
                            "text_model_used": text_model
                        })
                        continue
                
                logger.info(f"Completed offering extraction for {len(extraction_results)} decks")
                
                return jsonify({
                    "success": True,
                    "message": f"Offering extraction completed for {len(deck_ids)} decks",
                    "extraction_results": extraction_results,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error in offering extraction: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Error in offering extraction: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }), 500
    
    def _get_cached_visual_analysis(self, deck_ids: List[int]) -> Dict[int, Dict]:
        """Get cached visual analysis from production server for extraction testing"""
        try:
            import requests
            
            # Get the production server URL from environment or use default
            production_server = os.getenv("PRODUCTION_SERVER_URL", "http://65.108.32.168")
            
            # Request cached visual analysis data
            response = requests.post(
                f"{production_server}/api/internal/get-cached-visual-analysis",
                json={"deck_ids": deck_ids},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    cached_data = data.get("cached_analysis", {})
                    logger.info(f"Retrieved cached visual analysis for {len(cached_data)} decks")
                    return cached_data
                else:
                    logger.error(f"Failed to get cached visual analysis: {data.get('error', 'Unknown error')}")
                    return {}
            else:
                logger.error(f"HTTP error getting cached visual analysis: {response.status_code} - {response.text}")
                return {}
            
        except Exception as e:
            logger.error(f"Error getting cached visual analysis: {e}")
            return {}
    
    def _cache_visual_analysis_result(self, deck_id: int, visual_results: Dict, vision_model: str, analysis_prompt: str):
        """Cache visual analysis result immediately to backend"""
        try:
            import requests
            import json
            
            # Get the production server URL from environment or use default
            production_server = os.getenv("PRODUCTION_SERVER_URL", "http://65.108.32.168")
            
            # Prepare the cache data
            cache_data = {
                "pitch_deck_id": deck_id,
                "analysis_result_json": json.dumps(visual_results),
                "vision_model_used": vision_model,
                "prompt_used": analysis_prompt
            }
            
            # Make HTTP request to cache visual analysis
            response = requests.post(
                f"{production_server}/api/dojo/internal/cache-visual-analysis",
                json=cache_data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Cached visual analysis via HTTP: deck {deck_id}")
            else:
                logger.error(f"Failed to cache visual analysis via HTTP: {response.status_code} - {response.text}")
            
        except Exception as e:
            logger.error(f"Error caching visual analysis via HTTP for deck {deck_id}: {e}")
    
    def _update_database_with_results(self, pitch_deck_id: int, results_filename: str):
        """Update the database via HTTP request to the production server"""
        try:
            import requests
            
            # Get the production server URL from environment or use default
            production_server = os.getenv("PRODUCTION_SERVER_URL", "http://65.108.32.168")
            
            # Prepare the update data
            update_data = {
                "pitch_deck_id": pitch_deck_id,
                "results_file_path": f"results/{results_filename}",
                "processing_status": "completed"
            }
            
            # Make HTTP request to update database
            response = requests.post(
                f"{production_server}/api/internal/update-deck-results",
                json=update_data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Updated database via HTTP: deck {pitch_deck_id} -> results/{results_filename}")
            else:
                logger.error(f"Failed to update database via HTTP: {response.status_code} - {response.text}")
            
        except Exception as e:
            logger.error(f"Error updating database via HTTP for deck {pitch_deck_id}: {e}")
    
    def run(self, host: str = None, port: int = None):
        """Run the HTTP server"""
        # Use environment variables or defaults
        host = host or os.getenv("GPU_HTTP_HOST", "0.0.0.0")
        port = port or int(os.getenv("GPU_HTTP_PORT", "8001"))
        
        logger.info(f"Starting GPU HTTP server on {host}:{port}")
        logger.info(f"Using mount path: {config.mount_path}")
        logger.info(f"Results will be saved to: {config.results_path}")
        
        self.app.run(host=host, port=port, debug=False)

def main():
    """Main entry point"""
    server = GPUHTTPServer()
    server.run()

if __name__ == "__main__":
    main()