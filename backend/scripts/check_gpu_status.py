#!/usr/bin/env python3
"""
Check GPU server status and processing capabilities
"""

import requests
import json
import time
import logging
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_gpu_server_health():
    """Check if GPU server is responsive"""
    # Get GPU URL based on environment
    environment = os.environ.get('ENVIRONMENT', 'development')
    if environment == 'production':
        gpu_host = os.environ.get('GPU_PRODUCTION', 'localhost')
    else:
        gpu_host = os.environ.get('GPU_DEVELOPMENT', 'localhost')
    
    # Fallback to legacy variable
    if gpu_host == 'localhost':
        gpu_host = os.environ.get('GPU_INSTANCE_HOST', 'localhost')
    
    gpu_url = f'http://{gpu_host}:8001'
    
    try:
        # Try to reach GPU server health endpoint
        response = requests.get(f"{gpu_url}/api/health", timeout=30)
        
        if response.status_code == 200:
            logger.info("✅ GPU server is responsive")
            return True
        else:
            logger.error(f"❌ GPU server returned status {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("❌ GPU server health check timed out (30s)")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("❌ Cannot connect to GPU server")
        return False
    except Exception as e:
        logger.error(f"❌ GPU server health check failed: {e}")
        return False

def check_gpu_processing_status():
    """Check current GPU processing status"""
    # Get GPU URL based on environment
    environment = os.environ.get('ENVIRONMENT', 'development')
    if environment == 'production':
        gpu_host = os.environ.get('GPU_PRODUCTION', 'localhost')
    else:
        gpu_host = os.environ.get('GPU_DEVELOPMENT', 'localhost')
    
    # Fallback to legacy variable
    if gpu_host == 'localhost':
        gpu_host = os.environ.get('GPU_INSTANCE_HOST', 'localhost')
    
    gpu_url = f'http://{gpu_host}:8001'
    
    try:
        # Check current processing status
        response = requests.get(f"{gpu_url}/processing/status", timeout=10)
        
        if response.status_code == 200:
            status = response.json()
            logger.info(f"📊 GPU Processing Status: {json.dumps(status, indent=2)}")
            return status
        else:
            logger.warning(f"⚠️ Could not get GPU processing status: {response.status_code}")
            return None
            
    except Exception as e:
        logger.warning(f"⚠️ Could not check GPU processing status: {e}")
        return None

def check_ollama_models():
    """Check if Ollama models are available"""
    try:
        # This would need to be run on the GPU server
        import ollama
        models = ollama.list()
        logger.info(f"🤖 Available Ollama models: {[m['name'] for m in models['models']]}")
        return models
    except Exception as e:
        logger.warning(f"⚠️ Could not check Ollama models: {e}")
        return None

def test_simple_processing():
    """Test a simple processing request"""
    # Get GPU URL based on environment
    environment = os.environ.get('ENVIRONMENT', 'development')
    if environment == 'production':
        gpu_host = os.environ.get('GPU_PRODUCTION', 'localhost')
    else:
        gpu_host = os.environ.get('GPU_DEVELOPMENT', 'localhost')
    
    # Fallback to legacy variable
    if gpu_host == 'localhost':
        gpu_host = os.environ.get('GPU_INSTANCE_HOST', 'localhost')
    
    gpu_url = f'http://{gpu_host}:8001'
    
    try:
        # Test simple processing
        test_payload = {
            "file_path": "test.pdf",
            "company_id": "test"
        }
        
        response = requests.post(
            f"{gpu_url}/process", 
            json=test_payload, 
            timeout=60
        )
        
        if response.status_code == 200:
            logger.info("✅ GPU server can accept processing requests")
            return True
        else:
            logger.error(f"❌ GPU processing test failed: {response.status_code}")
            return False
            
    except requests.exceptions.Timeout:
        logger.error("❌ GPU processing test timed out")
        return False
    except Exception as e:
        logger.error(f"❌ GPU processing test failed: {e}")
        return False

def main():
    """Main diagnostic function"""
    logger.info("🔍 GPU Server Diagnostic Check")
    logger.info("=" * 50)
    
    # Check GPU server health
    logger.info("1. Checking GPU server health...")
    gpu_healthy = check_gpu_server_health()
    
    # Check processing status
    logger.info("2. Checking GPU processing status...")
    processing_status = check_gpu_processing_status()
    
    # Check Ollama models (if accessible)
    logger.info("3. Checking Ollama models...")
    models = check_ollama_models()
    
    # Test simple processing
    logger.info("4. Testing simple processing...")
    processing_works = test_simple_processing()
    
    # Summary
    logger.info("=" * 50)
    logger.info("📋 DIAGNOSTIC SUMMARY:")
    logger.info(f"  GPU Server Health: {'✅ OK' if gpu_healthy else '❌ FAILED'}")
    logger.info(f"  Processing Status: {'✅ OK' if processing_status else '❌ UNKNOWN'}")
    logger.info(f"  Ollama Models: {'✅ OK' if models else '❌ UNKNOWN'}")
    logger.info(f"  Processing Test: {'✅ OK' if processing_works else '❌ FAILED'}")
    
    if not gpu_healthy:
        logger.error("🚨 GPU server is not responding - check if it's running")
    elif not processing_works:
        logger.error("🚨 GPU server is responding but processing is failing")
    else:
        logger.info("🎉 GPU server appears to be working correctly")
    
    return gpu_healthy and processing_works

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)