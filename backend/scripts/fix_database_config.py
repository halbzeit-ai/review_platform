#!/usr/bin/env python3
"""
Script to fix database configuration on production server
Creates/updates .env file with PostgreSQL configuration
"""

import os

def fix_database_config():
    # Get the backend directory
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_file_path = os.path.join(backend_dir, '.env')
    
    print(f"=== Fixing Database Configuration ===")
    print(f"Backend directory: {backend_dir}")
    print(f".env file path: {env_file_path}")
    
    # PostgreSQL configuration
    postgres_config = """# Database Configuration
DATABASE_URL=postgresql://review_user:review_password@localhost:5432/review-platform

# Email Configuration
SMTP_SERVER=mail.halbzeit.ai
SMTP_PORT=587
SMTP_USERNAME=registration@halbzeit.ai
SMTP_PASSWORD=your_smtp_password_here
FROM_EMAIL=registration@halbzeit.ai
FROM_NAME=HALBZEIT AI Review Platform
FRONTEND_URL=http://65.108.32.168

# Security
SECRET_KEY=your-production-secret-key-here
"""
    
    # Check if .env file exists
    if os.path.exists(env_file_path):
        print("✓ .env file exists, backing up...")
        backup_path = env_file_path + '.backup'
        with open(env_file_path, 'r') as f:
            backup_content = f.read()
        with open(backup_path, 'w') as f:
            f.write(backup_content)
        print(f"✓ Backup created at: {backup_path}")
    
    # Write new .env file
    with open(env_file_path, 'w') as f:
        f.write(postgres_config)
    
    print(f"✓ .env file updated with PostgreSQL configuration")
    print(f"✓ Database URL: postgresql://review_user:review_password@localhost:5432/review-platform")
    
    # Check if PostgreSQL is running
    import subprocess
    try:
        result = subprocess.run(['systemctl', 'is-active', 'postgresql'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✓ PostgreSQL service is running")
        else:
            print("✗ PostgreSQL service is not running")
            print("Run: sudo systemctl start postgresql")
    except Exception as e:
        print(f"Could not check PostgreSQL status: {e}")
    
    print("\n=== Next Steps ===")
    print("1. Restart the FastAPI application")
    print("2. Run database migrations if needed")
    print("3. Test the connection with: python scripts/check_user_status.py")

if __name__ == "__main__":
    fix_database_config()