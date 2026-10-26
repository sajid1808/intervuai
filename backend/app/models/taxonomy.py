from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class JobRole(Base):
    __tablename__ = "job_roles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), unique=True, index=True, nullable=False)
    category = Column(String(100), index=True, nullable=False)
    description = Column(Text, nullable=True)
    is_custom = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    interviews = relationship("Interview", back_populates="job_role")
    practice_sessions = relationship("PracticeSession", back_populates="job_role")


class Skill(Base):
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), unique=True, index=True, nullable=False)
    category = Column(String(100), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user_skills = relationship("UserSkill", back_populates="skill", cascade="all, delete-orphan")


class UserSkill(Base):
    __tablename__ = "user_skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Integer, ForeignKey("skills.id", ondelete="CASCADE"), nullable=False)
    proficiency_level = Column(String(50), default="Intermediate") # Beginner, Intermediate, Expert
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="user_skills")
    skill = relationship("Skill", back_populates="user_skills")

    __table_args__ = (
        UniqueConstraint("user_id", "skill_id", name="uq_user_skill"),
    )
