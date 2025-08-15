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
import requests
import threading
import time
import socket
from flask import Flask, request, jsonify
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Import PDF processing components
from main import PDFProcessor
from config.processing_config import config

# Configure logging to write to shared filesystem - NO FALLBACKS!
import os
shared_filesystem_path = os.getenv('SHARED_FILESYSTEM_MOUNT_PATH')
if not shared_filesystem_path:
    raise ValueError("SHARED_FILESYSTEM_MOUNT_PATH environment variable is required but not set!")

log_file_path = os.path.join(shared_filesystem_path, 'logs', 'gpu_http_server.log')

# Ensure logs directory exists
os.makedirs(os.path.dirname(log_file_path), exist_ok=True)

# Configure logging with both file and console output - Force immediate flushing
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path),
        logging.StreamHandler()  # Keep console output too
    ],
    force=True  # Force reconfiguration even if already configured
)

# Ensure immediate flushing for all handlers
for handler in logging.getLogger().handlers:
    if hasattr(handler, 'stream'):
        handler.stream.flush()
        
# Custom flush function to force immediate writes
def force_log_flush():
    for handler in logging.getLogger().handlers:
        if hasattr(handler, 'flush'):
            handler.flush()
        if hasattr(handler, 'stream'):
            handler.stream.flush()
logger = logging.getLogger(__name__)

# Log the file location for debugging
logger.info(f"GPU HTTP server logs will be written to: {log_file_path}")
force_log_flush()  # Force immediate write of initialization logs

app = Flask(__name__)
# Disable Flask's default logging to avoid conflicts
app.logger.disabled = True
logging.getLogger('werkzeug').disabled = True

class GPUHTTPServer:
    """HTTP server for GPU model management and PDF processing"""
    
    def __init__(self):
        self.app = app
        # Get backend URL from environment variables
        environment = os.getenv('ENVIRONMENT', 'development').lower()
        if environment == 'production':
            self.backend_url = os.getenv('BACKEND_PRODUCTION', 'http://65.108.32.168:8000')
        else:
            self.backend_url = os.getenv('BACKEND_DEVELOPMENT', 'http://65.108.32.143:8000')
        
        # Server registration variables
        self.server_id = f"gpu-{socket.gethostname()}-{os.getpid()}"
        self.is_registered = False
        self.heartbeat_thread = None
        self.queue_polling_thread = None
        self.shutdown_flag = False
        
        logger.info(f"Initialized GPUHTTPServer with backend URL: {self.backend_url}")
        logger.info(f"Server ID: {self.server_id}")
        self.pdf_processor = PDFProcessor(mount_path=config.mount_path, backend_url=self.backend_url)
        self.setup_routes()
    
    def setup_routes(self):
        """Setup HTTP routes"""
        
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint"""
            logger.info("Health check requested")
            force_log_flush()
            try:
                # Test if Ollama is accessible
                ollama.list()
                logger.info("Health check passed - Ollama accessible")
                force_log_flush()
                return jsonify({
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat(),
                    "ollama_available": True
                })
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                force_log_flush()
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
                document_id = data.get('document_id', data.get('pitch_deck_id'))
                company_id = data.get('company_id')
                
                if not file_path:
                    return jsonify({
                        "success": False,
                        "error": "file_path is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                if not document_id:
                    return jsonify({
                        "success": False,
                        "error": "document_id is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                if not company_id:
                    return jsonify({
                        "success": False,
                        "error": "company_id is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                logger.info(f"Processing PDF: {file_path} for document {document_id}")
                
                # Process the PDF using the existing PDFProcessor
                results = self.pdf_processor.process_pdf(file_path, company_id)
                
                # Save results to shared filesystem (using backend-expected naming pattern)
                import time
                timestamp = int(time.time())
                results_filename = f"job_{document_id}_{timestamp}_results.json"
                results_path = config.results_path / results_filename
                
                # Ensure results directory exists
                os.makedirs(config.results_path, exist_ok=True)
                
                # Write results to file
                with open(str(results_path), 'w') as f:
                    json.dump(results, f, indent=2)
                
                logger.info(f"PDF processing completed successfully. Results saved to: {results_path}")
                
                # Update database with results file path
                self._update_database_with_results(document_id, results_filename)
                
                # Save specialized analysis to database
                specialized_analysis = results.get("specialized_analysis", {})
                if specialized_analysis:
                    self._save_specialized_analysis(document_id, specialized_analysis)
                else:
                    logger.info(f"No specialized analysis found for deck {document_id}")
                
                # Save template processing results to extraction_experiments for startup access
                self._save_template_processing_results(document_id, results)
                
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
        
        @self.app.route('/api/run-template-processing-only', methods=['POST'])
        def run_template_processing_only():
            """Run template processing using cached visual analysis and extraction results"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        "success": False,
                        "error": "No JSON data provided",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                deck_ids = data.get('deck_ids', [])
                template_id = data.get('template_id')
                text_model = data.get('text_model')
                generate_thumbnails = data.get('generate_thumbnails', True)
                enable_progressive_delivery = data.get('enable_progressive_delivery', False)
                
                if not deck_ids:
                    return jsonify({
                        "success": False,
                        "error": "deck_ids is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                if not template_id:
                    return jsonify({
                        "success": False,
                        "error": "template_id is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                logger.info(f"Starting template-only processing for {len(deck_ids)} decks using template {template_id}")
                if text_model:
                    logger.info(f"Using specified text model: {text_model}")
                else:
                    logger.info("No text model specified, using default")
                
                # Get cached visual analysis for all decks at once
                cached_analysis = self._get_cached_visual_analysis(deck_ids)
                
                # Load template configuration
                from utils.healthcare_template_analyzer import HealthcareTemplateAnalyzer
                
                # Process each deck
                batch_results = []
                
                for deck_id in deck_ids:
                    try:
                        # Check if we have cached visual analysis for this deck
                        if deck_id not in cached_analysis:
                            logger.error(f"No cached visual analysis found for deck {deck_id}")
                            continue
                        
                        deck_visual_data = cached_analysis[deck_id]
                        
                        if not deck_visual_data or 'visual_analysis_results' not in deck_visual_data:
                            logger.error(f"No visual analysis results in cached data for deck {deck_id}")
                            continue
                        
                        # Extract deck name from visual analysis data
                        deck_name = "Unknown"
                        if deck_visual_data['visual_analysis_results']:
                            deck_name = deck_visual_data['visual_analysis_results'][0].get('deck_name', f'deck_{deck_id}')
                        
                        # Get extraction results (offering, name, classification, etc.) from database
                        extraction_data = self._get_extraction_results_for_deck(deck_id)
                        
                        if not extraction_data:
                            logger.warning(f"No extraction results found for deck {deck_id} - proceeding with visual analysis only")
                            extraction_data = {}  # Empty dict to avoid errors
                        
                        # Create analyzer with model overrides if specified
                        if text_model:
                            analyzer = HealthcareTemplateAnalyzer(text_model_override=text_model, scoring_model_override=text_model)
                            logger.info(f"🔧 Creating analyzer with text and scoring models for deck {deck_id}: {text_model}")
                        else:
                            analyzer = HealthcareTemplateAnalyzer()
                        
                        # Set visual analysis results
                        analyzer.visual_analysis_results = deck_visual_data['visual_analysis_results']
                        logger.info(f"Loaded {len(analyzer.visual_analysis_results)} visual analysis results for deck {deck_id}")
                        
                        # Set extraction results
                        analyzer.company_offering = extraction_data.get('company_offering', '')
                        analyzer.startup_name = extraction_data.get('startup_name', '')
                        analyzer.funding_amount = extraction_data.get('funding_amount', '')
                        analyzer.deck_date = extraction_data.get('deck_date', '')
                        analyzer.classification_result = extraction_data.get('classification', {})
                        
                        # Load template configuration using analyzer's database connection (like the old method)
                        try:
                            analyzer.template_config = analyzer._load_template_config(template_id)
                            if analyzer.template_config:
                                template_name = analyzer.template_config.get('template', {}).get('name', 'Unknown')
                                logger.info(f"Loaded template '{template_name}' for deck {deck_id}")
                            else:
                                logger.error(f"Failed to load template {template_id}")
                                continue
                        except Exception as e:
                            logger.error(f"Error loading template {template_id}: {e}")
                            continue
                        
                        # Set progress callback with progressive delivery support
                        def progress_callback(deck_id: int, chapter_name: str, status: str = "processing", chapter_results: dict = None):
                            # Basic progress update
                            callback_data = {
                                "chapter_name": chapter_name,
                                "deck_id": deck_id,
                                "status": status,
                                "deck_name": deck_name  # Pass deck name for better progress display
                            }
                            
                            # Add chapter results for progressive delivery if enabled and results provided
                            if enable_progressive_delivery and chapter_results and status == "completed":
                                callback_data["chapter_results"] = chapter_results
                                logger.info(f"Progressive delivery - Sending chapter '{chapter_name}' results for deck {deck_id}")
                            
                            # Call backend to update progress
                            requests.post(
                                f"{self.backend_url}/api/dojo/template-progress-callback",
                                json=callback_data
                            )
                        
                        # Store progress callback and deck_id for chapter processing
                        analyzer.progress_callback = progress_callback
                        analyzer.current_deck_id = deck_id
                        
                        # Execute ONLY template analysis (no visual analysis, no extractions)
                        analyzer._execute_template_analysis()
                        
                        # Format results
                        template_analysis = self._format_template_analysis({
                            "template_results": analyzer.chapter_results
                        })
                        
                        # Save template processing results
                        save_success = self._save_template_processing_only(deck_id, {
                            "chapter_analysis": analyzer.chapter_results,
                            "overall_score": analyzer.overall_score if hasattr(analyzer, 'overall_score') else 0.0,
                            "template_used": template_name
                        })
                        
                        if save_success:
                            batch_results.append({
                                "deck_id": deck_id,
                                "success": True,
                                "template_analysis": template_analysis
                            })
                            logger.info(f"✅ Completed and saved template processing for deck {deck_id}")
                        else:
                            batch_results.append({
                                "deck_id": deck_id,
                                "success": False,
                                "error": "Failed to save template processing results"
                            })
                            logger.error(f"❌ Failed to save template processing for deck {deck_id}")
                        
                    except Exception as e:
                        logger.error(f"Error processing deck {deck_id}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        batch_results.append({
                            "deck_id": deck_id,
                            "success": False,
                            "error": str(e)
                        })
                
                return jsonify({
                    "success": True,
                    "message": f"Template processing completed for {len(batch_results)} decks",
                    "results": batch_results,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error in template processing: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/run-specialized-analysis-only', methods=['POST'])
        def run_specialized_analysis_only():
            """Run specialized analysis (regulatory, clinical, scientific) using cached visual analysis and extraction results"""
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
                
                if not deck_ids:
                    return jsonify({
                        "success": False,
                        "error": "deck_ids is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                logger.info(f"Starting specialized analysis for {len(deck_ids)} decks")
                if text_model:
                    logger.info(f"Using specified text model: {text_model}")
                else:
                    logger.info("No text model specified, using default")
                
                # Get cached visual analysis for all decks at once
                cached_analysis = self._get_cached_visual_analysis(deck_ids)
                
                # Process each deck
                batch_results = []
                
                for deck_id in deck_ids:
                    try:
                        # Check if we have cached visual analysis for this deck
                        if deck_id not in cached_analysis:
                            logger.error(f"No cached visual analysis found for deck {deck_id}")
                            batch_results.append({
                                "deck_id": deck_id,
                                "success": False,
                                "error": "No cached visual analysis found"
                            })
                            continue
                        
                        deck_visual_data = cached_analysis[deck_id]
                        
                        if not deck_visual_data or 'visual_analysis_results' not in deck_visual_data:
                            logger.error(f"No visual analysis results in cached data for deck {deck_id}")
                            batch_results.append({
                                "deck_id": deck_id,
                                "success": False,
                                "error": "No visual analysis results found"
                            })
                            continue
                        
                        # Get extraction results (offering, name, classification, etc.) from database
                        extraction_data = self._get_extraction_results_for_deck(deck_id)
                        
                        if not extraction_data:
                            logger.warning(f"No extraction results found for deck {deck_id} - proceeding with visual analysis only")
                            extraction_data = {}  # Empty dict to avoid errors
                        
                        # Create analyzer for specialized analysis
                        from utils.healthcare_template_analyzer import HealthcareTemplateAnalyzer
                        
                        if text_model:
                            analyzer = HealthcareTemplateAnalyzer(text_model_override=text_model, scoring_model_override=text_model)
                            logger.info(f"🔧 Creating analyzer with text model for deck {deck_id}: {text_model}")
                        else:
                            analyzer = HealthcareTemplateAnalyzer()
                            logger.info(f"🔧 Creating analyzer with default models for deck {deck_id}")
                        
                        # Run ONLY specialized analysis
                        logger.info(f"🔍 Running specialized analysis for deck {deck_id}")
                        specialized_results = analyzer.run_specialized_analysis_only(
                            deck_visual_data['visual_analysis_results'],
                            extraction_data
                        )
                        
                        # Save specialized analysis results
                        if specialized_results:
                            success = self._save_specialized_analysis(deck_id, specialized_results)
                            if success:
                                batch_results.append({
                                    "deck_id": deck_id,
                                    "success": True,
                                    "specialized_analysis": specialized_results
                                })
                                logger.info(f"✅ Successfully completed specialized analysis for deck {deck_id}")
                            else:
                                batch_results.append({
                                    "deck_id": deck_id,
                                    "success": False,
                                    "error": "Failed to save specialized analysis results"
                                })
                        else:
                            batch_results.append({
                                "deck_id": deck_id,
                                "success": False,
                                "error": "No specialized analysis results generated"
                            })
                        
                    except Exception as e:
                        logger.error(f"Error processing specialized analysis for deck {deck_id}: {e}")
                        import traceback
                        logger.error(traceback.format_exc())
                        batch_results.append({
                            "deck_id": deck_id,
                            "success": False,
                            "error": str(e)
                        })
                
                return jsonify({
                    "success": True,
                    "message": f"Specialized analysis completed for {len(batch_results)} decks",
                    "results": batch_results,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error in specialized analysis: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return jsonify({
                    "success": False,
                    "error": str(e),
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
                company_ids = data.get('company_ids', [])
                
                logger.info(f"📥 Received visual analysis request:")
                logger.info(f"   deck_ids: {deck_ids}")
                logger.info(f"   vision_model: {vision_model}")
                logger.info(f"   analysis_prompt: {analysis_prompt[:50] if analysis_prompt else None}...")
                logger.info(f"   file_paths count: {len(file_paths)}")
                logger.info(f"   company_ids: {company_ids}")
                
                if not deck_ids:
                    return jsonify({
                        "success": False,
                        "error": "deck_ids is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                # vision_model and analysis_prompt are now optional - will use database defaults if not provided
                
                logger.info(f"Starting visual analysis batch for {len(deck_ids)} decks using {vision_model}")
                logger.info(f"DEBUG: vision_model type: {type(vision_model)}, value: '{vision_model}'")
                
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
                        
                        # Only override if explicitly provided (not None)
                        if vision_model:
                            analyzer.vision_model = vision_model
                            logger.info(f"Overriding vision model to: {vision_model}")
                        
                        if analysis_prompt:
                            analyzer.image_analysis_prompt = analysis_prompt
                            logger.info(f"Overriding analysis prompt")
                        
                        # Full file path for processing
                        from pathlib import Path
                        full_pdf_path = str(Path(config.mount_path) / file_path)
                        
                        # Get company_id for this deck (use actual company or fallback to "dojo" for legacy)
                        if i < len(company_ids) and company_ids[i]:
                            company_id = company_ids[i]
                        else:
                            # Fallback for legacy/test data
                            company_id = "dojo"
                            logger.warning(f"No company_id provided for deck {deck_id}, using 'dojo' as fallback")
                        
                        # Run visual analysis with actual company_id
                        analyzer._analyze_visual_content(full_pdf_path, company_id=company_id, deck_id=deck_id)
                        
                        # Generate slide feedback after visual analysis
                        logger.info(f"Generating slide feedback for deck {deck_id}")
                        analyzer.deck_id = deck_id  # Set deck_id for feedback storage
                        analyzer._generate_slide_feedback()
                        
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
                        # Check if user's prompt mentions visual analysis, if not add context
                        if "visual analysis" in extraction_prompt.lower():
                            # User already mentions visual analysis in their prompt, just add the context
                            full_extraction_prompt = f"""{extraction_prompt}

PITCH DECK VISUAL ANALYSIS:
{visual_context}"""
                        else:
                            # User doesn't mention visual analysis, so provide full context
                            full_extraction_prompt = f"""Based on the pitch deck visual analysis provided below, {extraction_prompt}

PITCH DECK VISUAL ANALYSIS:
{visual_context}

IMPORTANT: Base your answer ONLY on the visual analysis above. If no meaningful visual analysis is provided, respond with "No visual analysis available for extraction"."""
                        
                        # DEBUG: Log the full prompt being sent to the model
                        logger.info(f"DEBUG: Full extraction prompt for deck {deck_id}:")
                        logger.info(f"Visual context length: {len(visual_context)} characters")
                        logger.info(f"Visual used flag: {visual_used}")
                        logger.info(f"First 500 chars of prompt: {full_extraction_prompt[:500]}...")
                        
                        # Use ollama to run text extraction
                        import ollama
                        
                        response = ollama.chat(
                            model=text_model,
                            messages=[
                                {
                                    'role': 'user', 
                                    'content': full_extraction_prompt
                                }
                            ],
                            options={'num_ctx': 32768, 'temperature': 0.3}
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
        
        @self.app.route('/api/run-extraction-experiment', methods=['POST'])
        def run_extraction_experiment():
            """Run comprehensive extraction experiment (all Step 3 extractions)"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        "success": False,
                        "error": "No JSON data provided",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                deck_ids = data.get('deck_ids', [])
                experiment_name = data.get('experiment_name', f'experiment_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
                extraction_type = data.get('extraction_type', 'all')
                text_model = data.get('text_model', 'gemma3:12b')
                processing_options = data.get('processing_options', {})
                
                if not deck_ids:
                    return jsonify({
                        "success": False,
                        "error": "deck_ids is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                logger.info(f"Starting comprehensive extraction experiment '{experiment_name}' for {len(deck_ids)} decks")
                
                # Import and instantiate the analyzer
                from utils.healthcare_template_analyzer import HealthcareTemplateAnalyzer
                analyzer = HealthcareTemplateAnalyzer()
                
                # Collect all extraction results
                all_results = {}
                
                # Step 1: Run offering extraction
                logger.info("Step 3.1: Running company offering extraction...")
                offering_prompt = analyzer._get_pipeline_prompt('offering_extraction')
                offering_results = self._run_extraction_step(deck_ids, offering_prompt, text_model, 'offering_extraction')
                all_results["offering_extraction"] = offering_results
                
                # Step 2: Run classification (if enabled)
                classification_results = []
                if processing_options.get('do_classification', True):
                    logger.info("Step 3.2: Running sector classification...")
                    # Use the existing dojo classification logic
                    classification_results = self._run_classification_step(deck_ids, offering_results)
                all_results["classification"] = classification_results
                
                # Step 3: Extract company names (if enabled)  
                company_name_results = []
                if processing_options.get('extract_company_name', True):
                    logger.info("Step 3.3: Extracting company names...")
                    name_prompt = analyzer._get_pipeline_prompt('startup_name_extraction')
                    company_name_results = self._run_extraction_step(deck_ids, name_prompt, text_model, 'company_name_extraction')
                all_results["company_names"] = company_name_results
                
                # Step 4: Extract funding amounts (if enabled)
                funding_results = []
                if processing_options.get('extract_funding_amount', True):
                    logger.info("Step 3.4: Extracting funding amounts...")
                    funding_prompt = analyzer._get_pipeline_prompt('funding_amount_extraction')
                    funding_results = self._run_extraction_step(deck_ids, funding_prompt, text_model, 'funding_amount_extraction')
                all_results["funding_amounts"] = funding_results
                
                # Step 5: Extract deck dates (if enabled)
                date_results = []
                if processing_options.get('extract_deck_date', True):
                    logger.info("Step 3.5: Extracting deck dates...")
                    date_prompt = analyzer._get_pipeline_prompt('deck_date_extraction')
                    date_results = self._run_extraction_step(deck_ids, date_prompt, text_model, 'deck_date_extraction')
                all_results["deck_dates"] = date_results
                
                # Save ALL extraction results together in one experiment
                experiment_id = self._save_extraction_experiment(experiment_name, deck_ids, all_results, 'comprehensive')
                
                logger.info(f"Comprehensive extraction experiment '{experiment_name}' completed successfully")
                
                return jsonify({
                    "success": True,
                    "message": f"Extraction experiment completed for {len(deck_ids)} decks",
                    "experiment_id": experiment_id,
                    "experiment_name": experiment_name,
                    "results": {
                        "offering_extraction": offering_results,
                        "classification": classification_results,
                        "company_names": company_name_results,
                        "funding_amounts": funding_results, 
                        "deck_dates": date_results
                    },
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error in extraction experiment: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Error in extraction experiment: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/run-classification', methods=['POST'])
        def run_classification():
            """Run classification using text model"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        "success": False,
                        "error": "No JSON data provided",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                model = data.get('model')
                prompt = data.get('prompt')
                options = data.get('options', {})
                
                if not model:
                    return jsonify({
                        "success": False,
                        "error": "model is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                if not prompt:
                    return jsonify({
                        "success": False,
                        "error": "prompt is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                logger.info(f"Starting classification using model {model}")
                
                # Use ollama.generate for text generation
                response = ollama.generate(
                    model=model,
                    prompt=prompt,
                    options=options
                )
                
                logger.info("Classification completed successfully")
                
                return jsonify({
                    "success": True,
                    "response": response['response'],
                    "message": "Classification completed successfully",
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error in classification: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Error in classification: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/api/processing-progress/<int:document_id>', methods=['GET'])
        def get_processing_progress(document_id: int):
            """Get processing progress for a specific pitch deck"""
            try:
                logger.info(f"Getting processing progress for document {document_id}")
                
                # For now, we'll implement a basic progress tracking system
                # In a real implementation, this would track actual processing stages
                
                # Check if there's an active processing job for this deck
                # This is a simplified version - in production you'd track actual progress
                
                # Try to determine status based on file system state
                import os
                from pathlib import Path
                
                # Check for results file
                results_pattern = f"job_{document_id}_*_results.json"
                results_dir = config.results_path
                import glob
                result_files = glob.glob(str(results_dir / results_pattern))
                
                if result_files:
                    # Processing completed
                    return jsonify({
                        "success": True,
                        "status": "completed",
                        "progress": {
                            "current_step": "Analysis Complete",
                            "progress_percentage": 100,
                            "message": "PDF analysis completed successfully"
                        },
                        "timestamp": datetime.now().isoformat()
                    })
                else:
                    # Check if processing is actually happening
                    # This is a simplified approach - in reality you'd track active jobs
                    return jsonify({
                        "success": True,
                        "status": "processing",
                        "progress": {
                            "current_step": "Analyzing PDF content",
                            "progress_percentage": 45,
                            "message": "Processing pitch deck slides and generating analysis..."
                        },
                        "timestamp": datetime.now().isoformat()
                    })
                
            except Exception as e:
                logger.error(f"Error getting processing progress for document {document_id}: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500
        
        @self.app.route('/analyze-images', methods=['POST'])
        def analyze_images():
            """Analyze single or multiple images with a prompt (for slide feedback generation)"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        "success": False,
                        "error": "No JSON data provided",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                images = data.get('images', [])
                prompt = data.get('prompt', '')
                model = data.get('model', 'gemma3:27b')  # Default vision model
                options = data.get('options', {})
                
                if not images or not prompt:
                    return jsonify({
                        "success": False,
                        "error": "images and prompt are required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                results = []
                
                for image_path in images:
                    try:
                        # Handle both absolute and relative paths correctly
                        if not os.path.isabs(image_path):
                            # For relative paths, prepend the shared filesystem mount path
                            # This matches how visual analysis stores paths (e.g., "analysis/deck_name/slide_1.jpg")
                            image_path = os.path.join(shared_filesystem_path, image_path)
                        
                        if not os.path.exists(image_path):
                            results.append({
                                "image_path": image_path,
                                "success": False,
                                "error": f"Image file not found: {image_path}"
                            })
                            continue
                        
                        # Use ollama vision model for image analysis
                        response = ollama.generate(
                            model=model,
                            prompt=prompt,
                            images=[image_path],
                            options=options
                        )
                        
                        analysis_text = response.get('response', '').strip()
                        
                        results.append({
                            "image_path": image_path,
                            "success": True,
                            "analysis": analysis_text
                        })
                        
                        logger.info(f"Generated analysis for image: {os.path.basename(image_path)}")
                        
                    except Exception as e:
                        logger.error(f"Error analyzing image {image_path}: {e}")
                        results.append({
                            "image_path": image_path,
                            "success": False,
                            "error": str(e)
                        })
                
                return jsonify({
                    "success": True,
                    "message": f"Analyzed {len([r for r in results if r['success']])} of {len(images)} images",
                    "results": results,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error in analyze-images endpoint: {e}")
                return jsonify({
                    "success": False,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }), 500

        @self.app.route('/api/run-template-processing-batch', methods=['POST'])
        def run_template_processing_batch():
            """Run template processing for multiple decks with optional thumbnail generation"""
            try:
                data = request.get_json()
                if not data:
                    return jsonify({
                        "success": False,
                        "error": "No JSON data provided",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                deck_ids = data.get('deck_ids', [])
                template_info = data.get('template_info')
                generate_thumbnails = data.get('generate_thumbnails', True)
                progress_callback_url = data.get('progress_callback_url')
                processing_options = data.get('processing_options', {})
                
                # Validation
                if not deck_ids:
                    return jsonify({
                        "success": False,
                        "error": "deck_ids is required",
                        "timestamp": datetime.now().isoformat()
                    }), 400
                
                logger.info(f"Starting template processing batch for {len(deck_ids)} decks with template: {template_info}")
                
                # Get template information
                template_name = template_info.get('name', 'Standard Analysis') if template_info else 'Standard Analysis'
                template_prompt = template_info.get('prompt', 'Analyze this healthcare startup pitch deck focusing on market opportunity, technology innovation, business model, competitive advantage, and regulatory considerations.') if template_info else 'Analyze this healthcare startup pitch deck focusing on market opportunity, technology innovation, business model, competitive advantage, and regulatory considerations.'
                
                # Get cached visual analysis for all decks
                cached_visual_data = self._get_cached_visual_analysis(deck_ids)
                logger.info(f"DEBUG: Retrieved cached visual data for {len(cached_visual_data)} decks out of {len(deck_ids)} requested")
                logger.info(f"DEBUG: Cached data keys: {list(cached_visual_data.keys())}")
                
                # Process each deck
                processing_results = []
                
                for deck_id in deck_ids:
                    try:
                        logger.info(f"Processing deck {deck_id} with template '{template_name}'")
                        
                        # Get visual analysis for this deck (keys are integers after conversion)
                        deck_visual_data = cached_visual_data.get(deck_id, {})
                        logger.info(f"DEBUG: deck_id={deck_id} (type: {type(deck_id)}), has data: {bool(deck_visual_data)}")
                        if deck_visual_data:
                            logger.info(f"DEBUG: deck_visual_data keys: {list(deck_visual_data.keys())[:5]}")
                        
                        if not deck_visual_data:
                            logger.warning(f"No cached visual analysis found for deck {deck_id}")
                            processing_results.append({
                                "deck_id": deck_id,
                                "filename": f"deck_{deck_id}",
                                "template_analysis": None,
                                "template_used": template_name,
                                "thumbnails": [],
                                "error": "No cached visual analysis available"
                            })
                            continue
                        
                        # Extract visual analysis text from the correct structure
                        visual_analysis_results = deck_visual_data.get('visual_analysis_results', [])
                        if visual_analysis_results:
                            # Format the visual analysis from the results
                            visual_descriptions = []
                            for result in visual_analysis_results:
                                page_desc = f"Page {result.get('page_number', 'N/A')}: {result.get('description', 'No description')}"
                                visual_descriptions.append(page_desc)
                            visual_analysis_text = "\n".join(visual_descriptions)
                        else:
                            visual_analysis_text = deck_visual_data.get('visual_analysis', '')
                        
                        filename = deck_visual_data.get('filename', f'deck_{deck_id}')
                        
                        # Check if we should use the healthcare template analyzer
                        # Use it for: 1) template-based analysis, or 2) extraction-only mode
                        logger.info(f"DEBUG: template_info = {template_info}")
                        logger.info(f"DEBUG: processing_options = {processing_options}")
                        logger.info(f"DEBUG: extraction_only = {processing_options.get('extraction_only', False) if processing_options else False}")
                        
                        use_chapter_analysis = (template_info and template_info.get('id') is not None) or (processing_options and processing_options.get('extraction_only', False))
                        logger.info(f"DEBUG: use_chapter_analysis = {use_chapter_analysis}")
                        
                        if use_chapter_analysis:
                            # Use healthcare template analyzer for chapter-by-chapter analysis
                            logger.info(f"Using healthcare template analyzer for chapter-by-chapter analysis of deck {deck_id}")
                            
                            # Create progress callback function
                            def progress_callback(deck_id, chapter_name, status="processing"):
                                if progress_callback_url:
                                    try:
                                        import requests
                                        requests.post(progress_callback_url, json={
                                            "deck_id": deck_id,
                                            "chapter_name": chapter_name,
                                            "status": status
                                        }, timeout=5)
                                    except Exception as e:
                                        logger.warning(f"Failed to send progress callback: {e}")
                            
                            # We need to get the PDF path for the deck
                            # First, try to get from database
                            import psycopg2
                            database_url = os.getenv("DATABASE_URL")
                            if not database_url:
                                database_url = "postgresql://dev_user:!dev_Halbzeit1024@65.108.32.143:5432/review_dev"
                            
                            conn = psycopg2.connect(database_url)
                            cursor = conn.cursor()
                            
                            cursor.execute("""
                                SELECT pd.file_path, p.company_id 
                                FROM project_documents pd
                                JOIN projects p ON pd.project_id = p.id
                                WHERE pd.id = %s
                            """, (deck_id,))
                            
                            result = cursor.fetchone()
                            cursor.close()
                            conn.close()
                            
                            if result and result[0]:
                                pdf_path = result[0]
                                company_id = result[1] if len(result) > 1 else "dojo"  # Use actual company_id or fallback
                                full_pdf_path = str(Path(config.mount_path) / pdf_path)
                                
                                # Create analyzer and run full analysis
                                from utils.healthcare_template_analyzer import HealthcareTemplateAnalyzer
                                analyzer = HealthcareTemplateAnalyzer()
                                
                                # The analyzer will load the template from database using template_id
                                # We need to set the template config before calling analyze_pdf (unless extraction_only)
                                try:
                                    if processing_options and processing_options.get('extraction_only', False):
                                        # In extraction_only mode, we don't need a template
                                        logger.info(f"Extraction-only mode: skipping template loading for deck {deck_id}")
                                        analyzer.template_config = None
                                    elif template_info and template_info.get('id'):
                                        # Load template configuration
                                        logger.info(f"DEBUG: Loading template {template_info['id']} for deck {deck_id}")
                                        template_config = analyzer._load_template_from_database(template_info['id'])
                                        logger.info(f"DEBUG: Template config result: {template_config is not None}")
                                        
                                        if not template_config:
                                            logger.error(f"Failed to load template {template_info['id']} from database")
                                            raise ValueError(f"Template {template_info['id']} not found in database")
                                        
                                        # Set the template config on the analyzer
                                        analyzer.template_config = template_config
                                        logger.info(f"DEBUG: Set analyzer.template_config = {analyzer.template_config is not None}")
                                        logger.info(f"Loaded template '{template_config.get('name', 'Unknown')}' for deck {deck_id}")
                                    else:
                                        logger.warning(f"No template specified and not in extraction_only mode for deck {deck_id}")
                                        analyzer.template_config = None
                                    
                                    # Also need to set the visual analysis results from cache
                                    if 'visual_analysis_results' in deck_visual_data:
                                        analyzer.visual_analysis_results = deck_visual_data['visual_analysis_results']
                                        logger.info(f"Set {len(analyzer.visual_analysis_results)} visual analysis results for deck {deck_id}")
                                    else:
                                        logger.warning(f"No visual_analysis_results in cached data for deck {deck_id}")
                                        # Try alternative format
                                        if isinstance(deck_visual_data.get('visual_analysis'), list):
                                            analyzer.visual_analysis_results = deck_visual_data['visual_analysis']
                                            logger.info(f"Set {len(analyzer.visual_analysis_results)} visual analysis results from alternative format")
                                        else:
                                            logger.error(f"No visual analysis data found in any format for deck {deck_id}")
                                    
                                except Exception as e:
                                    import traceback
                                    logger.error(f"Error loading template configuration: {e}")
                                    logger.error(f"Template config error traceback: {traceback.format_exc()}")
                                    raise
                                
                                # Run the analysis with progress callback and processing options
                                analysis_results = analyzer.analyze_pdf(
                                    full_pdf_path, 
                                    company_id=company_id,
                                    progress_callback=progress_callback,
                                    deck_id=deck_id,
                                    processing_options=processing_options
                                )
                                
                                # Extract the formatted template analysis
                                template_analysis = self._format_template_analysis(analysis_results)
                                
                                # Call save functions based on processing mode
                                
                                if processing_options and processing_options.get('extraction_only', False):
                                    # In extraction_only mode, only save extraction results
                                    logger.info("Extraction-only mode: saving only extraction results")
                                    
                                    # 2. Save extraction results (company_offering, classification, etc.)
                                    extraction_data = {
                                        "company_offering": analysis_results.get("company_offering", ""),
                                        "classification": analysis_results.get("classification", {}),
                                        "funding_amount": analysis_results.get("funding_amount", ""),
                                        "deck_date": analysis_results.get("deck_date", ""),
                                        "company_name": analysis_results.get("startup_name", ""),  # Fix: analyzer returns startup_name
                                        "model_used": analysis_results.get("text_model_used", "auto")
                                    }
                                    self._save_extraction_results(deck_id, extraction_data)
                                    
                                else:
                                    # Normal mode: save all four types of results
                                    
                                    # 1. Save visual analysis and feedback (already cached during analysis)
                                    visual_results = analysis_results.get("visual_analysis_results", [])
                                    self._save_visual_analysis_and_feedback(deck_id, visual_results)
                                    
                                    # 2. Save extraction results (company_offering, classification, etc.)
                                    extraction_data = {
                                        "company_offering": analysis_results.get("company_offering", ""),
                                        "classification": analysis_results.get("classification", {}),
                                        "funding_amount": analysis_results.get("funding_amount", ""),
                                        "deck_date": analysis_results.get("deck_date", ""),
                                        "company_name": analysis_results.get("startup_name", ""),  # Fix: analyzer returns startup_name
                                        "model_used": analysis_results.get("text_model_used", "auto")
                                    }
                                    self._save_extraction_results(deck_id, extraction_data)
                                    
                                    # 3. Save template processing results only (specialized analysis now separate)
                                    self._save_template_processing_only(deck_id, analysis_results)
                                
                            else:
                                logger.error(f"Could not find PDF path for deck {deck_id}")
                                template_analysis = "Error: Could not find PDF file for analysis"
                        else:
                            # Fall back to simple prompt-based analysis
                            logger.info(f"DEBUG: Using fallback prompt-based analysis for deck {deck_id}")
                            full_prompt = f"""Based on the following visual analysis of a healthcare startup pitch deck, {template_prompt}

Visual Analysis:
{visual_analysis_text}

Please provide a comprehensive analysis focusing on the requested areas."""
                            
                            # Use ollama to generate template analysis
                            model_name = "phi4:latest"  # Use the same model as other extractions
                            
                            response = ollama.generate(
                                model=model_name,
                                prompt=full_prompt,
                                options={
                                    "temperature": 0.3,
                                    "num_ctx": 32768,
                                    "num_predict": 4096
                                }
                            )
                            
                            template_analysis = response.get('response', '').strip()
                        
                        # Generate thumbnail paths (simulated for now)
                        thumbnails = []
                        if generate_thumbnails:
                            # In a real implementation, this would generate actual thumbnails
                            # For now, we'll return placeholder paths
                            thumbnails = [f"/thumbnails/{deck_id}_slide_{i}.jpg" for i in range(1, 6)]
                        
                        result = {
                            "deck_id": deck_id,
                            "filename": filename,
                            "template_analysis": template_analysis,
                            "template_used": template_name,
                            "thumbnails": thumbnails,
                            "error": None
                        }
                        processing_results.append(result)
                        
                        logger.info(f"Successfully processed deck {deck_id} with template analysis")
                        
                    except Exception as e:
                        logger.error(f"Error processing deck {deck_id}: {e}")
                        processing_results.append({
                            "deck_id": deck_id,
                            "filename": f"deck_{deck_id}",
                            "template_analysis": None,
                            "template_used": template_name,
                            "thumbnails": [],
                            "error": str(e)
                        })
                        continue
                
                success_count = len([r for r in processing_results if r.get('error') is None])
                
                return jsonify({
                    "success": True,
                    "message": f"Template processing batch completed: {success_count}/{len(deck_ids)} decks processed successfully",
                    "processing_results": processing_results,
                    "statistics": {
                        "total_decks": len(deck_ids),
                        "successful_processing": success_count,
                        "failed_processing": len(deck_ids) - success_count,
                        "success_rate": success_count / len(deck_ids) if deck_ids else 0
                    },
                    "template_used": template_name,
                    "thumbnails_generated": generate_thumbnails,
                    "timestamp": datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error in template processing batch: {e}")
                return jsonify({
                    "success": False,
                    "error": f"Error in template processing batch: {str(e)}",
                    "timestamp": datetime.now().isoformat()
                }), 500
    
    def _format_template_analysis(self, analysis_results: Dict[str, Any]) -> str:
        """Format ONLY the chapter analysis results for Step 4 template processing"""
        try:
            sections = []
            
            # Only include Chapter Analysis for Step 4
            if analysis_results.get('chapter_analysis'):
                sections.append("**Template Analysis Results**")
                
                for chapter_id, chapter_data in analysis_results['chapter_analysis'].items():
                    sections.append(f"\n### {chapter_data['name']} (Score: {chapter_data.get('average_score', 0):.1f}/7)")
                    
                    # Add question analyses
                    if chapter_data.get('questions'):
                        for question in chapter_data['questions']:
                            sections.append(f"\n**{question['question_text']}**")
                            sections.append(f"Score: {question['score']}/7")
                            sections.append(question.get('response', 'No response available'))
                    sections.append("")
                
                # Overall Score (calculated from chapter scores only)
                if analysis_results.get('overall_score') is not None:
                    sections.append(f"\n**Overall Template Score: {analysis_results['overall_score']:.1f}/7**")
            else:
                sections.append("No chapter analysis available.")
            
            return "\n".join(sections)
            
        except Exception as e:
            logger.error(f"Error formatting template analysis: {e}")
            return f"Error formatting analysis results: {str(e)}"
    
    def _get_visual_analysis_for_deck(self, deck_id: int) -> Dict:
        """Get cached visual analysis for a single deck"""
        try:
            cached_analysis = self._get_cached_visual_analysis([deck_id])
            return cached_analysis.get(deck_id, {})
        except Exception as e:
            logger.error(f"Error getting visual analysis for deck {deck_id}: {e}")
            return {}

    def _format_visual_analysis_for_extraction(self, visual_analysis: Dict) -> str:
        """Format visual analysis data for extraction prompts"""
        try:
            if 'visual_analysis_results' not in visual_analysis:
                return "No visual analysis available"
            
            slides = visual_analysis['visual_analysis_results']
            formatted_text = ""
            
            for slide in slides:
                page_num = slide.get('page_number', 'Unknown')
                description = slide.get('description', 'No description available')
                formatted_text += f"Slide {page_num}: {description}\n\n"
            
            return formatted_text.strip()
        except Exception as e:
            logger.error(f"Error formatting visual analysis for extraction: {e}")
            return f"Error formatting visual analysis: {str(e)}"

    def _get_cached_visual_analysis(self, deck_ids: List[int]) -> Dict[int, Dict]:
        """Get cached visual analysis via HTTP from backend"""
        try:
            import requests
            import json
            
            logger.info(f"Retrieving cached visual analysis for {len(deck_ids)} decks via HTTP from backend")
            
            logger.info(f"Using backend server: {self.backend_url}")
            
            # Call the backend endpoint to get cached visual analysis
            response = requests.post(
                f"{self.backend_url}/api/dojo/internal/get-cached-visual-analysis",
                json={"deck_ids": deck_ids},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    cached_analysis = data.get("cached_analysis", {})
                    logger.info(f"DEBUG: Raw cached_analysis keys: {list(cached_analysis.keys())}")
                    # Convert string keys to integers for consistency
                    cached_analysis_int_keys = {int(k): v for k, v in cached_analysis.items()}
                    logger.info(f"DEBUG: Converted keys: {list(cached_analysis_int_keys.keys())}")
                    logger.info(f"Retrieved cached visual analysis for {len(cached_analysis)}/{len(deck_ids)} decks via HTTP from backend")
                    return cached_analysis_int_keys
                else:
                    logger.error(f"Backend returned error: {data.get('error', 'Unknown error')}")
                    return {}
            else:
                logger.error(f"HTTP request failed with status {response.status_code}: {response.text}")
                return {}
            
        except Exception as e:
            logger.error(f"Error getting cached visual analysis from backend: {e}")
            return {}
    
    def _run_extraction_step(self, deck_ids: List[int], prompt: str, text_model: str, extraction_type: str) -> List[Dict]:
        """Run a single extraction step for multiple decks"""
        extraction_results = []
        
        for deck_id in deck_ids:
            try:
                # Get visual analysis for this deck
                visual_analysis = self._get_visual_analysis_for_deck(deck_id)
                
                if not visual_analysis or 'visual_analysis_results' not in visual_analysis:
                    logger.warning(f"No visual analysis found for deck {deck_id}")
                    extraction_results.append({
                        "deck_id": deck_id,
                        f"{extraction_type}": "No visual analysis available for extraction"
                    })
                    continue
                
                # Format visual analysis for extraction prompt
                visual_context = self._format_visual_analysis_for_extraction(visual_analysis)
                
                # Create full prompt with visual context
                if "visual analysis" in prompt.lower():
                    full_prompt = f"""{prompt}

VISUAL ANALYSIS:
{visual_context}"""
                else:
                    full_prompt = f"""Based on the pitch deck visual analysis provided below, {prompt}

VISUAL ANALYSIS:
{visual_context}

IMPORTANT: Base your answer ONLY on the visual analysis above. If no meaningful visual analysis is provided, respond with "No visual analysis available for extraction"."""
                
                # Use ollama for extraction
                import ollama
                response = ollama.chat(
                    model=text_model,
                    messages=[{
                        'role': 'user',
                        'content': full_prompt
                    }],
                    options={'num_ctx': 32768, 'temperature': 0.3}
                )
                
                extraction_result = response['message']['content']
                
                extraction_results.append({
                    "deck_id": deck_id,
                    f"{extraction_type}": extraction_result,
                    "text_model_used": text_model
                })
                
                logger.info(f"Completed {extraction_type} for deck {deck_id}")
                
            except Exception as e:
                logger.error(f"Error in {extraction_type} for deck {deck_id}: {e}")
                extraction_results.append({
                    "deck_id": deck_id,
                    f"{extraction_type}": f"Error: {str(e)}",
                    "text_model_used": text_model
                })
        
        return extraction_results
    
    def _save_extraction_experiment(self, experiment_name: str, deck_ids: List[int], results: List[Dict], experiment_type: str) -> int:
        """Save extraction experiment results to database via HTTP"""
        try:
            import requests
            import json
            
            # Call backend to save experiment
            backend_url = os.getenv('BACKEND_PRODUCTION', 'http://65.108.32.168:8000')
            response = requests.post(f"{backend_url}/api/dojo/save-extraction-experiment", 
                json={
                    "experiment_name": experiment_name,
                    "deck_ids": deck_ids,
                    "results": results,
                    "experiment_type": experiment_type
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('experiment_id', 0)
            else:
                logger.error(f"Failed to save experiment: {response.status_code} - {response.text}")
                return 0
                
        except Exception as e:
            logger.error(f"Error saving extraction experiment: {e}")
            return 0
    
    def _run_classification_step(self, deck_ids: List[int], offering_results: List[Dict]) -> List[Dict]:
        """Run classification step using offering results"""
        classification_results = []
        
        for deck_id in deck_ids:
            try:
                # Find offering result for this deck
                deck_offering = None
                for result in offering_results:
                    if result.get('deck_id') == deck_id:
                        deck_offering = result.get('offering_extraction', '')
                        break
                
                if not deck_offering:
                    classification_results.append({
                        "deck_id": deck_id,
                        "classification_result": {"error": "No offering available for classification"}
                    })
                    continue
                
                # Use internal classification endpoint (no authentication required)
                import requests
                backend_url = os.getenv('BACKEND_PRODUCTION', 'http://65.108.32.168:8000')
                response = requests.post(f"{backend_url}/api/dojo/internal/classify",
                    json={
                        "company_offering": deck_offering
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    classification_data = response.json()
                    classification_results.append({
                        "deck_id": deck_id,
                        "classification_result": classification_data
                    })
                else:
                    classification_results.append({
                        "deck_id": deck_id,
                        "classification_result": {"error": f"Classification failed: {response.status_code}"}
                    })
                
            except Exception as e:
                logger.error(f"Error in classification for deck {deck_id}: {e}")
                classification_results.append({
                    "deck_id": deck_id,
                    "classification_result": {"error": str(e)}
                })
        
        return classification_results
    
    def _update_experiment_classification(self, experiment_id: int, results: List[Dict]):
        """Update experiment with classification results"""
        try:
            import requests
            backend_url = os.getenv('BACKEND_PRODUCTION', 'http://65.108.32.168:8000')
            requests.post(f"{backend_url}/api/dojo/update-extraction-classification", 
                json={
                    "experiment_id": experiment_id,
                    "classification_results": results
                },
                timeout=30
            )
        except Exception as e:
            logger.error(f"Error updating classification results: {e}")
    
    def _update_experiment_company_names(self, experiment_id: int, results: List[Dict]):
        """Update experiment with company name results"""
        try:
            import requests
            backend_url = os.getenv('BACKEND_PRODUCTION', 'http://65.108.32.168:8000')
            requests.post(f"{backend_url}/api/dojo/update-extraction-company-names", 
                json={
                    "experiment_id": experiment_id,
                    "company_name_results": results
                },
                timeout=30
            )
        except Exception as e:
            logger.error(f"Error updating company name results: {e}")
    
    def _update_experiment_funding_amounts(self, experiment_id: int, results: List[Dict]):
        """Update experiment with funding amount results"""
        try:
            import requests
            backend_url = os.getenv('BACKEND_PRODUCTION', 'http://65.108.32.168:8000')
            requests.post(f"{backend_url}/api/dojo/update-extraction-funding-amounts", 
                json={
                    "experiment_id": experiment_id,
                    "funding_amount_results": results
                },
                timeout=30
            )
        except Exception as e:
            logger.error(f"Error updating funding amount results: {e}")
    
    def _update_experiment_deck_dates(self, experiment_id: int, results: List[Dict]):
        """Update experiment with deck date results"""
        try:
            import requests
            backend_url = os.getenv('BACKEND_PRODUCTION', 'http://65.108.32.168:8000')
            requests.post(f"{backend_url}/api/dojo/update-extraction-deck-dates", 
                json={
                    "experiment_id": experiment_id,
                    "deck_date_results": results
                },
                timeout=30
            )
        except Exception as e:
            logger.error(f"Error updating deck date results: {e}")
    
    def _get_extraction_results_for_deck(self, deck_id: int) -> Dict[str, Any]:
        """Get extraction results from extraction experiments for a deck via HTTP"""
        try:
            import requests
            import json
            
            # Query the backend for extraction results
            logger.info(f"Retrieving extraction results for deck {deck_id} via HTTP from backend")
            
            # Call the new internal endpoint to get extraction results
            response = requests.get(
                f"{self.backend_url}/api/internal/get-extraction-results/{deck_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                result_data = response.json()
                if result_data.get("has_results", False):
                    extraction_results = result_data.get("extraction_results", {})
                    logger.info(f"✅ Retrieved extraction results for deck {deck_id}: {list(extraction_results.keys())}")
                    return extraction_results
                else:
                    logger.warning(f"⚠️ No extraction results found for deck {deck_id} in database")
                    return {}
            else:
                logger.error(f"❌ Failed to get extraction results for deck {deck_id}: {response.status_code}")
                return {}
            
        except Exception as e:
            logger.error(f"Error getting extraction results for deck {deck_id}: {e}")
            return {}

    def _load_template_from_db(self, template_id: int) -> Dict[str, Any]:
        """Load template configuration from database via HTTP"""
        try:
            import requests
            
            logger.info(f"Loading template {template_id} from backend")
            
            # Call backend to get template configuration
            response = requests.get(
                f"{self.backend_url}/api/healthcare-templates/templates/{template_id}",
                timeout=30
            )
            
            if response.status_code == 200:
                template_data = response.json()
                logger.info(f"Loaded template '{template_data.get('name', 'Unknown')}' with {len(template_data.get('chapters', []))} chapters")
                return template_data
            else:
                logger.error(f"Failed to load template {template_id}: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error loading template {template_id}: {e}")
            return {}
    
    def _cache_visual_analysis_result(self, deck_id: int, visual_results: Dict, vision_model: str, analysis_prompt: str):
        """Cache visual analysis result immediately to backend"""
        try:
            import requests
            import json
            
            logger.info(f"Using backend server for caching: {self.backend_url}")
            
            # Prepare the cache data
            cache_data = {
                "document_id": deck_id,
                "analysis_result_json": json.dumps(visual_results),
                "vision_model_used": vision_model,
                "prompt_used": analysis_prompt
            }
            
            # Make HTTP request to cache visual analysis
            response = requests.post(
                f"{self.backend_url}/api/dojo/internal/cache-visual-analysis",
                json=cache_data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Cached visual analysis via HTTP: deck {deck_id}")
            else:
                logger.error(f"Failed to cache visual analysis via HTTP: {response.status_code} - {response.text}")
            
        except Exception as e:
            logger.error(f"Error caching visual analysis via HTTP for deck {deck_id}: {e}")
    
    def _update_database_with_results(self, document_id: int, results_filename: str):
        """Update the database via HTTP request to the production server"""
        try:
            import requests
            
            logger.info(f"Using backend server for database updates: {self.backend_url}")
            
            # Prepare the update data
            update_data = {
                "document_id": document_id,
                "results_file_path": f"results/{results_filename}",
                "processing_status": "completed"
            }
            
            # Make HTTP request to update database
            response = requests.post(
                f"{self.backend_url}/api/internal/update-deck-results",
                json=update_data,
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"Updated database via HTTP: deck {document_id} -> results/{results_filename}")
            else:
                logger.error(f"Failed to update database via HTTP: {response.status_code} - {response.text}")
            
        except Exception as e:
            logger.error(f"Error updating database via HTTP for deck {document_id}: {e}")
    
    def _save_visual_analysis_and_feedback(self, document_id: int, visual_analysis_results: list):
        """Save Function 1: Visual analysis results and slide feedback
        This includes slide descriptions and AI-generated feedback for each slide."""
        try:
            import requests
            
            if not visual_analysis_results:
                logger.info(f"No visual analysis to save for document {document_id}")
                return
            
            logger.info(f"💾 [1/4] Saving visual analysis and feedback for document {document_id} ({len(visual_analysis_results)} slides)")
            
            # The visual analysis is already cached via _cache_visual_analysis_result
            # This function ensures it's properly saved for retrieval
            # Visual analysis includes: slide_image_path, description, feedback
            
            # For now, visual analysis is cached separately
            # In future, we may want to save it to a dedicated table
            logger.info(f"✅ Visual analysis already cached for document {document_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error saving visual analysis for document {document_id}: {e}")
            return False
    
    def _save_extraction_results(self, document_id: int, extraction_data: dict):
        """Save Function 2: Extraction experiment results
        This includes: company_offering, classification, funding_sought, deck_date, company_name"""
        try:
            import requests
            import json
            import time
            
            # Essential extraction fields
            essential_fields = ['company_offering', 'classification', 'funding_amount', 'deck_date', 'company_name']
            
            # Check if we have any extraction data
            has_data = any(extraction_data.get(field) for field in essential_fields)
            
            if not has_data:
                logger.info(f"No extraction results to save for document {document_id}")
                return False
            
            logger.info(f"💾 [2/4] Saving extraction results for document {document_id}")
            
            # Create experiment name
            experiment_name = f"extraction_deck_{document_id}"
            
            # Prepare extraction data - ensure all fields are present
            extraction_results = {
                str(document_id): {
                    "company_offering": extraction_data.get('company_offering', ''),
                    "classification": extraction_data.get('classification', {}),
                    "funding_amount": extraction_data.get('funding_amount', ''),
                    "deck_date": extraction_data.get('deck_date', ''),
                    "company_name": extraction_data.get('company_name', '')
                }
            }
            
            # Save to main project_documents table
            response = requests.post(
                f"{self.backend_url}/api/internal/update-deck-results",
                json={
                    "document_id": document_id,  # Changed from deck_id to document_id
                    "extraction_results": extraction_results[str(document_id)],
                    "results_file_path": "",  # Required field but not used for extraction
                    "processing_status": "completed",  # Required field
                    "extraction_type": "startup_upload",
                    "text_model_used": extraction_data.get('model_used', 'auto')
                },
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✅ [2/4] Successfully saved extraction results for document {document_id}")
                return True
            else:
                logger.error(f"❌ Failed to save extraction results: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error saving extraction results for document {document_id}: {e}")
            return False
    
    def _save_template_processing_only(self, document_id: int, template_results: dict):
        """Save Function 3: Template processing results only
        This includes: chapter_analysis, question_analysis, overall_score, template_used"""
        try:
            import requests
            import json
            
            # Check if we have template processing results
            chapter_analysis = template_results.get("chapter_analysis", {})
            
            if not chapter_analysis:
                logger.info(f"No template processing results to save for document {document_id}")
                return False
            
            logger.info(f"💾 [3/4] Saving template processing results for document {document_id}")
            
            # Prepare template-specific data (excluding special analyses)
            template_data = {
                "template_analysis": self._format_template_analysis_for_storage(template_results),
                "template_used": template_results.get("template_used", {}),
                "chapter_analysis": chapter_analysis,
                "question_analysis": template_results.get("question_analysis", {}),
                "overall_score": template_results.get("overall_score", 0.0),
                "report_chapters": template_results.get("report_chapters", {}),
                "report_scores": template_results.get("report_scores", {}),
                "processing_metadata": template_results.get("processing_metadata", {})
            }
            
            # Save template processing to extraction_experiments
            response = requests.post(
                f"{self.backend_url}/api/internal/save-template-processing",
                json={
                    "experiment_name": f"template_deck_{document_id}",
                    "document_id": document_id,
                    "template_processing_results": template_data
                },
                timeout=30
            )
            
            if response.status_code == 200:
                logger.info(f"✅ [3/4] Successfully saved template processing for document {document_id}")
                return True
            else:
                logger.error(f"❌ Failed to save template processing: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error saving template processing for document {document_id}: {e}")
            return False
    
    def _save_specialized_analysis(self, document_id: int, specialized_analysis: dict):
        """Save Function 4: Special analyses (regulatory, clinical, scientific)
        This is independent of template and can be toggled based on business model"""
        try:
            import requests
            
            # Filter out empty or None values
            filtered_analysis = {
                key: value for key, value in specialized_analysis.items() 
                if value and str(value).strip()
            }
            
            if not filtered_analysis:
                logger.info(f"No specialized analysis to save for document {document_id}")
                return False
            
            logger.info(f"💾 [4/4] Saving specialized analysis for document {document_id}: {list(filtered_analysis.keys())}")
            
            # Prepare the specialized analysis data
            analysis_data = {
                "document_id": document_id,
                "specialized_analysis": filtered_analysis
            }
            
            # Make HTTP request to save specialized analysis
            response = requests.post(
                f"{self.backend_url}/api/internal/save-specialized-analysis",
                json=analysis_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                saved_analyses = result.get('saved_analyses', [])
                logger.info(f"✅ [4/4] Successfully saved specialized analysis: {saved_analyses}")
                return True
            else:
                logger.error(f"❌ Failed to save specialized analysis: {response.status_code} - {response.text}")
                return False
            
        except Exception as e:
            logger.error(f"❌ Error saving specialized analysis for document {document_id}: {e}")
            return False
    
    
    def _format_template_analysis_for_storage(self, results: dict) -> str:
        """Format template analysis as text for compatibility"""
        chapter_analysis = results.get("chapter_analysis", {})
        
        if not chapter_analysis:
            return "No template analysis available."
        
        analysis_parts = []
        
        for chapter_key, chapter_data in chapter_analysis.items():
            chapter_name = chapter_data.get("name", chapter_key)
            chapter_text = f"## {chapter_name}\n\n"
            
            questions = chapter_data.get("questions", [])
            if questions:
                for question in questions:
                    chapter_text += f"**{question.get('question_text', 'Question')}**\n"
                    chapter_text += f"{question.get('response', 'No response provided')}\n"
                    chapter_text += f"*Score: {question.get('score', 'N/A')}/7*\n\n"
            
            # Add chapter score
            if "average_score" in chapter_data:
                chapter_text += f"**Chapter Score: {chapter_data['average_score']:.1f}/7**\n"
            
            analysis_parts.append(chapter_text)
        
        return "\n\n".join(analysis_parts)

    def register_with_queue_system(self) -> bool:
        """Register this GPU server with the processing queue system"""
        try:
            registration_data = {
                "server_id": self.server_id,
                "server_type": "gpu",
                "capabilities": {
                    "visual_processing": True,
                    "text_processing": True,
                    "template_analysis": True,
                    "specialized_analysis": True
                },
                "max_concurrent_tasks": 3
            }
            
            response = requests.post(
                f"{self.backend_url}/api/internal/register-processing-server",
                json=registration_data,
                timeout=30
            )
            
            if response.status_code == 200:
                self.is_registered = True
                logger.info(f"✅ Successfully registered GPU server {self.server_id} with processing queue")
                return True
            else:
                logger.error(f"❌ Failed to register GPU server: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error registering GPU server: {e}")
            return False

    def send_heartbeat(self):
        """Send periodic heartbeat to backend to maintain server registration"""
        while not self.shutdown_flag:
            try:
                if self.is_registered:
                    response = requests.post(
                        f"{self.backend_url}/api/internal/server-heartbeat",
                        json={"server_id": self.server_id},
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        logger.debug(f"💓 Heartbeat sent for server {self.server_id}")
                    else:
                        logger.warning(f"⚠️ Heartbeat failed: {response.status_code}")
                        # Try to re-register if heartbeat fails
                        self.is_registered = False
                        self.register_with_queue_system()
                
                time.sleep(30)  # Send heartbeat every 30 seconds
                
            except Exception as e:
                logger.error(f"❌ Heartbeat error: {e}")
                time.sleep(30)

    def poll_for_queue_tasks(self):
        """Poll the backend for available processing queue tasks"""
        logger.info(f"🔍 Starting queue task polling for server {self.server_id}")
        
        while not self.shutdown_flag:
            try:
                if self.is_registered:
                    # Request next available task from processing queue
                    response = requests.post(
                        f"{self.backend_url}/api/internal/get-next-queue-task",
                        json={
                            "server_id": self.server_id,
                            "capabilities": {
                                "visual_processing": True,
                                "text_processing": True,
                                "template_analysis": True,
                                "specialized_analysis": True
                            }
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        task_data = response.json()
                        if task_data and task_data.get("task_id"):
                            logger.info(f"📋 Received queue task: {task_data['task_id']} - {task_data.get('task_type')}")
                            self.process_queue_task(task_data)
                        else:
                            # No tasks available, sleep longer
                            time.sleep(10)
                    else:
                        logger.warning(f"⚠️ Queue polling failed: {response.status_code}")
                        time.sleep(10)
                else:
                    # Not registered, try to register
                    if not self.register_with_queue_system():
                        time.sleep(30)  # Wait before retrying registration
                    else:
                        time.sleep(5)   # Quick check after successful registration
                        
                time.sleep(5)  # Base polling interval
                
            except Exception as e:
                logger.error(f"❌ Queue polling error: {e}")
                time.sleep(10)

    def process_queue_task(self, task_data: Dict[str, Any]):
        """Process a task received from the processing queue"""
        task_id = task_data.get("task_id")
        task_type = task_data.get("task_type")
        document_id = task_data.get("document_id")
        
        logger.info(f"🚀 Processing queue task {task_id}: {task_type} for document {document_id}")
        
        try:
            # Update task status to processing
            self.update_task_status(task_id, "processing", "Task picked up by GPU server")
            
            # Route task based on type
            if task_type == "pdf_analysis":
                # This is the main processing task - delegate to PDF processor
                success = self.process_full_pdf_analysis(task_data)
            elif task_type.startswith("specialized_"):
                # Handle specialized analysis tasks
                success = self.process_specialized_analysis(task_data)
            else:
                logger.warning(f"⚠️ Unknown task type: {task_type}")
                success = False
            
            if success:
                self.update_task_status(task_id, "completed", "Task completed successfully")
                logger.info(f"✅ Completed queue task {task_id}")
            else:
                self.update_task_status(task_id, "failed", "Task processing failed")
                logger.error(f"❌ Failed queue task {task_id}")
                
        except Exception as e:
            logger.error(f"❌ Error processing queue task {task_id}: {e}")
            self.update_task_status(task_id, "failed", f"Task error: {str(e)}")

    def update_task_status(self, task_id: int, status: str, message: str):
        """Update task status in the processing queue"""
        try:
            response = requests.post(
                f"{self.backend_url}/api/internal/update-task-status",
                json={
                    "task_id": task_id,
                    "status": status,
                    "message": message,
                    "server_id": self.server_id
                },
                timeout=30
            )
            
            if response.status_code == 200:
                logger.debug(f"✅ Updated task {task_id} status to {status}")
            else:
                logger.error(f"❌ Failed to update task status: {response.status_code}")
                
        except Exception as e:
            logger.error(f"❌ Error updating task status: {e}")

    def process_full_pdf_analysis(self, task_data: Dict[str, Any]) -> bool:
        """Process full PDF analysis using the existing PDF processor"""
        try:
            file_path = task_data.get("file_path")
            company_id = task_data.get("company_id") 
            document_id = task_data.get("document_id")
            task_id = task_data.get("task_id")
            
            if not all([file_path, company_id, document_id, task_id]):
                logger.error(f"❌ Missing required task data: file_path={file_path}, company_id={company_id}, document_id={document_id}, task_id={task_id}")
                return False
            
            # Use existing PDF processor
            result = self.pdf_processor.process_pdf_complete(
                file_path=file_path,
                company_id=company_id,
                deck_id=document_id  # PDF processor still uses deck_id parameter name
            )
            
            success = result.get("success", False)
            
            if success:
                # Notify backend that main task is complete AND create specialized analysis tasks
                logger.info(f"🎯 Main PDF analysis completed for document {document_id}, creating specialized analysis tasks")
                
                response = requests.post(
                    f"{self.backend_url}/api/internal/complete-task-and-create-specialized",
                    json={
                        "task_id": task_id,
                        "document_id": document_id,
                        "success": True,
                        "results_path": result.get("results_path"),
                        "metadata": result.get("metadata", {})
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    logger.info(f"✅ Successfully completed main task and created specialized analysis tasks for document {document_id}")
                else:
                    logger.error(f"❌ Failed to complete task and create specialized analysis: {response.status_code}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error in full PDF analysis: {e}")
            return False

    def process_specialized_analysis(self, task_data: Dict[str, Any]) -> bool:
        """Process specialized analysis tasks (clinical, regulatory, science)"""
        try:
            document_id = task_data.get("document_id")
            task_type = task_data.get("task_type")
            
            # Extract analysis type from task_type (e.g., "specialized_clinical" -> "clinical")
            analysis_type = task_type.replace("specialized_", "")
            
            logger.info(f"🔬 Starting {analysis_type} specialized analysis for document {document_id}")
            
            # Use PDF processor's specialized analysis method
            success = self.pdf_processor.process_specialized_analysis(document_id, analysis_type)
            
            if success:
                logger.info(f"✅ Completed {analysis_type} specialized analysis for document {document_id}")
            else:
                logger.error(f"❌ Failed {analysis_type} specialized analysis for document {document_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error in specialized analysis: {e}")
            return False

    def start_background_services(self):
        """Start heartbeat and queue polling background threads"""
        logger.info("🚀 Starting GPU server background services")
        
        # Register with the queue system first
        if not self.register_with_queue_system():
            logger.error("❌ Failed to register with queue system - will retry in background")
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        self.heartbeat_thread.start()
        logger.info("💓 Started heartbeat thread")
        
        # Start queue polling thread
        self.queue_polling_thread = threading.Thread(target=self.poll_for_queue_tasks, daemon=True)
        self.queue_polling_thread.start()
        logger.info("🔍 Started queue polling thread")

    def shutdown_background_services(self):
        """Shutdown background services gracefully"""
        logger.info("🛑 Shutting down GPU server background services")
        self.shutdown_flag = True
        
        # Unregister from queue system
        try:
            if self.is_registered:
                requests.post(
                    f"{self.backend_url}/api/internal/unregister-processing-server",
                    json={"server_id": self.server_id},
                    timeout=10
                )
                logger.info(f"✅ Unregistered server {self.server_id} from queue system")
        except Exception as e:
            logger.error(f"❌ Error unregistering server: {e}")

    def run(self, host: str = None, port: int = None):
        """Run the HTTP server"""
        # Use environment variables or defaults
        host = host or os.getenv("GPU_HTTP_HOST", "0.0.0.0")
        port = port or int(os.getenv("GPU_HTTP_PORT", "8001"))
        
        logger.info(f"Starting GPU HTTP server on {host}:{port}")
        logger.info(f"Using mount path: {config.mount_path}")
        logger.info(f"Results will be saved to: {config.results_path}")
        
        # Start background services (registration, heartbeat, queue polling)
        self.start_background_services()
        
        try:
            self.app.run(host=host, port=port, debug=False)
        finally:
            # Ensure cleanup on shutdown
            self.shutdown_background_services()

def main():
    """Main entry point"""
    server = GPUHTTPServer()
    server.run()

if __name__ == "__main__":
    main()