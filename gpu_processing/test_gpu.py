#!/usr/bin/env python3
"""
GPU Server Test Script
Test GPU server functionality including ollama and HTTP endpoints
"""

import os
import json
import logging
import requests
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_ollama():
    """Test direct ollama functionality"""
    logger.info("Testing ollama functionality...")
    
    try:
        import ollama
        
        # List models
        models = ollama.list()
        logger.info(f"✅ Ollama connected: {len(models.get('models', []))} models")
        
        for model in models.get('models', [])[:3]:  # Show first 3 models
            logger.info(f"  - {model.model}")
            
        # Test simple generation if we have models
        available_models = [model.model for model in models.get('models', [])]
        if available_models:
            test_model = available_models[0]
            logger.info(f"Testing generation with: {test_model}")
            
            response = ollama.generate(
                model=test_model,
                prompt="Say hello in one word.",
                options={'num_ctx': 1024, 'temperature': 0.3}
            )
            
            logger.info(f"✅ Generation test: {response['response'][:50]}...")
        else:
            logger.error("❌ No models available")
            
    except ImportError:
        logger.error("❌ Ollama not installed")
    except Exception as e:
        logger.error(f"❌ Ollama test failed: {e}")

def test_http_server():
    """Test if GPU HTTP server is running"""
    logger.info("Testing GPU HTTP server...")
    
    base_url = "http://localhost:8001/api"
    
    try:
        # Test health endpoint
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            logger.info(f"✅ Health endpoint: {data.get('status')}")
            logger.info(f"  Ollama available: {data.get('ollama_available')}")
        else:
            logger.error(f"❌ Health endpoint failed: {response.status_code}")
            
    except requests.ConnectionError:
        logger.error("❌ GPU HTTP server not running on localhost:8001")
    except Exception as e:
        logger.error(f"❌ HTTP server test failed: {e}")

def test_classification_endpoint():
    """Test the new classification endpoint"""
    logger.info("Testing classification endpoint...")
    
    base_url = "http://localhost:8001/api"
    
    try:
        # First check if we have models
        health_response = requests.get(f"{base_url}/health", timeout=5)
        if health_response.status_code != 200:
            logger.error("❌ Cannot test classification - health check failed")
            return
            
        # Get available models
        models_response = requests.get(f"{base_url}/models", timeout=10)
        if models_response.status_code == 200:
            models_data = models_response.json()
            models = models_data.get('models', [])
            if not models:
                logger.error("❌ No models available for classification test")
                return
                
            test_model = models[0]['name']
            logger.info(f"Testing classification with model: {test_model}")
            
            # Test classification
            payload = {
                "model": test_model,
                "prompt": "Respond with just the word 'test':",
                "options": {
                    "num_ctx": 1024,
                    "temperature": 0.3
                }
            }
            
            response = requests.post(
                f"{base_url}/run-classification",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    logger.info(f"✅ Classification endpoint works: {data.get('response', '')[:50]}...")
                else:
                    logger.error(f"❌ Classification failed: {data.get('error')}")
            else:
                logger.error(f"❌ Classification endpoint failed: {response.status_code} - {response.text}")
                
    except Exception as e:
        logger.error(f"❌ Classification endpoint test failed: {e}")

def main():
    """Main test function"""
    print("🚀 GPU Server Test Script")
    print("=" * 40)
    
    # Test ollama directly
    test_ollama()
    print()
    
    # Test HTTP server
    test_http_server()
    print()
    
    # Test classification endpoint
    test_classification_endpoint()
    
    print("\n" + "=" * 40)
    print("GPU test completed!")

if __name__ == "__main__":
    main()