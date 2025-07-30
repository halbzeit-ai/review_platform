#!/usr/bin/env python3
"""
Diagnose GPU processing issues
"""

import os
import sys
import subprocess
import requests
from pathlib import Path

print("🔍 GPU Processing Diagnostic")
print("="*40)

# Check environment variables
print("\n📋 Environment Variables:")
env_vars = ["BACKEND_DEVELOPMENT", "BACKEND_PRODUCTION", "SHARED_FILESYSTEM_MOUNT_PATH"]
for var in env_vars:
    value = os.getenv(var, "NOT SET")
    print(f"  {var}: {value}")

# Check poppler installation
print("\n📦 Poppler Installation:")
try:
    result = subprocess.run(["pdftoppm", "-h"], capture_output=True, text=True)
    print("  ✅ pdftoppm command available")
except FileNotFoundError:
    print("  ❌ pdftoppm command not found - install poppler-utils")

try:
    result = subprocess.run(["pdfinfo", "-h"], capture_output=True, text=True)
    print("  ✅ pdfinfo command available")
except FileNotFoundError:
    print("  ❌ pdfinfo command not found - install poppler-utils")

# Check Python packages
print("\n📦 Python Packages:")
packages = ["pdf2image", "ollama", "psycopg2", "flask"]
for package in packages:
    try:
        __import__(package)
        print(f"  ✅ {package} installed")
    except ImportError:
        print(f"  ❌ {package} not installed")

# Test pdf2image specifically
print("\n📄 PDF2Image Test:")
try:
    from pdf2image import convert_from_path
    print("  ✅ pdf2image imported successfully")
    
    # Try with a simple test (if poppler is working)
    try:
        # This will fail gracefully if poppler isn't working
        convert_from_path("/nonexistent.pdf")
    except Exception as e:
        if "poppler" in str(e).lower():
            print(f"  ❌ Poppler issue: {e}")
        else:
            print("  ✅ pdf2image can access poppler (file not found is expected)")
except ImportError as e:
    print(f"  ❌ pdf2image import failed: {e}")

# Check backend connectivity
print("\n🌐 Backend Connectivity:")
backend_url = os.getenv("BACKEND_DEVELOPMENT", "http://65.108.32.143:8000")
try:
    response = requests.get(f"{backend_url}/api/health", timeout=5)
    print(f"  ✅ Backend reachable at {backend_url}")
    print(f"  Status: {response.status_code}")
except Exception as e:
    print(f"  ❌ Backend not reachable: {e}")

# Check shared filesystem
print("\n📂 Shared Filesystem:")
shared_dir = os.getenv("SHARED_FILESYSTEM_MOUNT_PATH", "/mnt/dev-shared")
if Path(shared_dir).exists():
    print(f"  ✅ Shared directory exists: {shared_dir}")
    uploads_dir = Path(shared_dir) / "uploads"
    results_dir = Path(shared_dir) / "results"
    print(f"  Uploads dir: {'✅' if uploads_dir.exists() else '❌'} {uploads_dir}")
    print(f"  Results dir: {'✅' if results_dir.exists() else '❌'} {results_dir}")
else:
    print(f"  ❌ Shared directory not found: {shared_dir}")

print("\n" + "="*40)
print("Run this script to diagnose issues before starting GPU processing")