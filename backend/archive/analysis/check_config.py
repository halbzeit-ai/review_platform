#!/usr/bin/env python3
"""
Simple Configuration Checker
Quick script to check key configuration values
"""

import os
import sys
from pathlib import Path

# Add the app directory to path
sys.path.append(str(Path(__file__).parent))

def check_config():
    """Check configuration values"""
    print("🔧 Configuration Checker")
    print("=" * 40)
    
    try:
        from app.core.config import settings
        print(f"GPU_INSTANCE_HOST: {settings.GPU_INSTANCE_HOST}")
        print(f"GPU Host configured: {'✅ Yes' if settings.GPU_INSTANCE_HOST else '❌ No'}")
    except Exception as e:
        print(f"❌ Config error: {e}")
        
    # Check environment variables
    print("\n📋 Environment Variables:")
    gpu_host = os.getenv('GPU_INSTANCE_HOST')
    print(f"GPU_INSTANCE_HOST env: {gpu_host or '❌ Not set'}")
    
    # Check if we can import key modules
    print("\n📦 Module Availability:")
    
    try:
        import ollama
        print("✅ ollama module available (GPU server)")
    except ImportError:
        print("❌ ollama module not available (CPU server)")
        
    try:
        from app.services.gpu_http_client import gpu_http_client
        print("✅ GPU HTTP client available")
    except ImportError as e:
        print(f"❌ GPU HTTP client error: {e}")
        
    try:
        from app.services.startup_classifier import StartupClassifier
        print("✅ StartupClassifier available")
    except ImportError as e:
        print(f"❌ StartupClassifier error: {e}")

if __name__ == "__main__":
    check_config()