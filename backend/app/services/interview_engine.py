from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from backend.app.models.entities import (
    Interview, InterviewQuestion, InterviewState, DifficultyLevel
)
from backend.app.core.config import settings
from backend.app.core.exceptions import InvalidStateTransitionError

DIFFICULTY_ORDER = [
    DifficultyLevel.BEGINNER.value,
    DifficultyLevel.INTERMEDIATE.value,
    DifficultyLevel.ADVANCED.value
]

class InterviewEngine:
    @staticmethod
    def start_interview(db: Session, interview: Interview) -> Interview:
        if interview.state not in [InterviewState.CREATED.value, InterviewState.READY.value]:
            raise InvalidStateTransitionError(interview.state, InterviewState.IN_PROGRESS.value)
        
        interview.state = InterviewState.IN_PROGRESS.value
        interview.started_at = datetime.utcnow()
        interview.current_question_index = 1
        
        if not interview.difficulty_history:
            interview.difficulty_history = [{
                "question_index": 1,
                "difficulty": interview.current_difficulty,
                "reason": "Initial candidate-selected starting difficulty."
            }]
        
        db.commit()
        db.refresh(interview)
        return interview

    @staticmethod
    def get_current_question(interview: Interview) -> Optional[InterviewQuestion]:
        if not interview.questions:
            return None
        target_idx = interview.current_question_index
        for q in interview.questions:
            if q.order_index == target_idx:
                return q
        return interview.questions[-1]

    @staticmethod
    def calculate_difficulty_adjustment(interview: Interview) -> tuple[str, str]:
        """
        Calculates dynamic single-question difficulty adjustment:
        - Steps UP if latest response score >= 75.0 (BEGINNER -> INTERMEDIATE -> ADVANCED)
        - Steps DOWN if latest response score < 50.0 (ADVANCED -> INTERMEDIATE -> BEGINNER)
        - Maintains difficulty for consistent mid-tier performance (50 - 74)
        """
        answered = [
            q for q in interview.questions
            if q.answer and q.answer.evaluation
        ]
        if not answered:
            return interview.current_difficulty, "No evaluations recorded yet."

        latest_evaluation = answered[-1].answer.evaluation
        latest_score = latest_evaluation.overall_score
        current_diff = interview.current_difficulty
        current_idx = DIFFICULTY_ORDER.index(current_diff) if current_diff in DIFFICULTY_ORDER else 1

        # Check for stepping UP (high technical score >= 75)
        if latest_score >= 75.0:
            if current_idx < len(DIFFICULTY_ORDER) - 1:
                new_diff = DIFFICULTY_ORDER[current_idx + 1]
                reason = f"Strong technical response ({latest_score:.1f}/100). Upgrading difficulty from {current_diff} to {new_diff}."
                return new_diff, reason
            else:
                return current_diff, f"Candidate performing at top difficulty level ({current_diff}, {latest_score:.1f}/100)."

        # Check for stepping DOWN (struggling < 50)
        if latest_score < 50.0:
            if current_idx > 0:
                new_diff = DIFFICULTY_ORDER[current_idx - 1]
                reason = f"Struggled with previous topic ({latest_score:.1f}/100). Adjusting to build confidence from {current_diff} down to {new_diff}."
                return new_diff, reason
            else:
                return current_diff, f"Maintaining foundational level ({current_diff}) to support candidate progression."

        return current_diff, f"Maintaining {current_diff} difficulty ({latest_score:.1f}/100 steady performance)."

    @classmethod
    def advance_question_state(cls, db: Session, interview: Interview) -> bool:
        """
        Advances the interview to the next question or completes it.
        Dynamically applies difficulty adjustments to subsequent questions.
        Returns True if next question is available, False if completed.
        """
        # Calculate adaptive difficulty
        new_diff, reason = cls.calculate_difficulty_adjustment(interview)
        if new_diff != interview.current_difficulty:
            interview.current_difficulty = new_diff
            hist = list(interview.difficulty_history or [])
            hist.append({
                "question_index": interview.current_question_index + 1,
                "difficulty": new_diff,
                "reason": reason
            })
            interview.difficulty_history = hist

        # Check if more questions exist
        if interview.current_question_index < interview.total_questions:
            interview.current_question_index += 1
            interview.state = InterviewState.IN_PROGRESS.value

            # Dynamically synchronize the next question's difficulty
            next_q = cls.get_current_question(interview)
            if next_q:
                next_q.difficulty = interview.current_difficulty
                db.add(next_q)

            db.commit()
            db.refresh(interview)
            return True
        else:
            interview.state = InterviewState.COMPLETED.value
            interview.completed_at = datetime.utcnow()
            db.commit()
            db.refresh(interview)
            return False
