from pathlib import Path
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.core.exceptions import EntityNotFoundError, InvalidStateTransitionError
from backend.app.models.entities import (
    Interview, Resume, CandidateProfile, InterviewState,
    AssessmentReport, KnowledgeConsistencyCheck, EvidenceNode,
    Answer, Evaluation, InterviewQuestion
)
from backend.app.schemas.interview import (
    InterviewCreateRequest, InterviewResponse, InterviewQuestionResponse
)
from backend.app.services.question_generator import QuestionGeneratorService
from backend.app.services.interview_engine import InterviewEngine
from backend.app.services.scoring_engine import ScoringEngine

router = APIRouter(prefix="/interviews", tags=["Interviews"])

@router.post("", response_model=InterviewResponse)
async def create_interview(request: InterviewCreateRequest, db: Session = Depends(get_db)):
    resume = db.query(Resume).filter_by(id=request.resume_id).first()
    if not resume:
        raise EntityNotFoundError("Resume", request.resume_id)

    profile = resume.profile

    interview = Interview(
        candidate_id=resume.candidate_id,
        resume_id=resume.id,
        target_role=request.target_role,
        interview_type=request.interview_type,
        initial_difficulty=request.initial_difficulty,
        current_difficulty=request.initial_difficulty,
        state=InterviewState.READY.value,
        total_questions=request.total_questions,
        question_mix=request.question_mix,
        current_question_index=0
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)

    # Generate personalized questions
    q_service = QuestionGeneratorService()
    await q_service.generate_interview_questions(db, interview, profile)

    db.refresh(interview)
    return InterviewResponse.from_orm(interview)

@router.get("", response_model=List[InterviewResponse])
def list_interviews(db: Session = Depends(get_db)):
    interviews = db.query(Interview).order_by(Interview.created_at.desc()).all()
    return [InterviewResponse.from_orm(i) for i in interviews]

@router.get("/{interview_id}", response_model=InterviewResponse)
def get_interview(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter_by(id=interview_id).first()
    if not interview:
        raise EntityNotFoundError("Interview", interview_id)
    return InterviewResponse.from_orm(interview)

@router.post("/{interview_id}/start", response_model=InterviewResponse)
def start_interview(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter_by(id=interview_id).first()
    if not interview:
        raise EntityNotFoundError("Interview", interview_id)

    interview = InterviewEngine.start_interview(db, interview)
    return InterviewResponse.from_orm(interview)

@router.get("/{interview_id}/current-question", response_model=InterviewQuestionResponse)
def get_current_question(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter_by(id=interview_id).first()
    if not interview:
        raise EntityNotFoundError("Interview", interview_id)

    q = InterviewEngine.get_current_question(interview)
    if not q:
        raise HTTPException(status_code=404, detail="No active question available for this session.")
    return InterviewQuestionResponse.from_orm(q)

@router.post("/{interview_id}/end", response_model=InterviewResponse)
async def end_interview(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter_by(id=interview_id).first()
    if not interview:
        raise EntityNotFoundError("Interview", interview_id)

    interview.state = InterviewState.COMPLETED.value
    db.commit()

    # Generate final assessment report
    await ScoringEngine.generate_final_report(db, interview)

    db.refresh(interview)
    return InterviewResponse.from_orm(interview)

@router.post("/{interview_id}/cancel")
def cancel_interview(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter_by(id=interview_id).first()
    if not interview:
        raise EntityNotFoundError("Interview", interview_id)

    interview.state = InterviewState.CANCELLED.value
    db.commit()
    return {"message": f"Interview {interview_id} has been cancelled."}

@router.delete("/{interview_id}")
def delete_interview(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(Interview).filter_by(id=interview_id).first()
    if not interview:
        raise EntityNotFoundError("Interview", interview_id)

    # 1. Clean up temporary audio files if stored on disk
    answers = db.query(Answer).filter_by(interview_id=interview_id).all()
    for a in answers:
        if a.audio_path:
            try:
                p = Path(a.audio_path)
                if p.exists():
                    p.unlink()
            except Exception:
                pass

    # 2. Delete child records in reverse dependency order to prevent FK violations
    db.query(AssessmentReport).filter_by(interview_id=interview_id).delete(synchronize_session=False)
    db.query(KnowledgeConsistencyCheck).filter_by(interview_id=interview_id).delete(synchronize_session=False)

    # 3. Evidence nodes must be deleted before questions (related_question_id points to interview_questions)
    db.query(EvidenceNode).filter_by(interview_id=interview_id).delete(synchronize_session=False)

    # 4. Clear parent_question_id to avoid intra-table FK constraints
    db.query(InterviewQuestion).filter_by(interview_id=interview_id).update({"parent_question_id": None}, synchronize_session=False)

    # 5. Evaluations & Answers
    answer_ids = [a.id for a in answers]
    if answer_ids:
        db.query(Evaluation).filter(Evaluation.answer_id.in_(answer_ids)).delete(synchronize_session=False)

    db.query(Answer).filter_by(interview_id=interview_id).delete(synchronize_session=False)

    # 6. Questions
    db.query(InterviewQuestion).filter_by(interview_id=interview_id).delete(synchronize_session=False)

    # 7. Interview record
    db.query(Interview).filter_by(id=interview_id).delete(synchronize_session=False)
    db.commit()

    return {"message": f"Interview {interview_id} successfully deleted."}
