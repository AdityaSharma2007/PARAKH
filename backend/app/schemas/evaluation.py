from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class SingleEvaluationResponse(BaseModel):
    id: int
    question_id: Optional[int] = None
    overall_score: float
    technical_score: float
    conceptual_score: float
    relevance_score: float
    clarity_score: float
    correct_concepts: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    incorrect_statements: List[str] = Field(default_factory=list)
    transcript_evidence: List[str] = Field(default_factory=list)
    feedback: str
    improvement_tips: List[str] = Field(default_factory=list)
    confidence: float
    reliability_tier: str
    why_this_score: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class EvidenceNodeResponse(BaseModel):
    id: int
    claim_type: str
    claim_text: str
    verified_status: str
    confidence_score: float
    evidence_quote: Optional[str] = None
    related_question_id: Optional[int] = None

    class Config:
        from_attributes = True

class AssessmentReportResponse(BaseModel):
    id: int
    interview_id: int
    overall_score: float
    technical_score: float
    conceptual_score: float
    relevance_score: float
    clarity_score: float
    competency_scores: Dict[str, float] = Field(default_factory=dict)
    strengths: List[str] = Field(default_factory=list)
    areas_for_improvement: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    knowledge_gap_map: Dict[str, Any] = Field(default_factory=dict)
    completion_stats: Dict[str, Any] = Field(default_factory=dict)
    vision_analytics: Dict[str, Any] = Field(default_factory=dict)
    audio_analytics: Dict[str, Any] = Field(default_factory=dict)
    evaluations: List[SingleEvaluationResponse] = Field(default_factory=list)
    evidence_nodes: List[EvidenceNodeResponse] = Field(default_factory=list)
    generated_at: datetime

    class Config:
        from_attributes = True
