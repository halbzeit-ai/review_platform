
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "HALBZEIT Review Platform"
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    API_V1_STR: str = "/api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    DATABASE_URL: str = "postgresql://review_user:review_password@localhost:5432/review-platform"

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

    class Config:
        env_file = ".env"

settings = Settings()
