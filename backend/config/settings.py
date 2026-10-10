"""Paths and browser-origin settings for the local CIVIS API."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    UPLOADS_DIR: Path = BASE_DIR / "uploads"
    OUTPUTS_DIR: Path = BASE_DIR / "outputs"
    MODELS_DIR: Path = BASE_DIR.parent / "models"
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)


settings = Settings()
settings.UPLOADS_DIR.mkdir(exist_ok=True)
settings.OUTPUTS_DIR.mkdir(exist_ok=True)
settings.MODELS_DIR.mkdir(exist_ok=True, parents=True)
