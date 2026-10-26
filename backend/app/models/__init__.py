from app.database import Base
from app.models.user import User, Profile
from app.models.resume import Resume, JobDescription, ResumeAnalysis
from app.models.taxonomy import JobRole, Skill, UserSkill
from app.models.interview import (
    Interview,
    InterviewQuestion,
    Answer,
    AnswerEvaluation,
    PerformanceMetrics,
    PracticeSession,
    ProgressHistory
)

# Export all models for easier imports and database initialization
__all__ = [
    "Base",
    "User",
    "Profile",
    "Resume",
    "JobDescription",
    "ResumeAnalysis",
    "JobRole",
    "Skill",
    "UserSkill",
    "Interview",
    "InterviewQuestion",
    "Answer",
    "AnswerEvaluation",
    "PerformanceMetrics",
    "PracticeSession",
    "ProgressHistory"
]
