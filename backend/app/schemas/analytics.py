from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SessionTrendPoint(BaseModel):
    interview_id: int
    date: str
    target_role: str
    overall_score: float
    technical_score: float
    conceptual_score: float
    relevance_score: float
    clarity_score: float

class SkillDelta(BaseModel):
    skill: str
    first_score: float
    latest_score: float
    delta: float # e.g. +22.0
    status: str # "IMPROVED", "STABLE", "NEEDS_WORK"

class CandidateImprovementAnalytics(BaseModel):
    total_interviews: int
    average_score: float
    highest_score: float
    score_history: List[SessionTrendPoint] = Field(default_factory=list)
    skill_deltas: List[SkillDelta] = Field(default_factory=list)
    reinforced_concepts: List[str] = Field(default_factory=list)
    persistent_gaps: List[str] = Field(default_factory=list)
