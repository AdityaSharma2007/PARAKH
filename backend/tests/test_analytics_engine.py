import pytest
from datetime import datetime, timedelta
from backend.app.models.entities import Interview, AssessmentReport
from backend.app.services.analytics_service import AnalyticsService

def test_analytics_progression_and_deltas(db_session):
    # Create session 1
    it1 = Interview(target_role="Full Stack", created_at=datetime.utcnow() - timedelta(days=2))
    db_session.add(it1)
    db_session.commit()

    rep1 = AssessmentReport(
        interview_id=it1.id,
        overall_score=60.0,
        technical_score=58.0,
        conceptual_score=60.0,
        relevance_score=65.0,
        clarity_score=60.0,
        competency_scores={"Python": 55.0, "SQL": 65.0}
    )
    db_session.add(rep1)

    # Create session 2 (improved)
    it2 = Interview(target_role="Full Stack", created_at=datetime.utcnow())
    db_session.add(it2)
    db_session.commit()

    rep2 = AssessmentReport(
        interview_id=it2.id,
        overall_score=82.0,
        technical_score=85.0,
        conceptual_score=80.0,
        relevance_score=82.0,
        clarity_score=80.0,
        competency_scores={"Python": 80.0, "SQL": 84.0}
    )
    db_session.add(rep2)
    db_session.commit()

    # Calculate analytics
    analytics = AnalyticsService.get_candidate_progress(db_session)
    assert analytics["total_interviews"] == 2
    assert analytics["average_score"] == 71.0
    assert analytics["highest_score"] == 82.0

    # Verify skill deltas
    python_delta = next(d for d in analytics["skill_deltas"] if d["skill"] == "Python")
    assert python_delta["first_score"] == 55.0
    assert python_delta["latest_score"] == 80.0
    assert python_delta["delta"] == 25.0
    assert python_delta["status"] == "IMPROVED"

    # Verify Python was identified as reinforced
    assert "Python" in analytics["reinforced_concepts"]
