#!/usr/bin/env python3
"""
Script to check database configuration on production server
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings

def check_database_config():
    print("=== Database Configuration Check ===")
    print(f"DATABASE_URL from settings: {settings.DATABASE_URL}")
    print(f"DATABASE_URL from env: {os.environ.get('DATABASE_URL', 'NOT SET')}")
    
    # Check if .env file exists
    env_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
    print(f".env file path: {env_file_path}")
    print(f".env file exists: {os.path.exists(env_file_path)}")
    
    if os.path.exists(env_file_path):
        print("\n=== .env file contents ===")
        with open(env_file_path, 'r') as f:
            for line_num, line in enumerate(f, 1):
                if 'DATABASE_URL' in line:
                    print(f"Line {line_num}: {line.strip()}")
    else:
        print("No .env file found")
    
    # Check all environment variables related to database
    print("\n=== Environment Variables ===")
    for key, value in os.environ.items():
        if 'DATABASE' in key.upper() or 'DB' in key.upper():
            print(f"{key}: {value}")
    
    print("\n=== Current Working Directory ===")
    print(f"CWD: {os.getcwd()}")

if __name__ == "__main__":
    check_database_config()