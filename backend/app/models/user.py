from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, ARRAY, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("Profile", uselist=False, back_populates="user", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    job_descriptions = relationship("JobDescription", back_populates="user", cascade="all, delete-orphan")
    user_skills = relationship("UserSkill", back_populates="user", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="user", cascade="all, delete-orphan")
    performance_metrics = relationship("PerformanceMetrics", uselist=False, back_populates="user", cascade="all, delete-orphan")
    practice_sessions = relationship("PracticeSession", back_populates="user", cascade="all, delete-orphan")
    progress_history = relationship("ProgressHistory", back_populates="user", cascade="all, delete-orphan")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = Column(String(255))
    education = Column(Text)
    
    # We use a helper property to handle lists if the backend runs SQLite (SQLite does not support ARRAY type out of the box)
    # So we store skills and preferred roles as comma-separated values or JSON/Text when running SQLite, or use JSON/ARRAY.
    # To keep database portability, we can use Text and serialise as comma-separated or use sqlalchemy.types.JSON.
    # Let's use sqlalchemy.types.JSON or simple JSON/JSONB which works perfectly on both SQLite and PostgreSQL!
    # JSON is extremely standard in SQLAlchemy and works out-of-the-box on SQLite and PostgreSQL.
    skills_json = Column(Text, default="[]") 
    preferred_roles_json = Column(Text, default="[]")
    
    experience_level = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")

    @property
    def skills(self):
        import json
        try:
            return json.loads(self.skills_json or "[]")
        except Exception:
            return []

    @skills.setter
    def skills(self, value):
        import json
        self.skills_json = json.dumps(value or [])

    @property
    def preferred_roles(self):
        import json
        try:
            return json.loads(self.preferred_roles_json or "[]")
        except Exception:
            return []

    @preferred_roles.setter
    def preferred_roles(self, value):
        import json
        self.preferred_roles_json = json.dumps(value or [])
