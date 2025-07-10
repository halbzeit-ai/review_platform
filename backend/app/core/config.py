
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "HALBZEIT Review Platform"
    SECRET_KEY: str = "your-secret-key-here"  # Change in production
    API_V1_STR: str = "/api"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    DATABASE_URL: str = "sqlite:///./sql_app.db"  # Replace with PostgreSQL in production

    class Config:
        env_file = ".env"

settings = Settings()
