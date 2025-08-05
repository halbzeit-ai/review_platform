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
from flask import Flask, request, jsonify
from datetime import datetime
from typing import Dict, Any, List
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
        
        logger.info(f"Initialized GPUHTTPServer with backend URL: {self.backend_url}")
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
                        
                        batch_results.append({
                            "deck_id": deck_id,
                            "success": True,
                            "template_analysis": template_analysis
                        })
                        
                        logger.info(f"Completed template processing for deck {deck_id}")
                        
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
                
                # vision_model and analysis_prompt are now optional - will use database defaults if not provided
                
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
        
        @self.app.route('/api/processing-progress/<int:pitch_deck_id>', methods=['GET'])
        def get_processing_progress(pitch_deck_id: int):
            """Get processing progress for a specific pitch deck"""
            try:
                logger.info(f"Getting processing progress for pitch deck {pitch_deck_id}")
                
                # For now, we'll implement a basic progress tracking system
                # In a real implementation, this would track actual processing stages
                
                # Check if there's an active processing job for this deck
                # This is a simplified version - in production you'd track actual progress
                
                # Try to determine status based on file system state
                import os
                from pathlib import Path
                
                # Check for results file
                results_pattern = f"job_{pitch_deck_id}_*_results.json"
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
                logger.error(f"Error getting processing progress for pitch deck {pitch_deck_id}: {e}")
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
                        
                        # Check if we should use the healthcare template analyzer for chapter-by-chapter analysis
                        logger.info(f"DEBUG: template_info = {template_info}")
                        logger.info(f"DEBUG: template_info.get('id') = {template_info.get('id') if template_info else 'template_info is None'}")
                        use_chapter_analysis = template_info and template_info.get('id') is not None
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
                                SELECT file_path FROM pitch_decks WHERE id = %s
                                UNION
                                SELECT file_path FROM project_documents WHERE id = %s AND document_type = 'pitch_deck'
                            """, (deck_id, deck_id))
                            
                            result = cursor.fetchone()
                            cursor.close()
                            conn.close()
                            
                            if result and result[0]:
                                pdf_path = result[0]
                                full_pdf_path = str(Path(config.mount_path) / pdf_path)
                                
                                # Create analyzer and run full analysis
                                from utils.healthcare_template_analyzer import HealthcareTemplateAnalyzer
                                analyzer = HealthcareTemplateAnalyzer()
                                
                                # The analyzer will load the template from database using template_id
                                # We need to set the template config before calling analyze_pdf
                                try:
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
                                
                                # Run the analysis with progress callback 
                                analysis_results = analyzer.analyze_pdf(
                                    full_pdf_path, 
                                    company_id="dojo",
                                    progress_callback=progress_callback,
                                    deck_id=deck_id
                                )
                                
                                # Extract the formatted template analysis
                                template_analysis = self._format_template_analysis(analysis_results)
                                
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
    
    def _get_extraction_results_for_deck(self, deck_id: int) -> Dict[str, Any]:
        """Get extraction results from extraction experiments for a deck via HTTP"""
        try:
            import requests
            import json
            
            # Query the backend for extraction results
            logger.info(f"Retrieving extraction results for deck {deck_id} via HTTP from backend")
            
            # Create a dedicated backend endpoint for getting extraction results
            # For now, return empty dict to avoid the error - we'll need to implement this endpoint
            logger.warning(f"Extraction results endpoint not yet implemented - proceeding without Step 3 data for deck {deck_id}")
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
                "pitch_deck_id": deck_id,
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
    
    def _update_database_with_results(self, pitch_deck_id: int, results_filename: str):
        """Update the database via HTTP request to the production server"""
        try:
            import requests
            
            logger.info(f"Using backend server for database updates: {self.backend_url}")
            
            # Prepare the update data
            update_data = {
                "pitch_deck_id": pitch_deck_id,
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