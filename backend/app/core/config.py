from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import ConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    ALGORITHM : str
    ACCESS_TOKEN_EXPIRE_MINUTES : int
    SECRET_KEY: str
    REDIS_URL: str
    GOOGLE_CLIENT_ID: str
    GOOGLE_CLIENT_SECRET: str
    BREVO_API_KEY: str
    FROM_EMAIL: str
    FROM_NAME: str = "Task Manager"
    BASE_URL: str = "http://localhost:8000"  # Base URL for download links
    FRONTEND_URL: str = "http://localhost:3000"  # Frontend URL for OAuth2 redirect
    LOG_LEVEL: str = "INFO"
    

    model_config = ConfigDict(env_file=".env", extra="ignore")


settings = Settings()