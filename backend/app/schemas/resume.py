from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class ResumeBase(BaseModel):
    filename: str

class ResumeResponse(ResumeBase):
    id: int
    user_id: int
    file_path: str
    extracted_info: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ResumeConfirmUpdate(BaseModel):
    # Allows user to edit/confirm the parsed fields
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    education: List[Dict[str, Any]] = []
    skills: List[str] = []
    experience: List[Dict[str, Any]] = []
    projects: List[Dict[str, Any]] = []
    certifications: List[str] = []

class JobDescriptionCreate(BaseModel):
    title: str
    raw_text: str

class JobDescriptionResponse(BaseModel):
    id: int
    title: str
    raw_text: str
    parsed_info: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True

class AtsAnalysisRequest(BaseModel):
    resume_id: int
    job_description_id: Optional[int] = None
    raw_job_description: Optional[str] = None # alternative if not pre-saved

class CategoryScores(BaseModel):
    skills_match: int
    keyword_match: int
    experience_match: int
    education_match: int
    formatting_score: int

class AtsAnalysisResponse(BaseModel):
    id: int
    resume_id: int
    job_description_id: Optional[int] = None
    overall_score: int
    category_scores: CategoryScores
    analysis_data: Dict[str, Any] # lists of matches, critical missing, suggestions
    mode: str
    created_at: datetime

    class Config:
        from_attributes = True
