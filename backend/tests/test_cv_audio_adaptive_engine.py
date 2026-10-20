import pytest
import math
import struct
import wave
import numpy as np
from pathlib import Path
from backend.app.services.audio_confidence_analyzer import AudioConfidenceAnalyzer
from backend.app.services.vision_analyzer import VisionAnalyzerService
from backend.app.services.interview_engine import InterviewEngine
from backend.app.integrations.mock_llm_provider import MockLLMProvider
from backend.app.models.entities import Interview, InterviewQuestion, Answer, Evaluation, InterviewState

def create_synthetic_wav(file_path: Path, duration_sec: float = 3.0, pause_duration_sec: float = 1.6, freq: float = 220.0):
    """Generates a synthetic PCM WAV file with an intentional long hesitation pause."""
    sr = 16000
    total_samples = int(sr * duration_sec)
    samples = []
    
    pause_start = 0.8
    pause_end = pause_start + pause_duration_sec
    
    for i in range(total_samples):
        t = i / float(sr)
        if pause_start <= t < pause_end:
            samples.append(0) # Injected silence hesitation
        else:
            samples.append(int(12000 * math.sin(2 * math.pi * freq * t)))
            
    with wave.open(str(file_path), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f'<{len(samples)}h', *samples))

# ==========================================
# 1. ACOUSTIC AUDIO SIGNAL ANALYZER TESTS
# ==========================================

def test_audio_analyzer_synthetic_waveform(tmp_path):
    wav_path = tmp_path / "test_cadence.wav"
    create_synthetic_wav(wav_path, duration_sec=3.5, pause_duration_sec=1.6)
    
    result = AudioConfidenceAnalyzer.analyze_audio_file(wav_path)
    
    assert "acoustic_confidence_score" in result
    assert result["acoustic_confidence_score"] > 0
    assert result["long_pause_hesitations_count"] >= 1, "Must detect the 1.6s hesitation pause"
    assert result["fluency_ratio_percent"] < 80.0
    assert "signal_processing_methodology" in result
    assert "waveform_decoder" in result["signal_processing_methodology"]

def test_audio_analyzer_missing_or_corrupt_file(tmp_path):
    empty_file = tmp_path / "empty.wav"
    empty_file.write_bytes(b"")
    
    result = AudioConfidenceAnalyzer.analyze_audio_file(empty_file)
    assert result["acoustic_confidence_score"] == 78.0 # Default graceful baseline
    assert result["long_pause_hesitations_count"] == 0

# ==========================================
# 2. COMPUTER VISION & POSTURE TESTS
# ==========================================

def test_vision_analyzer_face_verification():
    service = VisionAnalyzerService()
    test_interview_id = 99991
    
    # Synthetic face ROI (100x100 RGB image)
    face_1 = np.full((100, 100, 3), 120, dtype=np.uint8)
    
    # 1. First frame registers reference face
    res1 = service._verify_identity(face_1, test_interview_id)
    assert res1["status"] == "INITIALIZED_REFERENCE"
    assert res1["is_match"] is True
    
    # 2. Same candidate face confirms match
    res2 = service._verify_identity(face_1, test_interview_id)
    assert res2["status"] == "VERIFIED_MATCH"
    assert res2["is_match"] is True
    assert res2["similarity_score"] >= 0.90
    
    # 3. Drastically different face triggers mismatch flag
    face_mismatch = np.zeros((100, 100, 3), dtype=np.uint8)
    face_mismatch[::2, ::2, 0] = 255
    res3 = service._verify_identity(face_mismatch, test_interview_id)
    assert res3["status"] == "MISMATCH_FLAGGED"
    assert res3["is_match"] is False

def test_vision_analyzer_posture_kinematics():
    service = VisionAnalyzerService()
    
    # Scenario A: Normal upright candidate (centroid ~ 40% of height)
    posture_upright = service._analyze_posture(
        fx=200, fy=120, fw=100, fh=120, frame_width=640, frame_height=480, interview_id=99992
    )
    assert posture_upright["slouch_status"] == "Upright & Ergonomic"
    assert posture_upright["posture_composure_score"] >= 80.0
    
    # Scenario B: Slouching candidate (head dropped to lower part of frame, > 64%)
    posture_slouch = service._analyze_posture(
        fx=200, fy=300, fw=100, fh=120, frame_width=640, frame_height=480, interview_id=99993
    )
    assert "Slouch" in posture_slouch["slouch_status"]
    assert posture_slouch["posture_composure_score"] < posture_upright["posture_composure_score"]

def test_vision_report_synthesis():
    interview = Interview(id=99994, target_role="Backend")
    report_high = VisionAnalyzerService.generate_interview_vision_report(interview, average_score=85.0)
    assert report_high["visual_confidence_score"] >= 80.0
    assert report_high["stress_indicator_level"] == "LOW"
    assert "computer_vision_methodology" in report_high

# ==========================================
# 3. CODE CHALLENGE NON-ATTEMPT SCORING TESTS
# ==========================================

@pytest.mark.anyio
async def test_code_evaluation_boilerplate_unchanged():
    provider = MockLLMProvider()
    starter = (
        "def find_first_unique_token(tokens: list[str]) -> str | None:\n"
        "    for token in tokens:\n"
        "        if tokens.count(token) == 1:\n"
        "            return token\n"
        "    return None\n\n"
        "def find_first_unique_token_optimized(tokens: list[str]) -> str | None:\n"
        "    pass\n"
    )
    q_data = {
        "question_text": "Refactor to O(N)",
        "question_type": "CODE",
        "skill_assessed": "Python Algorithms",
        "expected_concepts": ["O(N) time complexity", "hash map"],
        "code_snippet": starter
    }
    
    # Candidate submits unchanged starter code without writing anything
    eval_unattempted = await provider.evaluate_answer(
        question_data=q_data,
        transcript="",
        code_submission=starter
    )
    assert eval_unattempted["overall_score"] <= 15.0, f"Unattempted starter code must score <= 15, got {eval_unattempted['overall_score']}"
    assert eval_unattempted["technical_score"] <= 15.0
    assert "without implementation" in eval_unattempted["feedback"].lower()

@pytest.mark.anyio
async def test_code_evaluation_optimal_attempt():
    provider = MockLLMProvider()
    q_data = {
        "question_text": "Refactor to O(N)",
        "question_type": "CODE",
        "skill_assessed": "Python Algorithms",
        "expected_concepts": ["O(N) time complexity", "hash map"],
        "code_snippet": "def find_first_unique_token_optimized(tokens): pass"
    }
    
    working_code = (
        "def find_first_unique_token_optimized(tokens: list[str]) -> str | None:\n"
        "    counts = {}\n"
        "    for t in tokens:\n"
        "        counts[t] = counts.get(t, 0) + 1\n"
        "    for t in tokens:\n"
        "        if counts[t] == 1:\n"
        "            return t\n"
        "    return None\n"
    )
    
    eval_working = await provider.evaluate_answer(
        question_data=q_data,
        transcript="I used a frequency hash map for O(N) linear time scanning.",
        code_submission=working_code
    )
    assert eval_working["overall_score"] >= 80.0, f"Optimal solution should score >= 80, got {eval_working['overall_score']}"

# ==========================================
# 4. INSTANT ADAPTIVE DIFFICULTY MODULE TESTS
# ==========================================

def test_instant_adaptive_difficulty_step_up_and_down(db_session):
    interview = Interview(
        target_role="Software Engineer",
        interview_type="technical",
        current_difficulty="INTERMEDIATE",
        total_questions=5,
        current_question_index=1
    )
    db_session.add(interview)
    db_session.commit()
    db_session.refresh(interview)
    
    q1 = InterviewQuestion(
        interview_id=interview.id,
        order_index=1,
        question_text="Q1 Text",
        skill_assessed="Python",
        difficulty="INTERMEDIATE"
    )
    q2 = InterviewQuestion(
        interview_id=interview.id,
        order_index=2,
        question_text="Q2 Text",
        skill_assessed="System Design",
        difficulty="INTERMEDIATE"
    )
    db_session.add_all([q1, q2])
    db_session.commit()
    
    ans1 = Answer(interview_id=interview.id, question_id=q1.id, transcript="Great answer")
    db_session.add(ans1)
    db_session.commit()
    db_session.refresh(ans1)
    
    # 1. Candidate scores 88/100 -> Instant Step UP to ADVANCED
    ev1 = Evaluation(
        answer_id=ans1.id,
        overall_score=88.0,
        technical_score=88.0,
        conceptual_score=85.0,
        relevance_score=90.0,
        clarity_score=85.0,
        feedback="Superb answer"
    )
    db_session.add(ev1)
    db_session.commit()
    
    next_available = InterviewEngine.advance_question_state(db_session, interview)
    assert next_available is True
    assert interview.current_difficulty == "ADVANCED", "Score 88 must step UP difficulty to ADVANCED"
    
    # Verify next question synchronized difficulty
    db_session.refresh(q2)
    assert q2.difficulty == "ADVANCED"
    
    # 2. Candidate answers Q2 poorly (35/100) -> Instant Step DOWN to INTERMEDIATE
    ans2 = Answer(interview_id=interview.id, question_id=q2.id, transcript="I don't know")
    db_session.add(ans2)
    db_session.commit()
    db_session.refresh(ans2)
    
    ev2 = Evaluation(
        answer_id=ans2.id,
        overall_score=35.0,
        technical_score=35.0,
        conceptual_score=20.0,
        relevance_score=30.0,
        clarity_score=60.0,
        feedback="Struggled on advanced topic"
    )
    db_session.add(ev2)
    db_session.commit()
    
    new_diff, reason = InterviewEngine.calculate_difficulty_adjustment(interview)
    assert new_diff == "INTERMEDIATE", "Score 35 must step DOWN difficulty to INTERMEDIATE"

# ==========================================
# 5. DYNAMIC ARBITRARY QUESTION COUNT TESTS
# ==========================================

@pytest.mark.anyio
async def test_dynamic_question_count_arbitrary():
    provider = MockLLMProvider()
    profile = {"projects": [{"title": "Cloud Scale"}], "skills": {"backend": ["Python", "Docker"]}}
    
    for count in [1, 3, 7, 10, 15]:
        questions = await provider.generate_questions(
            profile_data=profile,
            target_role="Full Stack",
            interview_type="technical",
            difficulty="INTERMEDIATE",
            count=count,
            assessed_topics=["Python", "System Design"],
            question_mix="mixed"
        )
        assert len(questions) == count, f"Requested {count} questions, got {len(questions)}"
        assert all("question_text" in q and "question_type" in q for q in questions)
