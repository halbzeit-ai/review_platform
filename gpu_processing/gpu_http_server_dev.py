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
@app.route('/api/process-pdf', methods=['POST'])
def process_pdf():
    """Process a PDF file"""
    data = request.json
    
    # Handle both old and new parameter formats
    document_id = data.get('document_id', data.get('pitch_deck_id'))  # Backwards compatibility
    file_path = data.get('file_path')
    company_id = data.get('company_id')
    
    # Also support simple filename parameter
    if not file_path:
        file_path = data.get('filename')
    
    if not file_path:
        return jsonify({"error": "No file_path or filename provided"}), 400
    
    # The file_path might be a relative path like "uploads/company_name/uuid/filename.pdf"
    # Remove the "uploads/" prefix if present
    if file_path.startswith("uploads/"):
        relative_path = file_path[8:]  # Remove "uploads/" prefix
    else:
        relative_path = file_path
    
    # Build the full path
    pdf_path = os.path.join(UPLOADS_DIR, relative_path)
    pdf_filename = os.path.basename(file_path)
    
    logger.info(f"Processing request - file_path: {file_path}, pdf_path: {pdf_path}")
    
    if not os.path.exists(pdf_path):
        logger.error(f"File not found at {pdf_path}")
        # List what files exist in the uploads directory for debugging
        logger.info(f"Files in {UPLOADS_DIR}: {os.listdir(UPLOADS_DIR)}")
        return jsonify({"error": f"File not found: {pdf_filename} at path {pdf_path}"}), 404
    
    # For development, create a mock result
    result = {
        "filename": pdf_filename,
        "document_id": document_id,
        "company_id": company_id,
        "processed_at": datetime.now().isoformat(),
        "status": "success",
        "analysis": {
            "summary": "This is a development mock analysis for your startup pitch deck.",
            "key_points": [
                "Strong value proposition identified",
                "Market opportunity well defined",
                "Team expertise demonstrated"
            ],
            "score": 85,
            "strengths": [
                "Clear problem statement",
                "Innovative solution approach",
                "Experienced founding team"
            ],
            "areas_for_improvement": [
                "Financial projections need more detail",
                "Competitive analysis could be expanded",
                "Go-to-market strategy requires refinement"
            ]
        }
    }
    
    # Save result to results directory
    result_filename = f"{Path(pdf_filename).stem}_result.json"
    result_path = os.path.join(RESULTS_DIR, result_filename)
    
    with open(result_path, 'w') as f:
        json.dump(result, f, indent=2)
    
    logger.info(f"Processed document {document_id}: {pdf_filename}, result saved to {result_filename}")
    
    # Return response in the format expected by the backend
    return jsonify({
        "success": True,
        "results_file": result_filename,
        "results_path": result_path,
        "message": f"PDF processed successfully for document {document_id}"
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