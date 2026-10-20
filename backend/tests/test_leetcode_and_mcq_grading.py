import pytest
from backend.app.integrations.mock_llm_provider import MockLLMProvider
from backend.app.integrations.gemini_provider import GeminiProvider
from backend.app.services.code_runner import CodeRunnerService

@pytest.mark.anyio
async def test_wrong_mcq_answer_strictly_scores_zero_mock():
    provider = MockLLMProvider()
    q_data = {
        "question_text": "What is IoU?",
        "question_type": "MCQ",
        "correct_option": "A",
        "options": [
            {"id": "A", "text": "Intersection over Union"},
            {"id": "B", "text": "Incorrect option"},
            {"id": "C", "text": "Another incorrect option"},
            {"id": "D", "text": "Wrong answer"}
        ],
        "explanation": "Option A is correct.",
        "expected_concepts": ["IoU", "intersection", "union"],
        "skill_assessed": "Computer Vision"
    }

    # Test candidate selecting wrong option D
    eval_result = await provider.evaluate_answer(
        question_data=q_data,
        transcript="I think the answer is D because of whatever",
        selected_option="D"
    )
    assert eval_result["overall_score"] == 0.0
    assert eval_result["technical_score"] == 0.0
    assert eval_result["conceptual_score"] == 0.0
    assert "incorrect" in eval_result["why_this_score"].lower()

@pytest.mark.anyio
async def test_unattempted_mcq_scores_zero_mock():
    provider = MockLLMProvider()
    q_data = {
        "question_text": "What is IoU?",
        "question_type": "MCQ",
        "correct_option": "A",
        "options": [{"id": "A", "text": "Intersection over Union"}],
        "explanation": "Option A is correct.",
        "expected_concepts": ["IoU"],
        "skill_assessed": "Computer Vision"
    }

    # Test candidate selecting None / empty
    eval_result = await provider.evaluate_answer(
        question_data=q_data,
        transcript="",
        selected_option=None
    )
    assert eval_result["overall_score"] == 0.0
    assert eval_result["technical_score"] == 0.0

@pytest.mark.anyio
async def test_wrong_mcq_answer_strictly_scores_zero_gemini():
    provider = GeminiProvider()
    q_data = {
        "question_text": "Which interface is ASGI?",
        "question_type": "MCQ",
        "correct_option": "A",
        "options": [
            {"id": "A", "text": "Asynchronous Server Gateway Interface"},
            {"id": "B", "text": "Wrong"},
            {"id": "C", "text": "Wrong"},
            {"id": "D", "text": "Web Server Gateway Interface"}
        ],
        "explanation": "Option A is correct.",
        "expected_concepts": ["ASGI"],
        "skill_assessed": "FastAPI"
    }

    # Candidate picked Option D (as happened in the live screenshot)
    eval_result = await provider.evaluate_answer(
        question_data=q_data,
        transcript="I pick D",
        selected_option="D"
    )
    assert eval_result["overall_score"] == 0.0
    assert eval_result["technical_score"] == 0.0
    assert eval_result["conceptual_score"] == 0.0
    assert "incorrect" in eval_result["why_this_score"].lower()

def test_code_runner_service_execution():
    # Correct implementation of compute_iou
    correct_code = """
def compute_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])
    unionArea = float(boxAArea + boxBArea - interArea)

    return round(interArea / unionArea, 4) if unionArea > 0 else 0.0
"""
    test_cases = [
        {
            "name": "Partial Overlap",
            "input": "boxA=[0,0,2,2], boxB=[1,1,3,3]",
            "expected": 0.1429,
            "test_code": "actual = compute_iou([0, 0, 2, 2], [1, 1, 3, 3])"
        },
        {
            "name": "Identical Coordinates",
            "input": "boxA=[0,0,5,5], boxB=[0,0,5,5]",
            "expected": 1.0,
            "test_code": "actual = compute_iou([0, 0, 5, 5], [0, 0, 5, 5])"
        },
        {
            "name": "Disjoint",
            "input": "boxA=[0,0,1,1], boxB=[2,2,4,4]",
            "expected": 0.0,
            "test_code": "actual = compute_iou([0, 0, 1, 1], [2, 2, 4, 4])"
        }
    ]

    res = CodeRunnerService.run_code(code=correct_code, test_cases=test_cases)
    assert res["all_passed"] is True
    assert res["passed_cases"] == 3
    assert res["total_cases"] == 3

    # Incorrect implementation (always returns 0.5)
    wrong_code = """
def compute_iou(boxA, boxB):
    return 0.5
"""
    wrong_res = CodeRunnerService.run_code(code=wrong_code, test_cases=test_cases)
    assert wrong_res["all_passed"] is False
    assert wrong_res["passed_cases"] == 0

@pytest.mark.anyio
async def test_code_questions_include_leetcode_attributes():
    provider = MockLLMProvider()
    questions = await provider.generate_questions(
        profile_data={"skills": {"tech": ["PyTorch", "OpenCV"]}},
        target_role="Computer Vision Engineer",
        interview_type="technical",
        difficulty="INTERMEDIATE",
        count=3,
        assessed_topics=[],
        question_mix="coding_mcq"
    )

    code_qs = [q for q in questions if q.get("question_type") == "CODE"]
    assert len(code_qs) >= 1
    code_q = code_qs[0]
    assert "examples" in code_q
    assert len(code_q["examples"]) >= 1
    assert "input" in code_q["examples"][0]
    assert "output" in code_q["examples"][0]
    assert "constraints" in code_q
    assert len(code_q["constraints"]) >= 1
    assert "test_cases" in code_q
    assert len(code_q["test_cases"]) >= 1

def test_unimplemented_dsa_code_strictly_fails():
    starter_dsa = """
def two_sum_sorted(nums: list[int], target: int) -> list[int]:
    # ------------------------------------------------------------------
    # >>> START YOUR CODE HERE <<<
    # ------------------------------------------------------------------
    pass
"""
    test_cases = [
        {
            "name": "Standard Pair Found",
            "input": "nums=[2, 7, 11, 15], target=9",
            "expected": [0, 1],
            "test_code": "actual = two_sum_sorted([2, 7, 11, 15], 9)"
        }
    ]
    res = CodeRunnerService.run_code(code=starter_dsa, test_cases=test_cases, starter_code=starter_dsa)
    assert res["all_passed"] is False
    assert res["passed_cases"] == 0
    assert res["results"][0]["status"] == "FAILED"

def test_uncorrected_async_blocking_bug_strictly_fails():
    buggy_async_code = """
import asyncio
import time

async def fetch_user_data(user_id: int):
    time.sleep(1)
    return {"id": user_id, "status": "active"}
"""
    test_cases = [
        {
            "name": "Non-blocking Async Concurrency Check",
            "input": "fetch_user_data(1)",
            "expected": {"id": 1, "status": "active"},
            "test_code": """
import inspect
import asyncio
src = inspect.getsource(fetch_user_data)
if 'time.sleep' in src:
    raise AssertionError("Defect not resolved: Code still contains blocking synchronous 'time.sleep'. Replace with 'await asyncio.sleep'!")
actual = asyncio.run(fetch_user_data(1))
"""
        }
    ]
    res = CodeRunnerService.run_code(code=buggy_async_code, test_cases=test_cases, starter_code=buggy_async_code)
    assert res["all_passed"] is False
    assert res["passed_cases"] == 0
    assert "blocking synchronous" in res["results"][0]["actual"]

def test_corrected_async_blocking_bug_passes():
    fixed_async_code = """
import asyncio

async def fetch_user_data(user_id: int):
    await asyncio.sleep(0.01)
    return {"id": user_id, "status": "active"}
"""
    test_cases = [
        {
            "name": "Non-blocking Async Concurrency Check",
            "input": "fetch_user_data(1)",
            "expected": {"id": 1, "status": "active"},
            "test_code": """
import inspect
import asyncio
src = inspect.getsource(fetch_user_data)
if 'time.sleep' in src:
    raise AssertionError("Defect not resolved: Code still contains blocking synchronous 'time.sleep'. Replace with 'await asyncio.sleep'!")
actual = asyncio.run(fetch_user_data(1))
"""
        }
    ]
    res = CodeRunnerService.run_code(code=fixed_async_code, test_cases=test_cases)
    assert res["all_passed"] is True
    assert res["passed_cases"] == 1

def test_empty_test_cases_strictly_fails_on_unedited_template():
    starter = "def solve(*args):\n    pass\n"
    res = CodeRunnerService.run_code(code=starter, test_cases=[], starter_code=starter)
    assert res["all_passed"] is False
    assert res["passed_cases"] == 0

@pytest.mark.anyio
async def test_coding_modes_starter_comments():
    provider = MockLLMProvider()
    questions = await provider.generate_questions(
        profile_data={"skills": {"backend": ["Python", "FastAPI"]}},
        target_role="Backend Engineer",
        interview_type="technical",
        difficulty="INTERMEDIATE",
        count=6,
        assessed_topics=[],
        question_mix="coding_mcq"
    )

    code_qs = [q for q in questions if q.get("question_type") == "CODE"]
    assert len(code_qs) >= 2

    # Verify DSA question has starter comment
    dsa_qs = [q for q in code_qs if "pass" in q.get("code_snippet", "")]
    assert len(dsa_qs) >= 1
    assert ">>> START YOUR CODE HERE <<<" in dsa_qs[0]["code_snippet"]

    # Verify Correct-the-Code question does NOT have starter comment
    refactor_qs = [q for q in code_qs if "fetch_user_data" in q.get("code_snippet", "")]
    assert len(refactor_qs) >= 1
    assert ">>> START YOUR CODE HERE <<<" not in refactor_qs[0]["code_snippet"]

