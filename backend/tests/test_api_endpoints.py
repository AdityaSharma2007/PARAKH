import io
import pytest
try:
    import pymupdf as fitz
except ImportError:
    import fitz

def test_full_candidate_interview_workflow(client):
    # 1. Health check
    res = client.get("/api/health/ready")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"

    # 2. Public settings check
    res = client.get("/api/settings/public")
    assert res.status_code == 200
    assert "app_name" in res.json()

    # 3. Create a dummy PDF in memory
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Dev Candidate\nEmail: dev@example.com\nSkills: Python, FastAPI, Docker, SQL\nProjects: High-Load API")
    pdf_bytes = doc.tobytes()
    doc.close()

    # 4. Upload resume
    upload_res = client.post(
        "/api/resumes/upload",
        files={"file": ("resume.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    )
    assert upload_res.status_code == 200
    resume_data = upload_res.json()
    resume_id = resume_data["resume_id"]
    assert resume_id is not None
    assert "profile" in resume_data

    # 5. Get and edit profile
    profile_res = client.get(f"/api/resumes/{resume_id}/profile")
    assert profile_res.status_code == 200

    patch_res = client.patch(
        f"/api/resumes/{resume_id}/profile",
        json={"full_name": "Dev Candidate Updated", "skills": {"languages": ["Python", "FastAPI", "PostgreSQL"]}}
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["full_name"] == "Dev Candidate Updated"

    # 6. Create interview
    interview_res = client.post(
        "/api/interviews",
        json={
            "resume_id": resume_id,
            "target_role": "Python Backend Engineer",
            "interview_type": "technical",
            "initial_difficulty": "INTERMEDIATE",
            "total_questions": 3
        }
    )
    assert interview_res.status_code == 200
    interview = interview_res.json()
    interview_id = interview["id"]
    assert len(interview["questions"]) >= 3

    # 7. Start interview
    start_res = client.post(f"/api/interviews/{interview_id}/start")
    assert start_res.status_code == 200
    assert start_res.json()["state"] == "IN_PROGRESS"

    # 8. Fetch current question
    q_res = client.get(f"/api/interviews/{interview_id}/current-question")
    assert q_res.status_code == 200
    question = q_res.json()
    assert question["order_index"] == 1

    # 9. Submit spoken answer audio
    dummy_audio = b"RIFF....WAVEfmt ...."
    submit_res = client.post(
        f"/api/interviews/{interview_id}/answers/audio",
        data={"question_id": question["id"], "duration_seconds": 12.5},
        files={"audio_file": ("answer.webm", io.BytesIO(dummy_audio), "audio/webm")}
    )
    assert submit_res.status_code == 200
    submit_data = submit_res.json()
    assert submit_data["overall_score"] > 0
    assert submit_data["transcript"] != ""

    # 10. Conclude interview early
    end_res = client.post(f"/api/interviews/{interview_id}/end")
    assert end_res.status_code == 200
    assert end_res.json()["state"] == "COMPLETED"

    # 11. Fetch final assessment report
    report_res = client.get(f"/api/interviews/{interview_id}/report")
    assert report_res.status_code == 200
    report = report_res.json()
    assert report["overall_score"] > 0
    assert "knowledge_gap_map" in report

    # 12. Fetch evidence graph
    eg_res = client.get(f"/api/interviews/{interview_id}/evidence-graph")
    assert eg_res.status_code == 200
    assert "nodes" in eg_res.json()

    # 13. Fetch analytics progress
    analytics_res = client.get("/api/analytics/progress")
    assert analytics_res.status_code == 200
    assert analytics_res.json()["total_interviews"] >= 1

    # 14. Delete completed interview (validates cascade deletion with questions, answers, evaluations, evidence nodes & report)
    delete_res = client.delete(f"/api/interviews/{interview_id}")
    assert delete_res.status_code == 200
    assert f"Interview {interview_id} successfully deleted" in delete_res.json()["message"]

    # Verify interview is gone
    get_res = client.get(f"/api/interviews/{interview_id}")
    assert get_res.status_code == 404
