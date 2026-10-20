import pytest
from backend.app.models.entities import Interview, InterviewQuestion, Answer, Evaluation, DifficultyLevel
from backend.app.services.interview_engine import InterviewEngine

def create_mock_evaluated_interview(scores: list[float], starting_difficulty="INTERMEDIATE"):
    interview = Interview(
        id=1,
        target_role="Full Stack Engineer",
        current_difficulty=starting_difficulty,
        total_questions=len(scores),
        current_question_index=1,
        difficulty_history=[]
    )
    questions = []
    for idx, score in enumerate(scores, 1):
        q = InterviewQuestion(
            id=idx,
            interview_id=1,
            order_index=idx,
            question_text=f"Question {idx}",
            skill_assessed="Python",
            difficulty=starting_difficulty
        )
        ans = Answer(id=idx, interview_id=1, question_id=idx)
        ev = Evaluation(
            id=idx,
            answer_id=idx,
            overall_score=score,
            technical_score=score,
            conceptual_score=score,
            relevance_score=score,
            clarity_score=score,
            feedback="Good",
            confidence=0.9
        )
        ans.evaluation = ev
        q.answer = ans
        questions.append(q)
    interview.questions = questions
    return interview

def test_difficulty_steps_up_on_strong_performance():
    # 2 consecutive high scores (85, 90) starting from INTERMEDIATE
    interview = create_mock_evaluated_interview([85.0, 90.0], starting_difficulty="INTERMEDIATE")
    new_diff, reason = InterviewEngine.calculate_difficulty_adjustment(interview)
    assert new_diff == DifficultyLevel.ADVANCED.value
    assert "Upgrading difficulty" in reason

def test_difficulty_steps_down_on_weak_performance():
    # 2 consecutive low scores (40, 45) starting from INTERMEDIATE
    interview = create_mock_evaluated_interview([40.0, 45.0], starting_difficulty="INTERMEDIATE")
    new_diff, reason = InterviewEngine.calculate_difficulty_adjustment(interview)
    assert new_diff == DifficultyLevel.BEGINNER.value
    assert "Adjusting to build confidence" in reason

def test_difficulty_clamps_at_advanced():
    # Starting at ADVANCED, cannot step up further
    interview = create_mock_evaluated_interview([90.0, 95.0], starting_difficulty="ADVANCED")
    new_diff, reason = InterviewEngine.calculate_difficulty_adjustment(interview)
    assert new_diff == DifficultyLevel.ADVANCED.value

def test_difficulty_clamps_at_beginner():
    # Starting at BEGINNER, cannot step down further
    interview = create_mock_evaluated_interview([30.0, 35.0], starting_difficulty="BEGINNER")
    new_diff, reason = InterviewEngine.calculate_difficulty_adjustment(interview)
    assert new_diff == DifficultyLevel.BEGINNER.value
