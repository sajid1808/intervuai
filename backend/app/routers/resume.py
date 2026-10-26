import os
import uuid
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.models.resume import Resume, JobDescription, ResumeAnalysis
from app.schemas.resume import ResumeResponse, ResumeConfirmUpdate, AtsAnalysisRequest, AtsAnalysisResponse, JobDescriptionCreate, JobDescriptionResponse
from app.security import get_current_user
from app.services.resume_parser import parse_resume
from app.services.ats_scorer import score_ats_compatibility
from app.services.ai_client import analyze_job_description_with_llm

router = APIRouter(prefix="/resumes", tags=["Resumes & ATS"])

# Ensure uploads directory exists
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024 # 10 MB limit

def validate_uploaded_file(file: UploadFile):
    """Validate file type and size restrictions."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".doc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload PDF or Word documents (.docx, .doc)."
        )
    return True

@router.post("/upload", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    validate_uploaded_file(file)
    
    # Generate unique filename to avoid collision
    unique_filename = f"{uuid.uuid4()}_{file.filename}"
    temp_file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # Save the file locally
    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not save file: {str(e)}"
        )
        
    # Verify file size after copy
    file_size = os.path.getsize(temp_file_path)
    if file_size > MAX_FILE_SIZE:
        os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds the maximum limit of 10MB."
        )
        
    try:
        # Extract text and structure it via parser service
        parsed_data = parse_resume(temp_file_path, file.filename)
        
        # Save to Resumes table
        new_resume = Resume(
            user_id=current_user.id,
            filename=file.filename,
            file_path=temp_file_path,
            extracted_text=parsed_data["text"],
            extracted_info=parsed_data["structured_info"]
        )
        db.add(new_resume)
        db.commit()
        db.refresh(new_resume)
        
        return new_resume
    except Exception as e:
        # Cleanup file if error occurs
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error parsing resume: {str(e)}"
        )

@router.put("/{resume_id}/confirm", response_model=ResumeResponse)
def confirm_resume_details(
    resume_id: int,
    updated_data: ResumeConfirmUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    resume = db.query(Resume).filter(Resume.id == resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
        
    # Update profile fields based on confirmed fields
    info = resume.extracted_info or {}
    info.update(updated_data.dict(exclude_unset=True))
    resume.extracted_info = info
    
    # Sync this confirmed skills set to the User's Profile table
    profile = current_user.profile
    if profile:
        profile.skills = info.get("skills", [])
        # Save full name as profile name if exists
        if info.get("full_name"):
            profile.full_name = info.get("full_name")
            
    db.commit()
    db.refresh(resume)
    return resume

@router.post("/job-descriptions", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_job_description(
    jd_data: JobDescriptionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Parse description using LLM
    parsed_info = analyze_job_description_with_llm(jd_data.raw_text)
    
    new_jd = JobDescription(
        user_id=current_user.id,
        title=jd_data.title,
        raw_text=jd_data.raw_text,
        parsed_info=parsed_info
    )
    db.add(new_jd)
    db.commit()
    db.refresh(new_jd)
    return new_jd

@router.post("/analyze", response_model=AtsAnalysisResponse)
def analyze_ats_alignment(
    req: AtsAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Fetch Resume
    resume = db.query(Resume).filter(Resume.id == req.resume_id, Resume.user_id == current_user.id).first()
    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )
        
    # 2. Fetch or Parse Job Description
    jd = None
    jd_info = None
    mode = "general"
    
    if req.job_description_id:
        jd = db.query(JobDescription).filter(JobDescription.id == req.job_description_id).first()
        if not jd:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job description reference not found"
            )
        jd_info = jd.parsed_info
        mode = "job_specific"
    elif req.raw_job_description:
        # Paste mode: parse it immediately
        jd_info = analyze_job_description_with_llm(req.raw_job_description)
        # Save temporary JobDescription
        jd = JobDescription(
            user_id=current_user.id,
            title=jd_info.get("title", "Target Job Role"),
            raw_text=req.raw_job_description,
            parsed_info=jd_info
        )
        db.add(jd)
        db.commit()
        db.refresh(jd)
        mode = "job_specific"
    else:
        # General resume audit
        jd_info = {
            "title": "General Profile Audit",
            "skills": resume.extracted_info.get("skills", []) if resume.extracted_info else [],
            "qualifications": [],
            "responsibilities": []
        }
        
    # 3. Calculate scores and suggestions using ATS Scorer engine
    analysis_results = score_ats_compatibility(
        resume.extracted_text,
        resume.extracted_info or {},
        jd_info
    )
    
    # 4. Save analysis to DB
    new_analysis = ResumeAnalysis(
        resume_id=resume.id,
        job_description_id=jd.id if jd else None,
        overall_score=analysis_results["overall_score"],
        category_scores=analysis_results["category_scores"],
        analysis_data=analysis_results["analysis_data"],
        mode=mode
    )
    db.add(new_analysis)
    db.commit()
    db.refresh(new_analysis)
    
    # Update profile target role in user session if applicable
    if mode == "job_specific" and jd:
        profile = current_user.profile
        if profile and profile.preferred_roles:
            roles = profile.preferred_roles
            if jd.title not in roles:
                roles.append(jd.title)
                profile.preferred_roles = roles
                db.commit()
                
    return new_analysis
