import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "FMCG Beverages Business Intelligence Assistant"
    DATABASE_URL: str = "sqlite:///./fmcg_beverages.db"
    
    # API Keys for AI model endpoints
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    
    # App Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    
    # Model configuration: allow loading from .env
    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
