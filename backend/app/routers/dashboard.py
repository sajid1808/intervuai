from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.resume import Resume, ResumeAnalysis
from app.models.interview import Interview, PerformanceMetrics, ProgressHistory
from app.schemas.dashboard import DashboardDataResponse, AdminStatsResponse
from app.security import get_current_user, get_current_admin

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/", response_model=DashboardDataResponse)
def get_user_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Latest ATS Score & Strength
    latest_ats_score = None
    resume_strength = None
    latest_resume = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).first()
    
    if latest_resume:
        latest_analysis = db.query(ResumeAnalysis).filter(ResumeAnalysis.resume_id == latest_resume.id).order_by(ResumeAnalysis.created_at.desc()).first()
        if latest_analysis:
            latest_ats_score = latest_analysis.overall_score
            if latest_ats_score < 60:
                resume_strength = "Weak"
            elif latest_ats_score < 75:
                resume_strength = "Average"
            elif latest_ats_score < 87:
                resume_strength = "Strong"
            else:
                resume_strength = "Excellent"
                
    # 2. Interview aggregates
    completed_interviews = db.query(Interview).filter(
        Interview.user_id == current_user.id,
        Interview.overall_score.isnot(None)
    ).order_by(Interview.created_at.desc()).all()
    
    total_completed = len(completed_interviews)
    avg_score = 0.0
    if total_completed > 0:
        avg_score = round(sum(i.overall_score for i in completed_interviews) / total_completed, 2)
        
    # 3. Target job role
    target_job_role = None
    profile = current_user.profile
    if profile and profile.preferred_roles:
        target_job_role = profile.preferred_roles[0] if len(profile.preferred_roles) > 0 else None
        
    # 4. Best/Weakest skills
    metrics = db.query(PerformanceMetrics).filter(PerformanceMetrics.user_id == current_user.id).first()
    best_skill = metrics.best_performing_skill if metrics else "Communication"
    weak_skill = metrics.weakest_skill if metrics else "System Architecture"
    
    # 5. Recent Interviews
    recent_list = []
    for idx, i in enumerate(completed_interviews[:5]):
        recent_list.append({
            "id": i.id,
            "role": i.job_role.title if i.job_role else "Custom Role",
            "score": i.overall_score,
            "date": i.created_at.strftime("%b %d, %Y"),
            "difficulty": i.difficulty,
            "type": i.type
        })
        
    # 6. Performance Trend (in chronological order for line charts)
    trend_list = []
    chronological_interviews = sorted(completed_interviews, key=lambda x: x.created_at)
    for i in chronological_interviews:
        trend_list.append({
            "date": i.created_at.strftime("%m/%d"),
            "interview_id": i.id,
            "score": i.overall_score,
            "role": i.job_role.title if i.job_role else "Custom"
        })
        
    # 7. Recommended practice topics based on weakest skill
    recommended_practice = [
        {"topic": weak_skill, "difficulty": "Medium", "description": f"Focus review on {weak_skill} based on recent evaluations."},
        {"topic": "Data Structures & Algorithms", "difficulty": "Hard", "description": "Core computer science problem solving skills."},
        {"topic": "STAR Method Behavioral", "difficulty": "Easy", "description": "Practice structuring scenario based communication."}
    ]
    
    # Welcome message formatting
    user_name = profile.full_name if profile and profile.full_name else current_user.email.split("@")[0]
    welcome_message = f"Welcome back, {user_name}! Ready to elevate your interview readiness today?"
    
    return {
        "welcome_message": welcome_message,
        "latest_ats_score": latest_ats_score,
        "resume_strength": resume_strength,
        "total_interviews": total_completed,
        "average_score": avg_score,
        "best_performing_skill": best_skill,
        "weakest_skill": weak_skill,
        "target_job_role": target_job_role,
        "recent_interviews": recent_list,
        "performance_trend": trend_list,
        "recommended_practice": recommended_practice
    }

# ----------------- ADMIN DASHBOARD METRICS -----------------

@router.get("/admin", response_model=AdminStatsResponse)
def get_admin_dashboard(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    total_users = db.query(User).count()
    total_interviews = db.query(Interview).filter(Interview.overall_score.isnot(None)).count()
    active_interviews = db.query(Interview).filter(Interview.overall_score.is_None()).count()
    total_resumes = db.query(Resume).count()
    
    # Get role distributions (which role is practiced most)
    # Perform grouping
    from sqlalchemy import func
    role_counts = db.query(
        JobRole.title, func.count(Interview.id)
    ).join(Interview, Interview.job_role_id == JobRole.id).group_by(JobRole.title).order_by(func.count(Interview.id).desc()).limit(5).all()
    
    role_dist = [{"role": r[0], "count": r[1]} for r in role_counts]
    if not role_dist:
        # Placeholder standard metrics if no interviews completed
        role_dist = [
            {"role": "Backend Developer", "count": 12},
            {"role": "Machine Learning Engineer", "count": 8},
            {"role": "UI/UX Designer", "count": 5}
        ]
        
    return {
        "total_users": total_users,
        "total_interviews": total_interviews,
        "active_interviews": active_interviews,
        "total_resumes": total_resumes,
        "role_distribution": role_dist,
        "error_count": 0,
        "recent_errors": []
    }
