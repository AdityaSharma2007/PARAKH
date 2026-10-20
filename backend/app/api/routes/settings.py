from fastapi import APIRouter
from backend.app.core.config import settings

router = APIRouter(prefix="/settings", tags=["Application Settings"])

@router.get("/public")
def get_public_settings():
    return {
        "app_name": settings.APP_NAME,
        "max_upload_size_mb": settings.MAX_UPLOAD_SIZE_MB,
        "llm_provider": settings.LLM_PROVIDER,
        "gemini_model": settings.GEMINI_MODEL,
        "gemini_configured": bool(settings.GEMINI_API_KEY),
        "mock_mode": not bool(settings.GEMINI_API_KEY) or settings.MOCK_MODE,
        "stt_provider": settings.STT_PROVIDER,
        "audio_retention_enabled": settings.AUDIO_RETENTION_ENABLED,
        "difficulty_satisfactory_threshold": settings.DIFFICULTY_SATISFACTORY_THRESHOLD,
        "difficulty_unsatisfactory_threshold": settings.DIFFICULTY_UNSATISFACTORY_THRESHOLD,
        "enable_vision": settings.ENABLE_VISION
    }
