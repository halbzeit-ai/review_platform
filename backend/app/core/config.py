
import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "HALBZEIT Review Platform"
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    API_V1_STR: str = "/api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    DATABASE_URL: str = "postgresql://review_user:review_password@localhost:5432/review-platform"

    # Environment detection
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # Server Configuration
    FRONTEND_PORT: int = 3000
    BACKEND_PORT: int = 8000

    # Datacrunch.io API Configuration
    DATACRUNCH_CLIENT_ID: str = ""
    DATACRUNCH_CLIENT_SECRET: str = ""
    DATACRUNCH_API_BASE: str = "https://api.datacrunch.io/v1"
    DATACRUNCH_SHARED_FILESYSTEM_ID: Optional[str] = "ef23bde1-085b-4482-8d73-3fd9950af3e4"
    DATACRUNCH_SSH_KEY_IDS: str = ""  # Comma-separated SSH key IDs for GPU instances
    SHARED_FILESYSTEM_MOUNT_PATH: str = "/mnt/CPU-GPU"
    
    # Direct GPU Processing Configuration
    GPU_INSTANCE_HOST: str = ""  # IP address of your persistent GPU instance
    GPU_INSTANCE_USER: str = "root"
    GPU_INSTANCE_SSH_KEY_PATH: str = ""  # Path to SSH private key for GPU instance

    # Email Configuration (Hetzner)
    SMTP_SERVER: str = "mail.halbzeit.ai"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "registration@halbzeit.ai"
    SMTP_PASSWORD: str = ""
    FROM_EMAIL: str = "registration@halbzeit.ai"
    FROM_NAME: str = "HALBZEIT AI Review Platform"
    FRONTEND_URL: str = "http://localhost:3000"  # Update for production

    # File Upload Settings
    MAX_UPLOAD_SIZE: int = 1073741824  # 1GB
    UPLOAD_PATH: str = "/tmp/uploads"

    # Cache Settings
    REDIS_URL: Optional[str] = None
    CACHE_TTL: int = 3600

    # CORS Settings
    ENABLE_CORS: bool = True

    # Production-specific settings
    ALLOWED_HOSTS: str = "*"
    SSL_REQUIRED: bool = False
    SECURE_COOKIES: bool = False

    # Monitoring
    ENABLE_MONITORING: bool = False
    SENTRY_DSN: Optional[str] = None
    LOG_FILE: Optional[str] = None

    # Performance settings
    WORKERS: int = 1
    WORKER_TIMEOUT: int = 300
    MAX_REQUESTS: int = 1000
    MAX_REQUESTS_JITTER: int = 100

    class Config:
        env_file = ".env"

def get_environment() -> str:
    """Detect current environment from ENV variable or default to development"""
    return os.getenv("ENVIRONMENT", "development")

def load_environment_config() -> Settings:
    """Load configuration based on current environment"""
    environment = get_environment()
    
    # Determine environment file path
    env_file_map = {
        "development": "environments/development.env",
        "staging": "environments/staging.env", 
        "production": "environments/production.env"
    }
    
    env_file = env_file_map.get(environment, ".env")
    
    # Check if environment file exists
    if os.path.exists(env_file):
        # Load environment-specific settings
        class EnvironmentSettings(Settings):
            class Config:
                env_file = env_file
        
        return EnvironmentSettings()
    else:
        # Fall back to default settings with .env
        return Settings()

# Create settings instance with environment detection
settings = load_environment_config()
