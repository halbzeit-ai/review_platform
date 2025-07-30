#!/usr/bin/env python3
"""
Real GPU HTTP Server for PDF Processing
Uses actual AI models via Ollama
"""

import logging
import os
import json
import ollama
from flask import Flask, request, jsonify
from datetime import datetime
from pathlib import Path

# Import the existing PDF processor
from main import PDFProcessor
from config.processing_config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Development configuration - use dev-shared instead of CPU-GPU
SHARED_DIR = os.environ.get("SHARED_DIR", "/mnt/dev-shared")
UPLOADS_DIR = f"{SHARED_DIR}/uploads"
RESULTS_DIR = f"{SHARED_DIR}/results"

# Initialize PDF processor with development paths
pdf_processor = PDFProcessor(mount_path=SHARED_DIR)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint with Ollama status"""
    try:
        # Check if Ollama is available
        models = ollama.list()
        model_names = [m['name'] for m in models['models']] if 'models' in models else []
        ollama_status = True
    except Exception as e:
        logger.error(f"Ollama not available: {e}")
        model_names = []
        ollama_status = False
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "shared_dir": SHARED_DIR,
        "uploads_exist": os.path.exists(UPLOADS_DIR),
        "results_exist": os.path.exists(RESULTS_DIR),
        "ollama_available": ollama_status,
        "installed_models": model_names
    })

@app.route('/api/process-pdf', methods=['POST'])
def process_pdf():
    """Process a PDF file using real AI models"""
    data = request.json
    
    pitch_deck_id = data.get('pitch_deck_id')
    file_path = data.get('file_path')
    company_id = data.get('company_id')
    
    if not file_path:
        return jsonify({"error": "No file_path provided"}), 400
    
    try:
        logger.info(f"Processing PDF {pitch_deck_id}: {file_path}")
        
        # Process the PDF using the existing processor
        result = pdf_processor.process_pdf(file_path, company_id)
        
        # The processor returns a dict with the result file path
        if result.get('success'):
            logger.info(f"Successfully processed PDF {pitch_deck_id}")
            return jsonify({
                "success": True,
                "results_file": result.get('results_file'),
                "results_path": result.get('results_path'),
                "message": f"PDF processed successfully for pitch deck {pitch_deck_id}"
            })
        else:
            error_msg = result.get('error', 'Unknown processing error')
            logger.error(f"Processing failed: {error_msg}")
            return jsonify({
                "success": False,
                "error": error_msg
            }), 500
            
    except Exception as e:
        logger.error(f"Error processing PDF: {str(e)}", exc_info=True)
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

@app.route('/api/models', methods=['GET'])
def list_models():
    """List installed Ollama models"""
    try:
        models = ollama.list()
        model_list = []
        for model in models.get('models', []):
            model_list.append({
                "name": model['name'],
                "size": f"{model['size'] / 1e9:.1f}GB",
                "modified": model.get('modified_at', 'unknown')
            })
        return jsonify({"models": model_list})
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return jsonify({"models": [], "error": str(e)}), 500

@app.route('/api/pull-model', methods=['POST'])
def pull_model():
    """Pull a new model"""
    data = request.json
    model_name = data.get('model_name')
    
    if not model_name:
        return jsonify({"error": "No model_name provided"}), 400
    
    try:
        logger.info(f"Pulling model: {model_name}")
        ollama.pull(model_name)
        return jsonify({"success": True, "message": f"Model {model_name} pulled successfully"})
    except Exception as e:
        logger.error(f"Error pulling model: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    logger.info(f"Starting Real GPU HTTP Server")
    logger.info(f"Shared directory: {SHARED_DIR}")
    logger.info(f"Uploads directory: {UPLOADS_DIR}")
    logger.info(f"Results directory: {RESULTS_DIR}")
    
    # Check Ollama status
    try:
        models = ollama.list()
        logger.info(f"Ollama is available with {len(models.get('models', []))} models")
    except Exception as e:
        logger.warning(f"Ollama not available: {e}")
        logger.warning("Make sure Ollama is installed and running!")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=8001, debug=False)