import pytest
import asyncio
from backend.app.integrations.mock_llm_provider import MockLLMProvider

def test_mock_llm_multimodal_question_generation():
    provider = MockLLMProvider()
    profile_data = {
        "full_name": "Test Candidate",
        "skills": {"languages": ["Python", "JavaScript"], "frameworks": ["FastAPI", "React"]},
        "projects": [{
            "title": "Cloud Broker",
            "architecture": "Event-Driven Microservices",
            "metrics": "reduced latency by 40%",
            "technologies": ["Python", "FastAPI"]
        }]
    }

    # 1. Mixed mode: should contain SPOKEN, MCQ, and CODE
    questions = asyncio.run(provider.generate_questions(
        profile_data=profile_data,
        target_role="Full Stack Engineer",
        interview_type="mixed",
        difficulty="INTERMEDIATE",
        count=5,
        assessed_topics=[],
        question_mix="mixed"
    ))

    types = [q.get("question_type") for q in questions]
    assert "SPOKEN" in types
    assert "MCQ" in types
    assert "CODE" in types

    mcq_q = next(q for q in questions if q.get("question_type") == "MCQ")
    assert len(mcq_q.get("options", [])) == 4
    assert mcq_q.get("correct_option") is not None
    assert mcq_q.get("explanation") is not None

    code_q = next(q for q in questions if q.get("question_type") == "CODE")
    assert code_q.get("code_snippet") is not None
    assert code_q.get("language") == "python"

def test_mock_llm_mcq_evaluation():
    provider = MockLLMProvider()
    mcq_data = {
        "question_text": "What does async/await do?",
        "question_type": "MCQ",
        "correct_option": "B",
        "explanation": "Event loop yields execution to other tasks.",
        "expected_concepts": ["event loop", "non-blocking", "cooperative"]
    }

    # Correct option with reasoning
    eval_res = asyncio.run(provider.evaluate_answer(
        question_data=mcq_data,
        transcript="The event loop is non-blocking and enables cooperative multitasking.",
        selected_option="B"
    ))
    assert eval_res["overall_score"] >= 80.0
    assert "Correctly selected Option B" in eval_res["why_this_score"]

    # Incorrect option
    eval_wrong = asyncio.run(provider.evaluate_answer(
        question_data=mcq_data,
        transcript="It creates a new OS thread.",
        selected_option="A"
    ))
    assert eval_wrong["overall_score"] <= 60.0
    assert "Option A is incorrect" in eval_wrong["why_this_score"]

def test_mock_llm_code_evaluation():
    provider = MockLLMProvider()
    code_data = {
        "question_text": "Optimize token frequency count to O(N)",
        "question_type": "CODE",
        "expected_concepts": ["O(N) time complexity", "hash map / dict counting"]
    }

    code_solution = (
        "def find_first_unique_token_optimized(tokens: list[str]) -> str | None:\n"
        "    counts = {}\n"
        "    for t in tokens:\n"
        "        counts[t] = counts.get(t, 0) + 1\n"
        "    for t in tokens:\n"
        "        if counts[t] == 1:\n"
        "            return t\n"
        "    return None\n"
    )

    eval_code = asyncio.run(provider.evaluate_answer(
        question_data=code_data,
        transcript="I utilized a hash map for linear O(N) frequency counting with a two pass scan.",
        code_submission=code_solution
    ))

    assert eval_code["overall_score"] >= 80.0
    assert "hash-based linear optimization" in eval_code["feedback"].lower()

def test_mock_llm_spoken_uncertainty_evaluation():
    provider = MockLLMProvider()
    spoken_data = {
        "question_text": "Describe how you handle distributed locks with Redis and Redlock.",
        "question_type": "SPOKEN",
        "skill_assessed": "Distributed Systems",
        "expected_concepts": ["Redlock algorithm", "clock drift", "TTL expiry", "fencing tokens"]
    }

    # Test 1: Explicit "I don't know"
    eval_dont_know = asyncio.run(provider.evaluate_answer(
        question_data=spoken_data,
        transcript="Sorry, I don't know about this."
    ))
    assert eval_dont_know["overall_score"] <= 20.0
    assert eval_dont_know["overall_score"] >= 10.0
    assert len(eval_dont_know["correct_concepts"]) == 0
    assert "explicitly indicated they do not know" in eval_dont_know["why_this_score"].lower()
    assert "first principles" in eval_dont_know["feedback"].lower()

    # Test 2: Another variation of uncertainty
    eval_not_sure = asyncio.run(provider.evaluate_answer(
        question_data=spoken_data,
        transcript="Honestly I have no idea and haven't worked with Redlock before."
    ))
    assert eval_not_sure["overall_score"] <= 20.0
    assert eval_not_sure["overall_score"] >= 10.0

    # Test 3: Off-topic / zero concepts covered
    eval_irrelevant = asyncio.run(provider.evaluate_answer(
        question_data=spoken_data,
        transcript="Well computers are very interesting and the weather today is quite pleasant so everything is fine."
    ))
    assert eval_irrelevant["overall_score"] <= 35.0
    assert "did not address" in eval_irrelevant["feedback"].lower()

    # Test 4: Strong answer covering expected concepts
    eval_strong = asyncio.run(provider.evaluate_answer(
        question_data=spoken_data,
        transcript="We use the Redlock algorithm across multiple master nodes with TTL expiry and fencing tokens to prevent clock drift issues."
    ))
    assert eval_strong["overall_score"] >= 80.0
    assert len(eval_strong["correct_concepts"]) >= 3

def test_mock_llm_mcq_uncertainty_not_awarded_90():
    provider = MockLLMProvider()
    mcq_data = {
        "question_text": "What does async/await do?",
        "question_type": "MCQ",
        "correct_option": "B",
        "explanation": "Event loop yields execution to other tasks.",
        "expected_concepts": ["event loop", "non-blocking", "cooperative"]
    }

    # Candidate clicked B (correct), but said "Sorry, I don't know."
    eval_guess = asyncio.run(provider.evaluate_answer(
        question_data=mcq_data,
        transcript="Sorry, I don't know.",
        selected_option="B"
    ))
    # Must NOT give 90! Must be capped at 25
    assert eval_guess["overall_score"] <= 25.0
    assert len(eval_guess["correct_concepts"]) == 0
    assert "ungrounded guess" in eval_guess["why_this_score"].lower() or "lack of knowledge" in eval_guess["why_this_score"].lower()

def test_mock_llm_code_starter_template_not_awarded_90():
    provider = MockLLMProvider()
    starter_code = (
        "def find_first_unique_token(tokens: list[str]) -> str | None:\n"
        "    # Current implementation is quadratic O(N^2)\n"
        "    for token in tokens:\n"
        "        if tokens.count(token) == 1:\n"
        "            return token\n"
        "    return None\n\n"
        "# TODO: Refactor to O(N) linear time using a hash map\n"
        "def find_first_unique_token_optimized(tokens: list[str]) -> str | None:\n"
        "    pass\n"
    )
    code_data = {
        "question_text": "Optimize token frequency count to O(N)",
        "question_type": "CODE",
        "code_snippet": starter_code,
        "expected_concepts": ["O(N) time complexity", "hash map / dict counting"]
    }

    # Candidate submits without writing code
    eval_unattempted = asyncio.run(provider.evaluate_answer(
        question_data=code_data,
        transcript="",
        code_submission=starter_code
    ))
    # Must NOT give 90! Must be <= 20
    assert eval_unattempted["overall_score"] <= 20.0
    assert len(eval_unattempted["correct_concepts"]) == 0
    assert "unimplemented" in eval_unattempted["why_this_score"].lower() or "starter template" in eval_unattempted["feedback"].lower()

def test_mock_llm_dynamic_consistency_not_hardcoded():
    provider = MockLLMProvider()
    low_evals = [
        {"question_id": 1, "overall_score": 18.0},
        {"question_id": 2, "overall_score": 25.0},
        {"question_id": 3, "overall_score": 20.0}
    ]
    checks = asyncio.run(provider.check_knowledge_consistency(low_evals))
    assert len(checks) > 0
    # Consistency score must NOT be 0.90!
    assert checks[0]["consistency_score"] <= 0.30
    assert "struggled" in checks[0]["discrepancy_details"].lower()


