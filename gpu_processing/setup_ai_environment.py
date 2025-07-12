#!/usr/bin/env python3
"""
AI Environment Setup Script
Ensures Ollama is running and required models are available
"""

import subprocess
import time
import logging
import sys
import os

logger = logging.getLogger(__name__)

def run_command(command, description=""):
    """Run a shell command with error handling"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            logger.info(f"✓ {description}: Success")
            return True
        else:
            logger.error(f"✗ {description}: Failed - {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"✗ {description}: Exception - {e}")
        return False

def check_ollama_service():
    """Check if Ollama service is running"""
    logger.info("Checking Ollama service status...")
    
    # Check if ollama command exists
    if not run_command("which ollama", "Ollama installation check"):
        logger.error("Ollama is not installed. Please run the install script first.")
        return False
    
    # Check if service is running
    if run_command("systemctl is-active ollama", "Ollama service status"):
        logger.info("Ollama service is already running")
        return True
    
    # Try to start the service
    logger.info("Starting Ollama service...")
    if run_command("sudo systemctl start ollama", "Starting Ollama service"):
        time.sleep(5)  # Wait for service to fully start
        return True
    
    return False

def check_required_models():
    """Check if required AI models are available"""
    required_models = [
        "gemma3:12b",
        "phi4:latest"
    ]
    
    logger.info("Checking required AI models...")
    
    # Get list of available models
    result = subprocess.run("ollama list", shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Failed to list Ollama models")
        return False
    
    available_models = result.stdout.lower()
    missing_models = []
    
    for model in required_models:
        if model.lower() not in available_models:
            missing_models.append(model)
        else:
            logger.info(f"✓ Model {model} is available")
    
    if missing_models:
        logger.info(f"Missing models: {missing_models}")
        return pull_missing_models(missing_models)
    
    return True

def pull_missing_models(models):
    """Pull missing AI models"""
    logger.info("Pulling missing AI models...")
    
    for model in models:
        logger.info(f"Pulling model: {model}")
        if not run_command(f"ollama pull {model}", f"Pulling {model}"):
            logger.error(f"Failed to pull model: {model}")
            return False
        logger.info(f"✓ Model {model} pulled successfully")
    
    return True

def check_system_dependencies():
    """Check required system dependencies"""
    dependencies = [
        ("python3", "Python 3"),
        ("pip", "pip package manager"),
        ("poppler-utils", "Poppler PDF utilities")
    ]
    
    logger.info("Checking system dependencies...")
    
    all_available = True
    for command, description in dependencies:
        if run_command(f"which {command}", f"{description} availability"):
            continue
        else:
            # Try alternative checks
            if command == "poppler-utils":
                if not run_command("which pdftoppm", "Poppler pdftoppm utility"):
                    logger.error(f"Missing dependency: {description}")
                    all_available = False
            else:
                logger.error(f"Missing dependency: {description}")
                all_available = False
    
    return all_available

def main():
    """Main setup function"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger.info("=== AI Environment Setup ===")
    
    # Check system dependencies
    if not check_system_dependencies():
        logger.error("System dependencies missing. Please install required packages.")
        sys.exit(1)
    
    # Check and start Ollama service
    if not check_ollama_service():
        logger.error("Failed to ensure Ollama service is running")
        sys.exit(1)
    
    # Check and pull required models
    if not check_required_models():
        logger.error("Failed to ensure required AI models are available")
        sys.exit(1)
    
    logger.info("=== AI Environment Setup Complete ===")
    logger.info("All dependencies and models are ready for AI processing")

if __name__ == "__main__":
    main()