#!/usr/bin/env python3
"""
Check GPU environment variables and fix port issue
"""

import os

print("🔍 GPU Environment Variables Check")
print("="*40)

# Check environment variables
env_vars = {
    "BACKEND_DEVELOPMENT": os.getenv("BACKEND_DEVELOPMENT"),
    "BACKEND_PRODUCTION": os.getenv("BACKEND_PRODUCTION"),
    "DATABASE_URL": os.getenv("DATABASE_URL"),
    "SHARED_FILESYSTEM_MOUNT_PATH": os.getenv("SHARED_FILESYSTEM_MOUNT_PATH")
}

for var, value in env_vars.items():
    if value:
        print(f"✅ {var}: {value}")
    else:
        print(f"❌ {var}: NOT SET")

# Check if backend URLs include proper ports
for env_name in ["BACKEND_DEVELOPMENT", "BACKEND_PRODUCTION"]:
    backend_url = env_vars[env_name]
    if backend_url:
        if ":8000" in backend_url:
            print(f"✅ {env_name} includes port 8000")
        elif ":80" in backend_url:
            print(f"⚠️  {env_name} has port 80 (should be 8000)")
        elif backend_url.count(":") == 1:  # Only http: or https:
            print(f"❌ {env_name} missing port number")
            print("   This will default to port 80!")
        else:
            print(f"✅ {env_name} appears to have a port")

print("\n" + "="*40)
print("🔧 To set proper backend URLs:")
print("export BACKEND_DEVELOPMENT=http://65.108.32.143:8000")
print("export BACKEND_PRODUCTION=http://65.108.32.168:8000")