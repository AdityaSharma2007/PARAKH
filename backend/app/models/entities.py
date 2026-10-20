import enum
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, JSON, Enum
)
from sqlalchemy.orm import relationship
from backend.app.db.database import Base

class InterviewState(str, enum.Enum):
    CREATED = "CREATED"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    RECORDING = "RECORDING"
    PROCESSING = "PROCESSING"
    EVALUATED = "EVALUATED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class DifficultyLevel(str, enum.Enum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"

class VerificationStatus(str, enum.Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_DEMONSTRATED = "PARTIALLY_DEMONSTRATED"
    UNVERIFIED = "UNVERIFIED"
    CONTRADICTORY = "CONTRADICTORY"

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    resumes = relationship("Resume", back_populates="candidate", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=True)
    filename = Column(String(255), nullable=False)
    stored_path = Column(String(500), nullable=False)
    file_hash = Column(String(64), index=True, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="resumes")
    profile = relationship("CandidateProfile", back_populates="resume", uselist=False, cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="resume")

class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, unique=True)
    full_name = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    education = Column(JSON, default=list) # List of degrees, institutions, years
    skills = Column(JSON, default=dict) # Dict of categories: {languages: [], frameworks: [], tools: []}
    projects = Column(JSON, default=list) # List of {title, description, technologies, role}
    experience = Column(JSON, default=list) # List of {company, role, duration, highlights}
    certifications = Column(JSON, default=list)
    raw_text = Column(Text, nullable=True)
    skill_gap_analysis = Column(JSON, default=dict) # Detected strengths vs common role standards
    ats_score = Column(Float, default=0.0) # ATS compatibility score 0-100
    ats_breakdown = Column(JSON, default=dict) # Checklist & subscores
    contact_links = Column(JSON, default=dict) # GitHub, LinkedIn, Portfolio
    cv_improvement_tips = Column(JSON, default=list) # Concrete advice to enhance CV
    skill_depth_matrix = Column(JSON, default=dict) # Categorized depth map
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    resume = relationship("Resume", back_populates="profile")

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True)
    target_role = Column(String(100), nullable=False, default="Software Engineer")
    interview_type = Column(String(50), nullable=False, default="technical") # technical, project_based, behavioral, mixed
    initial_difficulty = Column(String(20), nullable=False, default=DifficultyLevel.INTERMEDIATE.value)
    current_difficulty = Column(String(20), nullable=False, default=DifficultyLevel.INTERMEDIATE.value)
    state = Column(String(30), nullable=False, default=InterviewState.CREATED.value)
    total_questions = Column(Integer, default=5)
    question_mix = Column(String(30), default="mixed") # mixed, spoken_only, coding_mcq
    current_question_index = Column(Integer, default=0)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    difficulty_history = Column(JSON, default=list) # [{index: 1, difficulty: "INTERMEDIATE", reason: "initial"}]
    created_at = Column(DateTime, default=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="interviews")
    resume = relationship("Resume", back_populates="interviews")
    questions = relationship("InterviewQuestion", back_populates="interview", order_by="InterviewQuestion.order_index", cascade="all, delete-orphan")
    report = relationship("AssessmentReport", back_populates="interview", uselist=False, cascade="all, delete-orphan")
    evidence_nodes = relationship("EvidenceNode", back_populates="interview", cascade="all, delete-orphan")
    consistency_checks = relationship("KnowledgeConsistencyCheck", back_populates="interview", cascade="all, delete-orphan")

class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    order_index = Column(Integer, nullable=False) # 1-based order
    question_text = Column(Text, nullable=False)
    skill_assessed = Column(String(100), nullable=False)
    category = Column(String(50), default="technical") # technical, project_deep_dive, system_design, behavioral
    difficulty = Column(String(20), nullable=False, default=DifficultyLevel.INTERMEDIATE.value)
    expected_concepts = Column(JSON, default=list) # List of key concept strings
    evaluation_rubric = Column(JSON, default=dict) # Rubric breakdown and expectations
    max_score = Column(Float, default=100.0)
    generation_source = Column(String(50), default="gemini") # gemini, fallback, dynamic_followup
    parent_question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=True)
    is_followup = Column(Boolean, default=False)
    question_type = Column(String(20), default="SPOKEN") # SPOKEN, MCQ, CODE
    options = Column(JSON, default=list) # [{"id": "A", "text": "..."}]
    correct_option = Column(String(10), nullable=True) # "A"
    code_snippet = Column(Text, nullable=True) # Starter/buggy code for challenges
    language = Column(String(30), default="python") # Language for code challenge
    explanation = Column(Text, nullable=True) # Concept rationale
    examples = Column(JSON, default=list) # [{"input": "...", "output": "...", "explanation": "..."}]
    test_cases = Column(JSON, default=list) # [{"name": "Case 1", "input": "...", "expected": "...", "test_code": "..."}]
    constraints = Column(JSON, default=list) # List of complexity & input constraints
    created_at = Column(DateTime, default=datetime.utcnow)

    interview = relationship("Interview", back_populates="questions")
    answer = relationship("Answer", back_populates="question", uselist=False, cascade="all, delete-orphan")

class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("interview_questions.id", ondelete="CASCADE"), nullable=False, unique=True)
    audio_path = Column(String(500), nullable=True)
    audio_duration_seconds = Column(Float, default=0.0)
    transcript = Column(Text, nullable=True)
    browser_transcript = Column(Text, nullable=True) # Real-time transcribed text from Web Speech API
    selected_option = Column(String(10), nullable=True) # Chosen option for MCQ
    code_submission = Column(Text, nullable=True) # Code challenge submission
    stt_confidence = Column(Float, default=1.0)
    is_audio_retained = Column(Boolean, default=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    retry_count = Column(Integer, default=0)

    question = relationship("InterviewQuestion", back_populates="answer")
    evaluation = relationship("Evaluation", back_populates="answer", uselist=False, cascade="all, delete-orphan")

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("answers.id", ondelete="CASCADE"), nullable=False, unique=True)
    overall_score = Column(Float, nullable=False) # 0 to 100
    technical_score = Column(Float, nullable=False)
    conceptual_score = Column(Float, nullable=False)
    relevance_score = Column(Float, nullable=False)
    clarity_score = Column(Float, nullable=False)
    correct_concepts = Column(JSON, default=list)
    missing_concepts = Column(JSON, default=list)
    incorrect_statements = Column(JSON, default=list)
    transcript_evidence = Column(JSON, default=list) # Exact quote snippets from candidate transcript
    feedback = Column(Text, nullable=False)
    improvement_tips = Column(JSON, default=list)
    confidence = Column(Float, default=0.9)
    reliability_tier = Column(String(20), default="HIGH") # HIGH, MEDIUM, LOW (audio degradation)
    provider_mode = Column(String(50), default="gemini") # gemini or mock
    why_this_score = Column(Text, nullable=True) # Explainable scoring justification
    created_at = Column(DateTime, default=datetime.utcnow)

    answer = relationship("Answer", back_populates="evaluation")

    @property
    def question_id(self) -> int | None:
        return self.answer.question_id if self.answer else None

class EvidenceNode(Base):
    __tablename__ = "evidence_nodes"

    id = Column(Integer, primary_key=True, index=True)
    candidate_id = Column(Integer, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=True)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    claim_type = Column(String(50), nullable=False) # "skill" or "project_claim"
    claim_text = Column(String(255), nullable=False) # e.g. "FastAPI", "PostgreSQL query optimization"
    verified_status = Column(String(30), default=VerificationStatus.UNVERIFIED.value)
    confidence_score = Column(Float, default=0.0)
    evidence_quote = Column(Text, nullable=True)
    related_question_id = Column(Integer, ForeignKey("interview_questions.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    interview = relationship("Interview", back_populates="evidence_nodes")

class KnowledgeConsistencyCheck(Base):
    __tablename__ = "knowledge_consistency_checks"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    concept_area = Column(String(100), nullable=False) # e.g. "Relational Databases / SQL"
    questions_compared = Column(JSON, default=list) # [question_id_1, question_id_2]
    consistency_score = Column(Float, default=1.0) # 0 to 1
    discrepancy_details = Column(Text, nullable=True)
    root_cause = Column(String(255), nullable=True) # e.g. "Strong syntax recall but conceptual query planner misunderstanding"
    created_at = Column(DateTime, default=datetime.utcnow)

    interview = relationship("Interview", back_populates="consistency_checks")

class AssessmentReport(Base):
    __tablename__ = "assessment_reports"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, unique=True)
    overall_score = Column(Float, nullable=False)
    technical_score = Column(Float, nullable=False)
    conceptual_score = Column(Float, nullable=False)
    relevance_score = Column(Float, nullable=False)
    clarity_score = Column(Float, nullable=False)
    competency_scores = Column(JSON, default=dict) # {Python: 85, SQL: 60, Architecture: 78}
    strengths = Column(JSON, default=list)
    areas_for_improvement = Column(JSON, default=list)
    recommendations = Column(JSON, default=list)
    knowledge_gap_map = Column(JSON, default=dict) # Hierarchical {foundational: [], intermediate: [], advanced: []}
    completion_stats = Column(JSON, default=dict)
    vision_analytics = Column(JSON, default=dict) # Computer Vision (CV) behavioral metrics
    audio_analytics = Column(JSON, default=dict) # Raw Audio Waveform acoustic telemetry
    generated_at = Column(DateTime, default=datetime.utcnow)

    interview = relationship("Interview", back_populates="report")
