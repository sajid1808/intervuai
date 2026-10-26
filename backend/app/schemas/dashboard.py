from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class PerformanceTrendItem(BaseModel):
    date: str
    interview_id: int
    score: int
    role: str

class DashboardDataResponse(BaseModel):
    welcome_message: str
    latest_ats_score: Optional[int] = None
    resume_strength: Optional[str] = None # Weak, Average, Strong, Excellent
    total_interviews: int
    average_score: float
    best_performing_skill: Optional[str] = None
    weakest_skill: Optional[str] = None
    target_job_role: Optional[str] = None
    
    # Lists for charts & tables
    recent_interviews: List[Dict[str, Any]] = []
    performance_trend: List[PerformanceTrendItem] = []
    recommended_practice: List[Dict[str, Any]] = []

class AdminStatsResponse(BaseModel):
    total_users: int
    total_interviews: int
    active_interviews: int
    total_resumes: int
    role_distribution: List[Dict[str, Any]] = []
    error_count: int
    recent_errors: List[Dict[str, Any]] = []
