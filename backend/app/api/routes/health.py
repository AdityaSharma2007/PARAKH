from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.db.database import get_db
from backend.app.core.config import settings
from backend.app.integrations import get_llm_provider

router = APIRouter(prefix="/health", tags=["Health & Diagnostics"])

@router.get("")
def health_liveness():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "environment": settings.APP_ENV
    }

@router.get("/ready")
def health_readiness(db: Session = Depends(get_db)):
    # 1. Database check
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    # 2. LLM check
    llm = get_llm_provider()
    gemini_configured = bool(settings.GEMINI_API_KEY)
    
    return {
        "status": "ready" if db_ok else "degraded",
        "database_connected": db_ok,
        "llm_provider": settings.LLM_PROVIDER,
        "gemini_configured": gemini_configured,
        "mock_mode": not gemini_configured or settings.MOCK_MODE,
        "stt_provider": settings.STT_PROVIDER,
        "whisper_model": settings.WHISPER_MODEL_SIZE
    }
