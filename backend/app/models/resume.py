from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    extracted_text = Column(Text, nullable=False)
    
    # Store skills, education details, projects, work experience, certifications
    extracted_info = Column(JSON, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="resumes")
    analyses = relationship("ResumeAnalysis", back_populates="resume", cascade="all, delete-orphan")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    title = Column(String(255), nullable=False)
    raw_text = Column(Text, nullable=False)
    
    # Store extracted keywords, responsibilities, skills, qualifications
    parsed_info = Column(JSON, nullable=True) 
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="job_descriptions")
    analyses = relationship("ResumeAnalysis", back_populates="job_description")


class ResumeAnalysis(Base):
    __tablename__ = "resume_analyses"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    job_description_id = Column(Integer, ForeignKey("job_descriptions.id", ondelete="SET NULL"), nullable=True)
    
    overall_score = Column(Integer, nullable=False)
    # Store category breakdowns: {skills_match, keyword_match, experience_match, education_match, formatting_score}
    category_scores = Column(JSON, nullable=False)
    # Store detailed analysis of matching keywords, missing items, suggestions
    analysis_data = Column(JSON, nullable=False)
    
    mode = Column(String(20), nullable=False) # 'general' or 'job_specific'
    created_at = Column(DateTime, default=datetime.utcnow)

    resume = relationship("Resume", back_populates="analyses")
    job_description = relationship("JobDescription", back_populates="analyses")
