"""
Configuration de l'application via pydantic-settings.

- Chargement de variables d'environnement depuis `.env`
- Paramètres de connexion à la base de données
- Paramètres JWT pour l'authentification
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Database ---
    DATABASE_URL: str

    # --- JWT/Auth ---
    JWT_SECRET: str = "change-me"  # À surcharger dans .env
    JWT_ALGO: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # pydantic v2: charge .env de façon fiable
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
