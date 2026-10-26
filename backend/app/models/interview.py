from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Numeric, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_role_id = Column(Integer, ForeignKey("job_roles.id", ondelete="SET NULL"), nullable=True)
    
    experience_level = Column(String(50), nullable=False)
    difficulty = Column(String(50), nullable=False)
    type = Column(String(50), nullable=False) # HR, Technical, Behavioral, Mixed, Resume-based
    num_questions = Column(Integer, nullable=False)
    
    overall_score = Column(Integer, nullable=True)
    feedback = Column(Text, nullable=True)
    
    # Store prepared preparation plan / recommendations
    recommendations = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="interviews")
    job_role = relationship("JobRole", back_populates="interviews")
    questions = relationship("InterviewQuestion", back_populates="interview", cascade="all, delete-orphan")
    progress_history = relationship("ProgressHistory", back_populates="interview", cascade="all, delete-orphan")


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    
    # List of expected keywords or key concepts
    expected_concepts = Column(JSON, nullable=True)
    difficulty = Column(String(50), nullable=False)
    order_index = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    interview = relationship("Interview", back_populates="questions")
    answer = relationship("Answer", uselist=False, back_populates="question", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("interview_questions.id", ondelete="CASCADE"), unique=True, nullable=False)
    answer_text = Column(Text, nullable=False)
    response_time_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    question = relationship("InterviewQuestion", back_populates="answer")
    evaluation = relationship("AnswerEvaluation", uselist=False, back_populates="answer", cascade="all, delete-orphan")


class AnswerEvaluation(Base):
    __tablename__ = "answer_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    answer_id = Column(Integer, ForeignKey("answers.id", ondelete="CASCADE"), unique=True, nullable=False)
    
    score = Column(Integer, nullable=False)
    relevance_score = Column(Integer, nullable=False)
    technical_score = Column(Integer, nullable=False)
    completeness_score = Column(Integer, nullable=False)
    communication_score = Column(Integer, nullable=False)
    reasoning_score = Column(Integer, nullable=False)
    star_score = Column(Integer, nullable=False) # 0 if not behavioral, otherwise 0-100 rating Situation-Task-Action-Result structure
    
    # Store feedback object: {strengths: [], weaknesses: [], details: ""}
    feedback = Column(JSON, nullable=False)
    # Store missing concepts / keywords
    missing_concepts = Column(JSON, nullable=False)
    improved_answer = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    answer = relationship("Answer", back_populates="evaluation")


class PerformanceMetrics(Base):
    __tablename__ = "performance_metrics"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_interviews = Column(Integer, default=0)
    average_score = Column(Numeric(5, 2), default=0.00)
    best_performing_skill = Column(String(150), nullable=True)
    weakest_skill = Column(String(150), nullable=True)
    
    # Store dynamic categories / trends over time
    metrics_data = Column(JSON, nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="performance_metrics")


class PracticeSession(Base):
    __tablename__ = "practice_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_role_id = Column(Integer, ForeignKey("job_roles.id", ondelete="SET NULL"), nullable=True)
    
    topic = Column(String(150), nullable=False)
    difficulty = Column(String(50), nullable=False)
    question_text = Column(Text, nullable=False)
    user_answer = Column(Text, nullable=True)
    
    # Store evaluations and scores
    feedback = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    num_questions = Column(Integer, default=1)
    questions_data = Column(JSON, nullable=True)
    answers_data = Column(JSON, nullable=True)

    user = relationship("User", back_populates="practice_sessions")
    job_role = relationship("JobRole", back_populates="practice_sessions")


class ProgressHistory(Base):
    __tablename__ = "progress_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    interview_id = Column(Integer, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow)
    overall_score = Column(Integer, nullable=False)
    
    # Store competencies breakdowns: {technical, communication, relevance, completeness, reasoning, STAR}
    competencies_scores = Column(JSON, nullable=False)

    user = relationship("User", back_populates="progress_history")
    interview = relationship("Interview", back_populates="progress_history")
