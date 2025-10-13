from pydantic_settings import BaseSettings
from typing import Optional
from pydantic import ConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    ALGORITHM : str
    ACCESS_TOKEN_EXPIRE_MINUTES : int
    SECRET_KEY: str
    REDIS_URL: str
    GOOGLE_CLIENT_ID: Optional[str] = None

    model_config = ConfigDict(env_file=".env", extra="ignore")


settings = Settings()