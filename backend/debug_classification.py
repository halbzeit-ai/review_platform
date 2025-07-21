#!/usr/bin/env python3
"""
Classification Debug Script
Can run on either CPU or GPU server to test classification functionality
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent))

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def detect_server_type():
    """Detect if we're on CPU or GPU server"""
    try:
        import ollama
        ollama.list()
        return "GPU"
    except ImportError:
        return "CPU"
    except Exception:
        return "CPU"

async def test_cpu_server():
    """Test classification from CPU server perspective"""
    logger.info("Testing CPU server classification...")
    
    try:
        # Test database connection
        from app.db.database import get_db
        from app.services.startup_classifier import StartupClassifier
        
        db = next(get_db())
        logger.info("✅ Database connection successful")
        
        # Test classifier initialization
        classifier = StartupClassifier(db)
        logger.info("✅ StartupClassifier initialized")
        logger.info(f"Classification model: {classifier.classification_model}")
        logger.info(f"Available sectors: {len(classifier.sectors)}")
        
        if classifier.sectors:
            logger.info(f"Sample sector: {classifier.sectors[0]['name']} - {classifier.sectors[0]['display_name']}")
        
        # Test GPU HTTP client
        from app.services.gpu_http_client import gpu_http_client
        from app.core.config import settings
        
        logger.info(f"GPU Host configured: {settings.GPU_INSTANCE_HOST}")
        
        # Test GPU availability
        is_available = gpu_http_client.is_available()
        logger.info(f"GPU server available: {is_available}")
        
        if is_available:
            # Test classification via HTTP
            test_offering = "We provide AI-powered medical imaging solutions to help radiologists detect cancer more accurately."
            
            logger.info("Testing classification via GPU HTTP...")
            result = await classifier.classify(test_offering)
            
            logger.info("✅ Classification completed")
            logger.info(f"Primary sector: {result.get('primary_sector')}")
            logger.info(f"Confidence: {result.get('confidence_score')}")
            logger.info(f"Reasoning: {result.get('reasoning', '')[:100]}...")
        else:
            logger.error("❌ GPU server not available")
            
    except Exception as e:
        logger.error(f"❌ CPU server test failed: {e}")
        import traceback
        traceback.print_exc()

def test_gpu_server():
    """Test classification from GPU server perspective"""
    logger.info("Testing GPU server classification...")
    
    try:
        import ollama
        
        # Test ollama connection
        models = ollama.list()
        logger.info("✅ Ollama connection successful")
        logger.info(f"Available models: {[model.model for model in models.get('models', [])]}")
        
        # Test direct classification
        test_prompt = """
You are a healthcare venture capital analyst. Classify this startup:

Company Offering: "We provide AI-powered medical imaging solutions to help radiologists detect cancer more accurately."

Healthcare Sectors:
- HealthTech: General health technology solutions

Respond in JSON format with:
{
  "primary_sector": "healthtech",
  "confidence": 0.85,
  "reasoning": "This is an AI-powered medical imaging solution for cancer detection"
}
"""
        
        # Try to use the first available model
        available_models = [model.model for model in models.get('models', [])]
        if available_models:
            test_model = available_models[0]
            logger.info(f"Testing with model: {test_model}")
            
            response = ollama.generate(
                model=test_model,
                prompt=test_prompt,
                options={'num_ctx': 8192, 'temperature': 0.3}
            )
            
            logger.info("✅ Direct ollama classification successful")
            logger.info(f"Response: {response['response'][:200]}...")
        else:
            logger.error("❌ No models available")
            
        # Test HTTP server endpoints
        logger.info("Testing GPU HTTP server...")
        
        # Import GPU server components
        try:
            from gpu_http_server import GPUHTTPServer
            logger.info("✅ GPU HTTP server components available")
        except ImportError as e:
            logger.error(f"❌ Cannot import GPU server components: {e}")
            
    except ImportError:
        logger.error("❌ Ollama not available - not on GPU server")
    except Exception as e:
        logger.error(f"❌ GPU server test failed: {e}")
        import traceback
        traceback.print_exc()

async def test_end_to_end():
    """Test end-to-end classification flow"""
    logger.info("Testing end-to-end classification flow...")
    
    server_type = detect_server_type()
    logger.info(f"Detected server type: {server_type}")
    
    if server_type == "CPU":
        await test_cpu_server()
    else:
        test_gpu_server()

def test_database_schema():
    """Test if required database tables exist"""
    logger.info("Testing database schema...")
    
    try:
        from app.db.database import get_db
        from sqlalchemy import text
        
        db = next(get_db())
        
        # Test extraction_experiments table
        result = db.execute(text("SELECT COUNT(*) FROM extraction_experiments")).fetchone()
        logger.info(f"✅ extraction_experiments table: {result[0]} rows")
        
        # Test classification columns
        try:
            result = db.execute(text("SELECT classification_enabled, classification_results_json FROM extraction_experiments LIMIT 1")).fetchone()
            logger.info("✅ Classification columns exist")
        except Exception as e:
            logger.error(f"❌ Classification columns missing: {e}")
            
        # Test healthcare_sectors table
        try:
            result = db.execute(text("SELECT COUNT(*) FROM healthcare_sectors")).fetchone()
            logger.info(f"✅ healthcare_sectors table: {result[0]} rows")
        except Exception as e:
            logger.error(f"❌ healthcare_sectors table missing: {e}")
            
    except Exception as e:
        logger.error(f"❌ Database schema test failed: {e}")

def main():
    """Main test function"""
    print("🚀 Classification Debug Script")
    print("=" * 50)
    
    # Test database schema
    test_database_schema()
    print()
    
    # Run end-to-end test
    asyncio.run(test_end_to_end())
    
    print("\n" + "=" * 50)
    print("Debug script completed!")

if __name__ == "__main__":
    main()