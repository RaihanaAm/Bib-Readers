<<<<<<< HEAD
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str

    # pydantic v2: charge .env de façon fiable
    model_config = SettingsConfigDict(
        
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
=======
# backend/app/core/config.py
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str

    # --- JWT/Auth ---
    JWT_SECRET: str = "change-me"         # override in .env
    JWT_ALGO: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    class Config:
        env_file = ".env"

>>>>>>> main

settings = Settings()
