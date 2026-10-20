from pathlib import Path
from sqlalchemy.orm import Session
from backend.app.models.entities import Interview, InterviewQuestion, Answer, Evaluation
from backend.app.integrations import get_llm_provider, get_speech_provider
from backend.app.services.evidence_graph_service import EvidenceGraphService
from backend.app.core.config import settings

class AnswerEvaluatorService:
    def __init__(self):
        self.llm = get_llm_provider()
        self.stt = get_speech_provider()

    async def process_spoken_answer(
        self,
        db: Session,
        interview: Interview,
        question: InterviewQuestion,
        audio_file_path: Path | str | None = None,
        duration_seconds: float = 0.0,
        browser_transcript: str | None = None,
        selected_option: str | None = None,
        code_submission: str | None = None
    ) -> Evaluation:
        """
        Transcribes candidate audio, reconciles with browser-native transcript,
        evaluates spoken, MCQ, or code submissions, persists records, and updates evidence graph.
        """
        stt_confidence = 1.0
        whisper_transcript = ""

        # 1. Transcribe audio if provided
        if audio_file_path and Path(audio_file_path).exists():
            whisper_transcript, stt_confidence = self.stt.transcribe(audio_file_path)

        # 2. Reconcile transcript
        # If candidate confirmed or corrected via browser Web Speech API, use browser_transcript
        clean_browser = browser_transcript.strip() if browser_transcript else ""
        if clean_browser:
            transcript = clean_browser
            if stt_confidence < 0.6:
                stt_confidence = 0.90 # Browser speech recognition was confirmed by user
        elif whisper_transcript:
            transcript = whisper_transcript.strip()
        else:
            if selected_option:
                transcript = f"Selected Option {selected_option}"
            elif code_submission:
                transcript = "Code solution submitted without spoken audio."
            else:
                transcript = ""

        # 3. Check or create Answer entity
        answer = question.answer
        if not answer:
            answer = Answer(
                interview_id=interview.id,
                question_id=question.id,
                audio_path=str(audio_file_path) if (audio_file_path and settings.AUDIO_RETENTION_ENABLED) else None,
                audio_duration_seconds=duration_seconds,
                transcript=transcript,
                browser_transcript=clean_browser if clean_browser else None,
                selected_option=selected_option,
                code_submission=code_submission,
                stt_confidence=stt_confidence,
                is_audio_retained=settings.AUDIO_RETENTION_ENABLED,
                retry_count=0
            )
            db.add(answer)
        else:
            answer.transcript = transcript
            answer.browser_transcript = clean_browser if clean_browser else None
            answer.selected_option = selected_option
            answer.code_submission = code_submission
            answer.stt_confidence = stt_confidence
            answer.audio_duration_seconds = duration_seconds
            answer.retry_count += 1

        db.commit()
        db.refresh(answer)

        # 4. Assess audio reliability
        reliability_tier = "HIGH"
        if audio_file_path and stt_confidence < settings.CONFIDENCE_MIN_RELIABLE_THRESHOLD and not clean_browser:
            reliability_tier = "LOW"
        elif len(transcript.strip()) < 10 and question.question_type == "SPOKEN":
            reliability_tier = "MEDIUM"

        # 5. Run LLM evaluation
        eval_dict = await self.llm.evaluate_answer(
            question_data={
                "question_text": question.question_text,
                "question_type": question.question_type,
                "skill_assessed": question.skill_assessed,
                "expected_concepts": question.expected_concepts,
                "evaluation_rubric": question.evaluation_rubric,
                "difficulty": question.difficulty,
                "options": question.options,
                "correct_option": question.correct_option,
                "explanation": question.explanation
            },
            transcript=transcript,
            selected_option=selected_option,
            code_submission=code_submission
        )

        # 6. Persist Evaluation
        evaluation = answer.evaluation
        if not evaluation:
            evaluation = Evaluation(
                answer_id=answer.id,
                overall_score=eval_dict.get("overall_score", 50.0),
                technical_score=eval_dict.get("technical_score", 50.0),
                conceptual_score=eval_dict.get("conceptual_score", 50.0),
                relevance_score=eval_dict.get("relevance_score", 50.0),
                clarity_score=eval_dict.get("clarity_score", 50.0),
                correct_concepts=eval_dict.get("correct_concepts", []),
                missing_concepts=eval_dict.get("missing_concepts", []),
                incorrect_statements=eval_dict.get("incorrect_statements", []),
                transcript_evidence=eval_dict.get("transcript_evidence", []),
                feedback=eval_dict.get("feedback", "Evaluation recorded."),
                improvement_tips=eval_dict.get("improvement_tips", []),
                confidence=eval_dict.get("confidence", 0.9),
                reliability_tier=reliability_tier,
                provider_mode="gemini" if settings.GEMINI_API_KEY else "mock",
                why_this_score=eval_dict.get("why_this_score", "Evaluated based on expected concept alignment.")
            )
            db.add(evaluation)
        else:
            evaluation.overall_score = eval_dict.get("overall_score", 50.0)
            evaluation.technical_score = eval_dict.get("technical_score", 50.0)
            evaluation.conceptual_score = eval_dict.get("conceptual_score", 50.0)
            evaluation.relevance_score = eval_dict.get("relevance_score", 50.0)
            evaluation.clarity_score = eval_dict.get("clarity_score", 50.0)
            evaluation.correct_concepts = eval_dict.get("correct_concepts", [])
            evaluation.missing_concepts = eval_dict.get("missing_concepts", [])
            evaluation.incorrect_statements = eval_dict.get("incorrect_statements", [])
            evaluation.transcript_evidence = eval_dict.get("transcript_evidence", [])
            evaluation.feedback = eval_dict.get("feedback", "Evaluation updated.")
            evaluation.improvement_tips = eval_dict.get("improvement_tips", [])
            evaluation.confidence = eval_dict.get("confidence", 0.9)
            evaluation.reliability_tier = reliability_tier
            evaluation.why_this_score = eval_dict.get("why_this_score")

        db.commit()
        db.refresh(evaluation)

        # 7. Update Resume-to-Evidence Intelligence Graph
        EvidenceGraphService.sync_evidence_nodes(db, interview)

        return evaluation
