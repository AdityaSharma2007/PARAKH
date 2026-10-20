from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.schemas.analytics import CandidateImprovementAnalytics
from backend.app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Candidate Analytics & Improvement"])

@router.get("/progress", response_model=CandidateImprovementAnalytics)
def get_progress_analytics(
    candidate_id: int | None = Query(None, description="Optional candidate filter"),
    db: Session = Depends(get_db)
):
    """
    Computes cross-session metrics: score trajectory over time, skill mastery deltas,
    and reinforced technical concepts across multiple interviews.
    """
    return AnalyticsService.get_candidate_progress(db, candidate_id)
