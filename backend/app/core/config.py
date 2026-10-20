import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "PARAKH"
    APP_ENV: str = "development"
    DEBUG: bool = True
    
    # Storage & Uploads
    BASE_DIR: Path = BASE_DIR
    UPLOAD_DIR: Path = BASE_DIR / "uploads"
    AUDIO_DIR: Path = BASE_DIR / "uploads" / "audio"
    RESUME_DIR: Path = BASE_DIR / "uploads" / "resumes"
    MAX_UPLOAD_SIZE_MB: int = 15
    AUDIO_RETENTION_ENABLED: bool = False
    
    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'parakh.db'}"
    
    # AI / LLM Configuration
    # Free tier options: "gemini" (recommended) or "mock"
    LLM_PROVIDER: str = "gemini"
    GEMINI_API_KEY: str = Field(default="", env="GEMINI_API_KEY")
    GEMINI_MODEL: str = "gemini-flash-lite-latest"
    LLM_TIMEOUT_SECONDS: int = 40
    MOCK_MODE: bool = False
    
    # Speech-to-Text Configuration
    # STT options: "faster-whisper" or "mock"
    STT_PROVIDER: str = "faster-whisper"
    WHISPER_MODEL_SIZE: str = "tiny"
    
    # Scoring & Adaptive Engine Parameters
    DIFFICULTY_SATISFACTORY_THRESHOLD: float = 70.0
    DIFFICULTY_UNSATISFACTORY_THRESHOLD: float = 50.0
    CONFIDENCE_MIN_RELIABLE_THRESHOLD: float = 0.65
    
    # Camera Analysis (Privacy guarded: default false)
    ENABLE_VISION: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

settings = Settings()

# Ensure required runtime directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.AUDIO_DIR.mkdir(parents=True, exist_ok=True)
settings.RESUME_DIR.mkdir(parents=True, exist_ok=True)
