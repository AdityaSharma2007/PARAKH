from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class InterviewCreateRequest(BaseModel):
    resume_id: int
    target_role: str = Field(default="Full Stack Engineer", description="Target job title")
    interview_type: str = Field(default="mixed", description="technical, project_based, behavioral, mixed")
    initial_difficulty: str = Field(default="INTERMEDIATE", description="BEGINNER, INTERMEDIATE, ADVANCED")
    total_questions: int = Field(default=5, ge=1, le=15, description="Total number of questions")
    question_mix: str = Field(default="mixed", description="mixed, spoken_only, coding_mcq")

class InterviewQuestionResponse(BaseModel):
    id: int
    order_index: int
    question_text: str
    skill_assessed: str
    category: str
    difficulty: str
    question_type: str = "SPOKEN"
    options: List[Dict[str, Any]] = Field(default_factory=list)
    correct_option: Optional[str] = None
    code_snippet: Optional[str] = None
    language: Optional[str] = "python"
    explanation: Optional[str] = None
    examples: List[Dict[str, Any]] = Field(default_factory=list)
    test_cases: List[Dict[str, Any]] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    expected_concepts: List[str] = Field(default_factory=list)
    max_score: float = 100.0
    is_followup: bool = False
    parent_question_id: Optional[int] = None

    class Config:
        from_attributes = True

class CodeRunRequest(BaseModel):
    code: str
    language: Optional[str] = "python"

class CodeRunResponse(BaseModel):
    all_passed: bool
    total_cases: int
    passed_cases: int
    runtime_ms: float
    stdout: str = ""
    error: Optional[str] = None
    results: List[Dict[str, Any]] = Field(default_factory=list)

class AnswerSubmitResponse(BaseModel):
    answer_id: int
    question_id: int
    transcript: str
    stt_confidence: float
    overall_score: float
    feedback: str
    current_difficulty: str
    next_question_available: bool
    is_interview_completed: bool
    selected_option: Optional[str] = None
    correct_option: Optional[str] = None
    is_correct: Optional[bool] = None
    explanation: Optional[str] = None
    code_feedback: Optional[str] = None

class InterviewResponse(BaseModel):
    id: int
    candidate_id: Optional[int] = None
    resume_id: Optional[int] = None
    target_role: str
    interview_type: str
    initial_difficulty: str
    current_difficulty: str
    state: str
    total_questions: int
    current_question_index: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    questions: List[InterviewQuestionResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True
