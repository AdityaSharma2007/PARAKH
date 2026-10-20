import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from backend.app.db.database import get_db
from backend.app.core.config import settings
from backend.app.core.security import (
    validate_resume_file, generate_secure_filename, compute_file_hash
)
from backend.app.core.exceptions import EntityNotFoundError
from backend.app.models.entities import Resume, CandidateProfile, Candidate
from backend.app.schemas.profile import (
    ResumeUploadResponse, CandidateProfileResponse, CandidateProfileUpdate
)
from backend.app.services.resume_parser import ResumeParser
from backend.app.services.resume_analyzer import ResumeAnalyzer

router = APIRouter(prefix="/resumes", tags=["Resumes & Profiles"])

@router.post("/upload", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    validate_resume_file(file.filename or "resume.pdf", content, file.content_type)
    
    file_hash = compute_file_hash(content)
    secure_name = generate_secure_filename(file.filename or "resume.pdf")
    destination_path = settings.RESUME_DIR / secure_name

    with open(destination_path, "wb") as f:
        f.write(content)

    # Parse resume text
    raw_text = ResumeParser.parse_file(destination_path)

    # Analyze with LLM
    analyzer = ResumeAnalyzer()
    profile_data = await analyzer.analyze_text(raw_text)

    # Ensure candidate exists
    candidate_name = profile_data.get("full_name") or "Anonymous Candidate"
    candidate_email = profile_data.get("email")
    
    candidate = None
    if candidate_email:
        candidate = db.query(Candidate).filter_by(email=candidate_email).first()
    if not candidate:
        candidate = Candidate(full_name=candidate_name, email=candidate_email)
        db.add(candidate)
        db.commit()
        db.refresh(candidate)

    # Create Resume entity
    resume = Resume(
        candidate_id=candidate.id,
        filename=file.filename or "resume.pdf",
        stored_path=str(destination_path),
        file_hash=file_hash,
        file_size_bytes=len(content),
        mime_type=file.content_type or "application/octet-stream"
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # Create Profile entity
    profile = CandidateProfile(
        resume_id=resume.id,
        full_name=candidate_name,
        email=candidate_email,
        phone=profile_data.get("phone"),
        contact_links=profile_data.get("contact_links", {}),
        education=profile_data.get("education", []),
        skills=profile_data.get("skills", {}),
        projects=profile_data.get("projects", []),
        experience=profile_data.get("experience", []),
        certifications=profile_data.get("certifications", []),
        raw_text=raw_text[:12000],
        skill_gap_analysis=profile_data.get("skill_gap_analysis", {}),
        ats_score=profile_data.get("ats_score", 0.0),
        ats_breakdown=profile_data.get("ats_breakdown", {}),
        cv_improvement_tips=profile_data.get("cv_improvement_tips", []),
        skill_depth_matrix=profile_data.get("skill_depth_matrix", {})
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)

    return ResumeUploadResponse(
        resume_id=resume.id,
        filename=resume.filename,
        file_size_bytes=resume.file_size_bytes,
        uploaded_at=resume.uploaded_at,
        profile=CandidateProfileResponse.from_orm(profile)
    )

@router.get("/{resume_id}/profile", response_model=CandidateProfileResponse)
def get_resume_profile(resume_id: int, db: Session = Depends(get_db)):
    profile = db.query(CandidateProfile).filter_by(resume_id=resume_id).first()
    if not profile:
        raise EntityNotFoundError("CandidateProfile", resume_id)
    return CandidateProfileResponse.from_orm(profile)

@router.patch("/{resume_id}/profile", response_model=CandidateProfileResponse)
def update_resume_profile(
    resume_id: int,
    update_data: CandidateProfileUpdate,
    db: Session = Depends(get_db)
):
    profile = db.query(CandidateProfile).filter_by(resume_id=resume_id).first()
    if not profile:
        raise EntityNotFoundError("CandidateProfile", resume_id)

    if update_data.full_name is not None:
        profile.full_name = update_data.full_name
    if update_data.email is not None:
        profile.email = update_data.email
    if update_data.phone is not None:
        profile.phone = update_data.phone
    if update_data.education is not None:
        profile.education = [e.dict() for e in update_data.education]
    if update_data.skills is not None:
        profile.skills = update_data.skills
    if update_data.projects is not None:
        profile.projects = [p.dict() for p in update_data.projects]
    if update_data.experience is not None:
        profile.experience = [exp.dict() for exp in update_data.experience]
    if update_data.certifications is not None:
        profile.certifications = update_data.certifications

    db.commit()
    db.refresh(profile)
    return CandidateProfileResponse.from_orm(profile)

@router.delete("/{resume_id}")
def delete_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.query(Resume).filter_by(id=resume_id).first()
    if not resume:
        raise EntityNotFoundError("Resume", resume_id)
    
    # Safely remove stored file
    try:
        path = settings.RESUME_DIR / resume.stored_path
        if path.exists():
            path.unlink()
    except Exception:
        pass

    db.delete(resume)
    db.commit()
    return {"message": f"Resume {resume_id} and associated data successfully deleted."}
