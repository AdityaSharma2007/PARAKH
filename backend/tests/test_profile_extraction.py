import asyncio
import pytest
from backend.app.services.resume_analyzer import ResumeAnalyzer

def test_resume_analyzer_text():
    analyzer = ResumeAnalyzer()
    raw = "Candidate: Alice Smith. Email: alice@example.com. Skills: Python, FastAPI, Docker, SQL."
    
    result = asyncio.run(analyzer.analyze_text(raw))
    assert result["email"] == "alice@example.com"
    assert "skill_gap_analysis" in result
    assert "Full Stack Engineer" in result["skill_gap_analysis"]
    assert "Python Backend Engineer" in result["skill_gap_analysis"]
