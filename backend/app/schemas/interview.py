from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class JobRoleBase(BaseModel):
    title: str
    category: str
    description: Optional[str] = None

class JobRoleCreate(JobRoleBase):
    pass

class JobRoleResponse(JobRoleBase):
    id: int
    is_custom: bool
    created_at: datetime

    class Config:
        from_attributes = True

class InterviewConfigureRequest(BaseModel):
    job_role_id: Optional[int] = None
    custom_role_title: Optional[str] = None # used if job_role_id is null
    experience_level: str # Fresher, Entry Level, Intermediate, Experienced, Senior, Lead/Manager
    difficulty: str # Easy, Medium, Hard, Expert
    type: str # HR, Technical, Behavioral, Situational, Resume-Based, Project-Based, Managerial, Mixed
    num_questions: int = Field(5, ge=1, le=25)

class InterviewQuestionResponse(BaseModel):
    id: int
    question_text: str
    difficulty: str
    order_index: int

    class Config:
        from_attributes = True

class InterviewStartResponse(BaseModel):
    interview_id: int
    job_role_title: str
    total_questions: int
    first_question: Optional[InterviewQuestionResponse] = None

class AnswerSubmitRequest(BaseModel):
    question_id: int
    answer_text: str
    response_time_seconds: Optional[int] = None

class FeedbackDetails(BaseModel):
    strengths: List[str]
    weaknesses: List[str]
    details: str

class AnswerEvaluationResponse(BaseModel):
    score: int
    relevance_score: int
    technical_score: int
    completeness_score: int
    communication_score: int
    reasoning_score: int
    star_score: int
    feedback: FeedbackDetails
    missing_concepts: List[str]
    improved_answer: Optional[str] = None

    class Config:
        from_attributes = True

class AnswerSubmitResponse(BaseModel):
    evaluation: AnswerEvaluationResponse
    next_question: Optional[InterviewQuestionResponse] = None
    is_completed: bool

class InterviewQuestionReview(BaseModel):
    id: int
    question_text: str
    expected_concepts: List[str] = []
    user_answer: Optional[str] = None
    evaluation: Optional[AnswerEvaluationResponse] = None

    class Config:
        from_attributes = True

class InterviewResultResponse(BaseModel):
    id: int
    job_role_title: str
    experience_level: str
    difficulty: str
    type: str
    num_questions: int
    overall_score: Optional[int] = None
    feedback: Optional[str] = None
    recommendations: Optional[Dict[str, Any]] = None # learning plan
    created_at: datetime
    questions_review: List[InterviewQuestionReview] = []

    class Config:
        from_attributes = True

class InterviewHistoryItem(BaseModel):
    id: int
    job_role_title: str
    experience_level: str
    difficulty: str
    type: str
    num_questions: int
    overall_score: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class PracticeConfigureRequest(BaseModel):
    job_role_id: Optional[int] = None
    topic: str
    difficulty: str
    num_questions: int = Field(3, ge=1, le=10)

class PracticeQuestionItem(BaseModel):
    index: int
    question_text: str
    topic: str
    difficulty: str
    expected_concepts: List[str] = []

class PracticeQuestionResponse(BaseModel):
    id: int
    topic: str
    difficulty: str
    num_questions: int
    questions: List[PracticeQuestionItem] = []
    question_text: Optional[str] = None # backward compatibility

class PracticeSubmitRequest(BaseModel):
    practice_id: int
    question_index: int = 0
    user_answer: str

class PracticeSubmitResponse(BaseModel):
    practice_id: int
    question_index: int
    is_completed: bool
    evaluation: Dict[str, Any]
    feedback: Optional[Dict[str, Any]] = None # backward compatibility
    all_evaluations: Optional[List[Dict[str, Any]]] = None
    overall_score: Optional[int] = None
