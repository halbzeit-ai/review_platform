
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "HALBZEIT Review Platform"
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    API_V1_STR: str = "/api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    DATABASE_URL: str = "sqlite:///./sql_app.db"  # Replace with PostgreSQL in production

    # Datacrunch.io API Configuration
    DATACRUNCH_CLIENT_ID: str = ""
    DATACRUNCH_CLIENT_SECRET: str = ""
    DATACRUNCH_API_BASE: str = "https://api.datacrunch.io/v1"
    DATACRUNCH_SHARED_FILESYSTEM_ID: Optional[str] = None
    SHARED_FILESYSTEM_MOUNT_PATH: str = "/mnt/shared"

    class Config:
        env_file = ".env"

settings = Settings()
