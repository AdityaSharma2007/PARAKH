import uuid
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, Request
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.core.config import settings
from backend.app.core.security import validate_audio_file, generate_secure_filename
from backend.app.core.exceptions import EntityNotFoundError, InvalidStateTransitionError
from backend.app.models.entities import Interview, InterviewQuestion, Answer, Evaluation, InterviewState
from backend.app.schemas.interview import AnswerSubmitResponse, CodeRunRequest, CodeRunResponse
from backend.app.services.answer_evaluator import AnswerEvaluatorService
from backend.app.services.code_runner import CodeRunnerService
from backend.app.services.interview_engine import InterviewEngine
from backend.app.services.scoring_engine import ScoringEngine
from backend.app.services.question_generator import QuestionGeneratorService

router = APIRouter(prefix="/interviews/{interview_id}/answers", tags=["Spoken Answers & Evaluations"])

@router.post("/audio", response_model=AnswerSubmitResponse)
async def submit_spoken_answer(
    interview_id: int,
    question_id: int = Form(...),
    duration_seconds: float = Form(0.0),
    audio_file: UploadFile | None = File(None),
    browser_transcript: str | None = Form(None),
    selected_option: str | None = Form(None),
    code_submission: str | None = Form(None),
    db: Session = Depends(get_db)
):
    interview = db.query(Interview).filter_by(id=interview_id).first()
    if not interview:
        raise EntityNotFoundError("Interview", interview_id)

    if interview.state not in [InterviewState.IN_PROGRESS.value, InterviewState.RECORDING.value, InterviewState.EVALUATED.value]:
        raise InvalidStateTransitionError(interview.state, InterviewState.PROCESSING.value, "Interview is not active.")

    question = db.query(InterviewQuestion).filter_by(id=question_id, interview_id=interview.id).first()
    if not question:
        raise EntityNotFoundError("InterviewQuestion", question_id)

    # Validate and save audio chunk if present
    destination_path = None
    if audio_file and audio_file.filename:
        content = await audio_file.read()
        if len(content) > 0:
            # Auto-align WebM container header if browser flushed orphan chunk headers
            ebml_idx = content.find(b"\x1a\x45\xdf\xa3")
            if ebml_idx > 0:
                content = content[ebml_idx:]

            validate_audio_file(audio_file.filename or "recording.webm", content)
            secure_audio_name = generate_secure_filename(audio_file.filename or "recording.webm")
            destination_path = settings.AUDIO_DIR / secure_audio_name
            with open(destination_path, "wb") as f:
                f.write(content)

    # Process transcription and evaluation
    eval_service = AnswerEvaluatorService()
    evaluation = await eval_service.process_spoken_answer(
        db=db,
        interview=interview,
        question=question,
        audio_file_path=destination_path,
        duration_seconds=duration_seconds,
        browser_transcript=browser_transcript,
        selected_option=selected_option,
        code_submission=code_submission
    )

    answer = question.answer

    # Check for dynamic follow-up trigger:
    # If the score was in the intermediate/borderline zone (50 - 75), and this wasn't already a follow-up,
    # and interview has not exceeded total limit + 2
    if not question.is_followup and 50 <= evaluation.overall_score <= 75 and interview.total_questions < 8:
        q_service = QuestionGeneratorService()
        await q_service.create_followup_question(
            db=db,
            interview=interview,
            parent_question=question,
            candidate_transcript=answer.transcript or ""
        )

    # Advance state machine
    next_available = InterviewEngine.advance_question_state(db, interview)
    is_completed = (interview.state == InterviewState.COMPLETED.value)

    if is_completed:
        await ScoringEngine.generate_final_report(db, interview)

    is_correct = None
    if question.question_type == "MCQ" and selected_option and question.correct_option:
        is_correct = (selected_option.strip().upper() == str(question.correct_option).strip().upper())

    return AnswerSubmitResponse(
        answer_id=answer.id,
        question_id=question.id,
        transcript=answer.transcript or "",
        stt_confidence=answer.stt_confidence,
        overall_score=evaluation.overall_score,
        feedback=evaluation.feedback,
        current_difficulty=interview.current_difficulty,
        next_question_available=next_available,
        is_interview_completed=is_completed,
        selected_option=answer.selected_option,
        correct_option=question.correct_option,
        is_correct=is_correct,
        explanation=question.explanation,
        code_feedback=evaluation.feedback if question.question_type == "CODE" else None
    )

@router.get("/{answer_id}")
def get_answer_details(interview_id: int, answer_id: int, db: Session = Depends(get_db)):
    answer = db.query(Answer).filter_by(id=answer_id, interview_id=interview_id).first()
    if not answer:
        raise EntityNotFoundError("Answer", answer_id)
    
    ev = answer.evaluation
    return {
        "id": answer.id,
        "question_id": answer.question_id,
        "transcript": answer.transcript,
        "stt_confidence": answer.stt_confidence,
        "evaluation": {
            "overall_score": ev.overall_score if ev else None,
            "technical_score": ev.technical_score if ev else None,
            "feedback": ev.feedback if ev else None,
            "why_this_score": ev.why_this_score if ev else None,
            "reliability_tier": ev.reliability_tier if ev else None
        }
    }

@router.post("/{answer_id}/retry")
def retry_answer(interview_id: int, answer_id: int, db: Session = Depends(get_db)):
    answer = db.query(Answer).filter_by(id=answer_id, interview_id=interview_id).first()
    if not answer:
        raise EntityNotFoundError("Answer", answer_id)

    # Remove evaluation to permit clean retry
    if answer.evaluation:
        db.delete(answer.evaluation)
    answer.transcript = None
    answer.retry_count += 1
    db.commit()

    return {"message": "Answer reset. Candidate may re-record response."}

@router.post("/run-code/{question_id}", response_model=CodeRunResponse)
async def run_code_solution(
    interview_id: int,
    question_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    interview = db.query(Interview).filter_by(id=interview_id).first()
    if not interview:
        raise EntityNotFoundError("Interview", interview_id)

    question = db.query(InterviewQuestion).filter_by(id=question_id, interview_id=interview.id).first()
    if not question:
        raise EntityNotFoundError("InterviewQuestion", question_id)

    code = ""
    language = question.language or "python"
    try:
        body_json = await request.json()
        if isinstance(body_json, dict):
            code = body_json.get("code", "")
            language = body_json.get("language") or language
    except Exception:
        raw_body = (await request.body()).decode("utf-8", errors="ignore")
        if raw_body:
            try:
                import json
                parsed = json.loads(raw_body)
                if isinstance(parsed, dict):
                    code = parsed.get("code", "")
                    language = parsed.get("language") or language
                else:
                    code = raw_body
            except Exception:
                code = raw_body

    res = CodeRunnerService.run_code(
        code=code,
        test_cases=question.test_cases or [],
        language=language,
        starter_code=question.code_snippet or "",
        question_text=question.question_text or ""
    )
    return CodeRunResponse(**res)
