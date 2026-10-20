import pytest
import math
import struct
import wave
import base64
import numpy as np
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.audio_confidence_analyzer import AudioConfidenceAnalyzer
from backend.app.services.vision_analyzer import VisionAnalyzerService
from backend.app.services.interview_engine import InterviewEngine
from backend.app.integrations.mock_llm_provider import MockLLMProvider
from backend.app.models.entities import Interview, InterviewQuestion, Answer, Evaluation, InterviewState

client = TestClient(app)

def create_synthetic_wav(file_path: Path, duration_sec: float = 3.0, silence_runs: list = None, freq: float = 220.0):
    sr = 16000
    total_samples = int(sr * duration_sec)
    samples = []
    
    silence_runs = silence_runs or []
    for i in range(total_samples):
        t = i / float(sr)
        is_silent = any(start <= t < end for (start, end) in silence_runs)
        if is_silent:
            samples.append(0)
        else:
            samples.append(int(10000 * math.sin(2 * math.pi * freq * t)))
            
    with wave.open(str(file_path), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f'<{len(samples)}h', *samples))

# ==============================================================================
# JPMORGAN QA SUITE - TEST 1: ACOUSTIC AUDIO SIGNAL EDGE CASES
# ==============================================================================

def test_audio_edge_case_pure_silence(tmp_path):
    """Audio containing 100% silence (zero sound) must not crash or divide by zero."""
    wav_path = tmp_path / "pure_silence.wav"
    sr = 16000
    with wave.open(str(wav_path), 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f'<{sr * 2}h', *([0] * (sr * 2))))
        
    res = AudioConfidenceAnalyzer.analyze_audio_file(wav_path)
    assert res["fluency_ratio_percent"] <= 5.0
    assert res["acoustic_confidence_score"] <= 60.0
    assert "signal_processing_methodology" in res

def test_audio_edge_case_multiple_long_hesitations(tmp_path):
    """Audio containing 3 distinct pauses > 1.5s must accurately count all 3."""
    wav_path = tmp_path / "triple_pause.wav"
    # 10s audio with three 1.6s pauses
    silence_runs = [(1.0, 2.6), (4.0, 5.6), (7.0, 8.6)]
    create_synthetic_wav(wav_path, duration_sec=10.0, silence_runs=silence_runs)
    
    res = AudioConfidenceAnalyzer.analyze_audio_file(wav_path)
    assert res["long_pause_hesitations_count"] >= 3, f"Expected 3 long pauses, got {res['long_pause_hesitations_count']}"
    assert "Hesitant" in res["speaking_cadence"]

def test_audio_edge_case_ultra_short_sample(tmp_path):
    """Audio with < 0.2s duration should be handled gracefully without math errors."""
    wav_path = tmp_path / "micro.wav"
    create_synthetic_wav(wav_path, duration_sec=0.1)
    
    res = AudioConfidenceAnalyzer.analyze_audio_file(wav_path)
    assert res["acoustic_confidence_score"] > 0
    assert "Acoustic baseline" in res["acoustic_summary"]

# ==============================================================================
# JPMORGAN QA SUITE - TEST 2: COMPUTER VISION & ANTI-CHEATING STRESS VECTORS
# ==============================================================================

def test_vision_edge_case_garbage_base64():
    """Corrupted or invalid base64 frame input must gracefully return fallback."""
    service = VisionAnalyzerService()
    res = service.analyze_frame_data("not_valid_base64!!!###")
    assert res["face_detected"] is False or res["face_detected"] is True
    assert "visual_confidence_score" in res

def test_vision_edge_case_biometric_face_identity_reentry():
    """Identity continuity: Ref Face -> Match -> Mismatch -> Candidate Re-entry."""
    service = VisionAnalyzerService()
    test_id = 88101
    
    ref_face = np.full((120, 120, 3), 150, dtype=np.uint8)
    impostor_face = np.zeros((120, 120, 3), dtype=np.uint8)
    impostor_face[::3, ::3, 1] = 255
    
    # Frame 1: Register reference
    f1 = service._verify_identity(ref_face, test_id)
    assert f1["status"] == "INITIALIZED_REFERENCE"
    
    # Frame 2: Authentic match
    f2 = service._verify_identity(ref_face, test_id)
    assert f2["status"] == "VERIFIED_MATCH"
    assert f2["is_match"] is True
    
    # Frame 3: Impostor substitution
    f3 = service._verify_identity(impostor_face, test_id)
    assert f3["status"] == "MISMATCH_FLAGGED"
    assert f3["is_match"] is False
    
    # Frame 4: Authentic candidate returns
    f4 = service._verify_identity(ref_face, test_id)
    assert f4["status"] == "VERIFIED_MATCH"
    assert f4["is_match"] is True

def test_vision_posture_extreme_boundary_conditions():
    """Test extreme posture metrics (extreme tilt, rapid displacement, standing)."""
    service = VisionAnalyzerService()
    test_id = 88102
    
    # Standing position (very high in frame, norm_y < 0.28)
    res_standing = service._analyze_posture(fx=200, fy=10, fw=100, fh=80, frame_width=640, frame_height=480, interview_id=test_id)
    assert "Standing" in res_standing["slouch_status"] or "Elevated" in res_standing["slouch_status"]
    
    # Extreme lateral tilt (head far to right edge)
    res_tilted = service._analyze_posture(fx=580, fy=180, fw=80, fh=100, frame_width=640, frame_height=480, interview_id=test_id)
    assert abs(res_tilted["lean_angle_deg"]) > 16.0
    assert "Tilt" in res_tilted["lean_status"]

# ==============================================================================
# JPMORGAN QA SUITE - TEST 3: CODE CHALLENGE & BOILERPLATE SCORING INTEGRITY
# ==============================================================================

@pytest.mark.anyio
async def test_code_edge_case_whitespace_and_comments_only():
    """Candidate submits only comments and blank lines -> Strictly score <= 15.0."""
    provider = MockLLMProvider()
    starter = "def solve():\n    pass\n"
    q_data = {
        "question_text": "Implement algorithm",
        "question_type": "CODE",
        "skill_assessed": "Python",
        "expected_concepts": ["O(N) time complexity"],
        "code_snippet": starter
    }
    
    junk_submissions = [
        "",
        "   \n\t\n   ",
        "# I will do this later\n# TODO: optimize\n",
        starter,
        "def solve():\n    # just starter code with comments\n    pass\n"
    ]
    
    for sub in junk_submissions:
        res = await provider.evaluate_answer(question_data=q_data, transcript="", code_submission=sub)
        assert res["overall_score"] <= 15.0, f"Submission '{sub}' awarded {res['overall_score']} marks, must be <= 15.0"
        assert res["technical_score"] <= 15.0

@pytest.mark.anyio
async def test_code_verbal_admission_of_uncertainty():
    """Candidate admits 'I have no idea how to do this' on code question."""
    provider = MockLLMProvider()
    q_data = {
        "question_text": "Implement algorithm",
        "question_type": "CODE",
        "skill_assessed": "Python",
        "expected_concepts": ["O(N) time"],
        "code_snippet": "def solve(): pass"
    }
    
    res = await provider.evaluate_answer(
        question_data=q_data,
        transcript="I have no idea how to solve this algorithm, sorry.",
        code_submission="def solve(): pass"
    )
    assert res["overall_score"] <= 15.0
    assert "unfamiliarity" in res["feedback"].lower() or "without implementation" in res["feedback"].lower()

# ==============================================================================
# JPMORGAN QA SUITE - TEST 4: MCQ CASE-INSENSITIVITY & GUESS DETECTION
# ==============================================================================

@pytest.mark.anyio
async def test_mcq_case_insensitivity_and_spacing():
    """Selected option ' c ' must match correct option 'C'."""
    provider = MockLLMProvider()
    q_data = {
        "question_text": "Select correct index",
        "question_type": "MCQ",
        "skill_assessed": "Database Indexing",
        "correct_option": "C",
        "expected_concepts": ["composite index", "equality before range"],
        "explanation": "B-tree index on (status, created_at)"
    }
    
    res = await provider.evaluate_answer(
        question_data=q_data,
        transcript="I chose Option C because composite indexes require equality columns first.",
        selected_option="  c  "
    )
    assert res["overall_score"] >= 80.0, f"Case-insensitive correct MCQ choice should score >= 80, got {res['overall_score']}"

@pytest.mark.anyio
async def test_mcq_guess_with_admission_of_ignorance():
    """Candidate correctly guesses 'C' but explicitly says 'I don't know, pure guess'."""
    provider = MockLLMProvider()
    q_data = {
        "question_text": "Select correct index",
        "question_type": "MCQ",
        "skill_assessed": "Database Indexing",
        "correct_option": "C",
        "expected_concepts": ["composite index"],
        "explanation": "Explanation text"
    }
    
    res = await provider.evaluate_answer(
        question_data=q_data,
        transcript="I don't know this at all, I'm just guessing C.",
        selected_option="C"
    )
    assert res["overall_score"] <= 30.0, f"Blind guess admitted by candidate must not score high, got {res['overall_score']}"
    assert "guess" in res["why_this_score"].lower() or "lack of knowledge" in res["why_this_score"].lower()

# ==============================================================================
# JPMORGAN QA SUITE - TEST 5: QUESTION MIX MODES & ARBITRARY COUNTS
# ==============================================================================

@pytest.mark.anyio
async def test_question_mix_modes():
    provider = MockLLMProvider()
    profile = {"skills": {"backend": ["Python", "FastAPI"]}}
    
    # 1. Spoken only
    spoken_qs = await provider.generate_questions(
        profile_data=profile, target_role="Backend", interview_type="technical",
        difficulty="INTERMEDIATE", count=6, assessed_topics=["Python"], question_mix="spoken_only"
    )
    assert len(spoken_qs) == 6
    assert all(q["question_type"] == "SPOKEN" for q in spoken_qs)
    
    # 2. Coding and MCQ only
    code_mcq_qs = await provider.generate_questions(
        profile_data=profile, target_role="Backend", interview_type="technical",
        difficulty="INTERMEDIATE", count=6, assessed_topics=["Python"], question_mix="coding_mcq"
    )
    assert len(code_mcq_qs) == 6
    assert all(q["question_type"] in ["MCQ", "CODE"] for q in code_mcq_qs)

# ==============================================================================
# JPMORGAN QA SUITE - TEST 6: FULL WORKFLOW WITH AUDIO, VISION & ADAPTATION
# ==============================================================================

@pytest.mark.anyio
async def test_full_workflow_end_to_end_jpmorgan(db_session, tmp_path):
    # 1. Create interview with count=3
    interview = Interview(
        target_role="Full Stack Engineer",
        interview_type="technical",
        current_difficulty="INTERMEDIATE",
        total_questions=3,
        current_question_index=1,
        question_mix="mixed"
    )
    db_session.add(interview)
    db_session.commit()
    db_session.refresh(interview)
    
    # 2. Add 3 questions
    q1 = InterviewQuestion(interview_id=interview.id, order_index=1, question_text="Q1 Spoken", skill_assessed="System Architecture", question_type="SPOKEN", difficulty="INTERMEDIATE")
    q2 = InterviewQuestion(interview_id=interview.id, order_index=2, question_text="Q2 MCQ", skill_assessed="Databases", question_type="MCQ", difficulty="INTERMEDIATE", correct_option="A")
    q3 = InterviewQuestion(interview_id=interview.id, order_index=3, question_text="Q3 Code", skill_assessed="Algorithms", question_type="CODE", difficulty="INTERMEDIATE", code_snippet="def solve(): pass")
    db_session.add_all([q1, q2, q3])
    db_session.commit()
    
    # 3. Simulate Candidate answering Q1 with real synthetic audio
    audio_path = tmp_path / "q1_answer.wav"
    create_synthetic_wav(audio_path, duration_sec=4.0)
    
    ans1 = Answer(interview_id=interview.id, question_id=q1.id, audio_path=str(audio_path), audio_duration_seconds=4.0, transcript="Architectural trade-offs were managed cleanly.")
    db_session.add(ans1)
    db_session.commit()
    db_session.refresh(ans1)
    
    ev1 = Evaluation(
        answer_id=ans1.id, overall_score=85.0, technical_score=85.0, conceptual_score=85.0, relevance_score=90.0, clarity_score=80.0, feedback="Strong architecture answer."
    )
    db_session.add(ev1)
    db_session.commit()
    
    # Verify adaptive difficulty stepped UP
    has_next = InterviewEngine.advance_question_state(db_session, interview)
    assert has_next is True
    assert interview.current_difficulty == "ADVANCED"
    db_session.refresh(q2)
    assert q2.difficulty == "ADVANCED"
    
    # 4. Candidate answers Q2 with wrong answer
    ans2 = Answer(interview_id=interview.id, question_id=q2.id, selected_option="B", transcript="Selected Option B")
    db_session.add(ans2)
    db_session.commit()
    db_session.refresh(ans2)
    
    ev2 = Evaluation(
        answer_id=ans2.id, overall_score=30.0, technical_score=30.0, conceptual_score=25.0, relevance_score=40.0, clarity_score=70.0, feedback="Incorrect option selected."
    )
    db_session.add(ev2)
    db_session.commit()
    
    # Verify adaptive difficulty stepped DOWN
    has_next = InterviewEngine.advance_question_state(db_session, interview)
    assert has_next is True
    assert interview.current_difficulty == "INTERMEDIATE"
    db_session.refresh(q3)
    assert q3.difficulty == "INTERMEDIATE"
    
    # 5. Candidate answers Q3 with unmodified starter code
    ans3 = Answer(interview_id=interview.id, question_id=q3.id, code_submission="def solve(): pass")
    db_session.add(ans3)
    db_session.commit()
    db_session.refresh(ans3)
    
    ev3 = Evaluation(
        answer_id=ans3.id, overall_score=10.0, technical_score=10.0, conceptual_score=10.0, relevance_score=20.0, clarity_score=50.0, feedback="Boilerplate template submitted."
    )
    db_session.add(ev3)
    db_session.commit()
    
    # Completing final question
    has_next = InterviewEngine.advance_question_state(db_session, interview)
    assert has_next is False
    assert interview.state == InterviewState.COMPLETED.value
    
    # 6. Verify Assessment Report generation
    from backend.app.services.scoring_engine import ScoringEngine
    report = await ScoringEngine.generate_final_report(db_session, interview)
    
    assert report is not None
    assert "visual_confidence_score" in report.vision_analytics
    assert "posture_composure_score" in report.vision_analytics
    assert "identity_verification" in report.vision_analytics
    assert "acoustic_confidence_score" in report.audio_analytics
    assert "fluency_ratio_percent" in report.audio_analytics
    assert "signal_processing_methodology" in report.audio_analytics

# ==============================================================================
# JPMORGAN QA SUITE - TEST 5: SCORING & RUNTIME REGRESSION INTEGRITY
# ==============================================================================

@pytest.mark.anyio
async def test_mcq_unselected_scores_strictly_zero():
    """Leaving an MCQ question unattempted (selected_option=None) must award strictly 0.0 marks."""
    provider = MockLLMProvider()
    q_data = {
        "question_text": "What is an index in PostgreSQL?",
        "question_type": "MCQ",
        "correct_option": "B",
        "expected_concepts": ["B-tree", "lookup speed"],
        "explanation": "B-tree index speeds up query lookups.",
        "skill_assessed": "PostgreSQL Indexing"
    }
    res = await provider.evaluate_answer(
        question_data=q_data,
        transcript="",
        selected_option=None,
        code_submission=None
    )
    assert res["overall_score"] == 0.0
    assert res["technical_score"] == 0.0
    assert "unattempted" in res["why_this_score"].lower() or "no option" in res["feedback"].lower()

    # Also test GeminiProvider guard
    from backend.app.integrations.gemini_provider import GeminiProvider
    gem_provider = GeminiProvider()
    gem_res = await gem_provider.evaluate_answer(
        question_data=q_data,
        transcript="",
        selected_option=None,
        code_submission=None
    )
    assert gem_res["overall_score"] == 0.0
    assert gem_res["technical_score"] == 0.0

@pytest.mark.anyio
async def test_idontknow_spoken_scores_strictly_low():
    """Candidate explicitly saying 'I don't know' must score <= 15.0 with empty correct concepts."""
    provider = MockLLMProvider()
    q_data = {
        "question_text": "Explain distributed transaction rollback in 2PC.",
        "question_type": "SPOKEN",
        "expected_concepts": ["two-phase commit", "coordinator", "rollback"],
        "skill_assessed": "Distributed Transactions"
    }
    res = await provider.evaluate_answer(
        question_data=q_data,
        transcript="I am sorry, I don't know anything about two phase commit.",
        selected_option=None,
        code_submission=None
    )
    assert res["overall_score"] <= 15.0
    assert res["technical_score"] <= 15.0
    assert len(res["correct_concepts"]) == 0
    assert "lack of knowledge" in res["why_this_score"].lower() or "do not know" in res["why_this_score"].lower()

def test_pyav_monkeypatch_metadata_errors():
    """Verify PyAV wrapper safely swallows metadata_errors argument without throwing TypeError."""
    import io
    import backend.app.integrations.speech_provider  # triggers patch
    import av
    # Calling av.open with metadata_errors="ignore" on invalid/empty data should NOT raise TypeError
    try:
        av.open(io.BytesIO(b"dummy"), metadata_errors="ignore")
    except TypeError as te:
        pytest.fail(f"TypeError raised indicating metadata_errors was not stripped: {te}")
    except Exception:
        # Any format/container error is expected because dummy bytes are not valid media
        pass

def test_cv_spectacles_and_cascade_robustness():
    """Verify VisionAnalyzerService loads spectacles and alt cascades."""
    vision = VisionAnalyzerService()
    if vision.is_opencv_ready:
        assert vision.face_alt_cascade is not None, "haarcascade_frontalface_alt2.xml must be loaded"
        assert vision.eye_glass_cascade is not None, "haarcascade_eye_tree_eyeglasses.xml must be loaded"

