import pytest
import asyncio
from backend.app.services.resume_parser import ResumeParser
from backend.app.services.resume_analyzer import ResumeAnalyzer

SAMPLE_RICH_CV = """
Alex Morgan
Email: alex.morgan@example.com
Phone: +1 (555) 234-5678
LinkedIn: https://linkedin.com/in/alexmorgan-dev
GitHub: https://github.com/alexmorgan-dev

PROFESSIONAL SUMMARY
Senior Full Stack Engineer with 4+ years of experience architecting distributed cloud systems and real-time APIs.

TECHNICAL SKILLS
Languages: Python, JavaScript, TypeScript, SQL, Bash
Frameworks: FastAPI, Django, React, Next.js, Node.js
Databases: PostgreSQL, Redis, MongoDB, SQLite
DevOps & Cloud: Docker, Kubernetes, AWS, GitHub Actions, Linux
Architecture: Microservices, REST APIs, WebSockets, Celery

PROJECTS
High-Throughput Order Engine | Microservices
- Architected asynchronous event-driven payment and order microservices using FastAPI and Redis.
- Reduced end-to-end API latency by 45% under 12,000 RPS peak concurrency.
- Deployed on AWS Kubernetes with automated GitHub Actions CI/CD pipelines.

PARAKH Evaluation Engine | Distributed System
- Engineered multimodal interview evaluation engine integrating speech transcription and LLMs.
- Built interactive SQLite persistence layer processing 25,000 queries per second.
- Reduced memory overhead by 30% through connection pooling.

WORK EXPERIENCE
Software Engineer | Acme Cloud Corp (2022 - Present)
- Engineered backend REST APIs in Python and PostgreSQL.
- Optimized slow relational database queries, improving dashboard load times by 50%.

EDUCATION
Bachelor of Science in Computer Science
State University, 2021
"""

def test_resume_parser_contact_and_sections():
    contacts = ResumeParser.extract_contact_info(SAMPLE_RICH_CV)
    assert contacts["email"] == "alex.morgan@example.com"
    assert contacts["phone"] == "+1 (555) 234-5678"
    assert contacts["linkedin"] == "https://linkedin.com/in/alexmorgan-dev"
    assert contacts["github"] == "https://github.com/alexmorgan-dev"

    sections = ResumeParser.segment_sections(SAMPLE_RICH_CV)
    assert "SUMMARY" in sections
    assert "SKILLS" in sections
    assert "PROJECTS" in sections
    assert "EXPERIENCE" in sections
    assert "EDUCATION" in sections

def test_resume_analyzer_ats_and_deep_projects():
    analyzer = ResumeAnalyzer()
    profile = asyncio.run(analyzer.analyze_text(SAMPLE_RICH_CV))

    # ATS score validation
    assert profile["ats_score"] >= 80.0
    ats_breakdown = profile["ats_breakdown"]
    assert ats_breakdown["contact_score"] >= 14.0
    assert ats_breakdown["section_score"] >= 20.0
    assert ats_breakdown["metrics_score"] >= 14.0

    # Project architecture and metrics
    projects = profile["projects"]
    assert len(projects) >= 2
    proj1 = projects[0]
    assert "Order Engine" in proj1["title"] or "FastAPI" in proj1["description"] or len(proj1["technologies"]) > 0
    assert proj1.get("metrics") is not None
    assert ("%" in proj1.get("metrics", "") or "RPS" in proj1.get("metrics", "") or "45%" in str(proj1["highlights"]))

    # Skill depth matrix
    depth = profile["skill_depth_matrix"]
    assert "languages" in depth
    assert any(s["skill"] == "Python" for s in depth["languages"])

    # Improvement tips
    tips = profile["cv_improvement_tips"]
    assert isinstance(tips, list)
