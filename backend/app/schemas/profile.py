from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class ProjectSchema(BaseModel):
    title: str = Field(..., description="Project name or title")
    description: str = Field(..., description="Summary of the project")
    technologies: List[str] = Field(default_factory=list, description="Tech stack used")
    role: Optional[str] = Field(None, description="Role in the project")
    architecture: Optional[str] = Field(None, description="Architectural style (Microservices, Monolith, etc.)")
    metrics: Optional[str] = Field(None, description="Quantified performance or impact metrics")
    highlights: List[str] = Field(default_factory=list, description="Key accomplishments or features")

class EducationSchema(BaseModel):
    degree: str
    institution: str
    year: Optional[str] = None
    field_of_study: Optional[str] = None

class ExperienceSchema(BaseModel):
    company: str
    role: str
    duration: Optional[str] = None
    highlights: List[str] = Field(default_factory=list)

class CandidateProfileBase(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_links: Dict[str, Optional[str]] = Field(default_factory=dict)
    education: List[EducationSchema] = Field(default_factory=list)
    skills: Dict[str, List[str]] = Field(default_factory=dict) # e.g. {"languages": ["Python", "JS"], "frameworks": ["FastAPI"]}
    projects: List[ProjectSchema] = Field(default_factory=list)
    experience: List[ExperienceSchema] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    ats_score: float = 0.0
    ats_breakdown: Dict[str, Any] = Field(default_factory=dict)
    cv_improvement_tips: List[str] = Field(default_factory=list)
    skill_depth_matrix: Dict[str, Any] = Field(default_factory=dict)

class CandidateProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    contact_links: Optional[Dict[str, str]] = None
    education: Optional[List[EducationSchema]] = None
    skills: Optional[Dict[str, List[str]]] = None
    projects: Optional[List[ProjectSchema]] = None
    experience: Optional[List[ExperienceSchema]] = None
    certifications: Optional[List[str]] = None

class CandidateProfileResponse(CandidateProfileBase):
    id: int
    resume_id: int
    skill_gap_analysis: Dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime

    class Config:
        from_attributes = True

class ResumeUploadResponse(BaseModel):
    resume_id: int
    filename: str
    file_size_bytes: int
    uploaded_at: datetime
    profile: CandidateProfileResponse
