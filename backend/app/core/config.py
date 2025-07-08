
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "Startup Review Platform"
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    API_V1_STR: str = "/api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    DATABASE_URL: str = "sqlite:///./sql_app.db"  # Replace with PostgreSQL in production
    S3_BUCKET_NAME: Optional[str] = None
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: Optional[int] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    DO_SPACES_KEY: str = ""
    DO_SPACES_SECRET: str = ""
    DO_SPACES_ENDPOINT: str = ""
    DO_SPACES_REGION: str = ""
    DO_SPACES_BUCKET: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
