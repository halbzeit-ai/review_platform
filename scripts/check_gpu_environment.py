#!/usr/bin/env python3
"""
Check GPU environment variables and fix port issue
"""

import os

print("🔍 GPU Environment Variables Check")
print("="*40)

# Check environment variables
env_vars = {
    "PRODUCTION_SERVER_URL": os.getenv("PRODUCTION_SERVER_URL"),
    "BACKEND_URL": os.getenv("BACKEND_URL"),
    "DATABASE_URL": os.getenv("DATABASE_URL"),
    "SHARED_FILESYSTEM_MOUNT_PATH": os.getenv("SHARED_FILESYSTEM_MOUNT_PATH")
}

for var, value in env_vars.items():
    if value:
        print(f"✅ {var}: {value}")
    else:
        print(f"❌ {var}: NOT SET")

# Check if PRODUCTION_SERVER_URL includes port
prod_url = env_vars["PRODUCTION_SERVER_URL"]
if prod_url:
    if ":8000" in prod_url:
        print("✅ PRODUCTION_SERVER_URL includes port 8000")
    elif ":80" in prod_url:
        print("⚠️  PRODUCTION_SERVER_URL has port 80 (should be 8000)")
    elif prod_url.count(":") == 1:  # Only http: or https:
        print("❌ PRODUCTION_SERVER_URL missing port number")
        print("   This will default to port 80!")
    else:
        print("✅ PRODUCTION_SERVER_URL appears to have a port")

print("\n" + "="*40)
print("🔧 To fix the port 80 issue:")
print("export PRODUCTION_SERVER_URL=http://65.108.32.143:8000")