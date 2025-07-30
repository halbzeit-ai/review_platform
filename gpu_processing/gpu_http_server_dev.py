#!/usr/bin/env python3
"""
Development GPU HTTP Server for PDF Processing
Simplified version for development environment
"""

import logging
import os
import json
from flask import Flask, request, jsonify
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Development configuration
SHARED_DIR = "/mnt/dev-shared"
UPLOADS_DIR = f"{SHARED_DIR}/uploads"
RESULTS_DIR = f"{SHARED_DIR}/results"

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "shared_dir": SHARED_DIR,
        "uploads_exist": os.path.exists(UPLOADS_DIR),
        "results_exist": os.path.exists(RESULTS_DIR)
    })

@app.route('/api/process', methods=['POST'])
def process_pdf():
    """Process a PDF file"""
    data = request.json
    pdf_filename = data.get('filename')
    
    if not pdf_filename:
        return jsonify({"error": "No filename provided"}), 400
    
    pdf_path = os.path.join(UPLOADS_DIR, pdf_filename)
    
    if not os.path.exists(pdf_path):
        return jsonify({"error": f"File not found: {pdf_filename}"}), 404
    
    # For development, create a mock result
    result = {
        "filename": pdf_filename,
        "processed_at": datetime.now().isoformat(),
        "status": "success",
        "analysis": {
            "summary": "This is a development mock analysis",
            "key_points": [
                "Mock point 1",
                "Mock point 2",
                "Mock point 3"
            ],
            "score": 85
        }
    }
    
    # Save result to results directory
    result_filename = f"{Path(pdf_filename).stem}_result.json"
    result_path = os.path.join(RESULTS_DIR, result_filename)
    
    with open(result_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Processed {pdf_filename}, result saved to {result_filename}")
    
    return jsonify({
        "status": "success",
        "result_file": result_filename,
        "result": result
    })

@app.route('/api/models', methods=['GET'])
def list_models():
    """List available models (mock for development)"""
    return jsonify({
        "models": [
            {"name": "mock-model-1", "size": "7B"},
            {"name": "mock-model-2", "size": "13B"}
        ]
    })

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    logger.info(f"Starting GPU HTTP Server (Development)")
    logger.info(f"Shared directory: {SHARED_DIR}")
    logger.info(f"Uploads directory: {UPLOADS_DIR}")
    logger.info(f"Results directory: {RESULTS_DIR}")
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=8001, debug=True)