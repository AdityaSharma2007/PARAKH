import pytest
from backend.app.models.entities import (
    Interview, Resume, CandidateProfile, InterviewQuestion, Answer, Evaluation, VerificationStatus
)
from backend.app.services.evidence_graph_service import EvidenceGraphService

def test_evidence_graph_sync(db_session):
    # Setup interview with profile
    resume = Resume(
        filename="test.pdf",
        stored_path="test.pdf",
        file_hash="hash123",
        file_size_bytes=1000,
        mime_type="application/pdf"
    )
    db_session.add(resume)
    db_session.commit()

    profile = CandidateProfile(
        resume_id=resume.id,
        skills={"languages": ["FastAPI", "SQL"]},
        projects=[{"title": "E-Commerce Microservices", "technologies": ["FastAPI", "Docker"]}]
    )
    db_session.add(profile)

    interview = Interview(
        resume_id=resume.id,
        target_role="Backend Engineer",
        total_questions=2
    )
    db_session.add(interview)
    db_session.commit()

    # Add question testing FastAPI
    q1 = InterviewQuestion(
        interview_id=interview.id,
        order_index=1,
        question_text="How do you structure FastAPI endpoints?",
        skill_assessed="FastAPI"
    )
    db_session.add(q1)
    db_session.commit()

    # Add high-scoring answer
    ans1 = Answer(interview_id=interview.id, question_id=q1.id, transcript="We used async endpoints.")
    db_session.add(ans1)
    db_session.commit()

    ev1 = Evaluation(
        answer_id=ans1.id,
        overall_score=85.0,
        technical_score=85.0,
        conceptual_score=85.0,
        relevance_score=85.0,
        clarity_score=85.0,
        feedback="Excellent",
        transcript_evidence=["We used async endpoints."]
    )
    db_session.add(ev1)
    db_session.commit()

    # Sync evidence graph
    nodes = EvidenceGraphService.sync_evidence_nodes(db_session, interview)
    
    # Assert FastAPI node is VERIFIED
    fastapi_node = next(n for n in nodes if n.claim_text == "FastAPI")
    assert fastapi_node.verified_status == VerificationStatus.VERIFIED.value
    assert fastapi_node.confidence_score == 85.0
    assert fastapi_node.evidence_quote == "We used async endpoints."

    # Assert SQL node is UNVERIFIED (not yet asked)
    sql_node = next(n for n in nodes if n.claim_text == "SQL")
    assert sql_node.verified_status == VerificationStatus.UNVERIFIED.value
