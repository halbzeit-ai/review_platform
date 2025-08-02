import os
import sys
sys.path.insert(0, '/opt/review-platform/backend')

print("=== OS Environment ===")
for key in sorted(os.environ.keys()):
    if 'SHARED' in key or 'MOUNT' in key or 'PATH' in key:
        print(f"{key}: {os.environ[key]}")

print("\n=== Settings Object ===")
from app.core.config import settings
print(f"SHARED_FILESYSTEM_MOUNT_PATH: {settings.SHARED_FILESYSTEM_MOUNT_PATH}")
print(f"Type: {type(settings)}")
print(f"Module: {settings.__module__}")

print("\n=== Working Directory ===")
print(f"CWD: {os.getcwd()}")
