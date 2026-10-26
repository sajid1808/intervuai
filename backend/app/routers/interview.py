from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import json

from app.database import get_db
from app.models.user import User
from app.models.taxonomy import JobRole, Skill, UserSkill
from app.models.resume import Resume
from app.models.interview import (
    Interview,
    InterviewQuestion,
    Answer,
    AnswerEvaluation,
    PerformanceMetrics,
    PracticeSession,
    ProgressHistory
)
from app.schemas.interview import (
    JobRoleResponse,
    JobRoleCreate,
    InterviewConfigureRequest,
    InterviewStartResponse,
    InterviewQuestionResponse,
    AnswerSubmitRequest,
    AnswerSubmitResponse,
    InterviewResultResponse,
    InterviewHistoryItem,
    PracticeConfigureRequest,
    PracticeQuestionResponse,
    PracticeSubmitRequest,
    PracticeSubmitResponse
)
from app.security import get_current_user
from app.services.ai_client import (
    generate_questions_with_llm,
    evaluate_answer_with_llm,
    generate_prep_plan_with_llm,
    generate_practice_question_with_llm,
    generate_practice_questions_with_llm
)

router = APIRouter(prefix="/interviews", tags=["Interviews & Practice"])

# ----------------- JOB ROLES ENDPOINTS -----------------

@router.get("/roles", response_model=List[JobRoleResponse])
def get_job_roles(
    category: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(JobRole)
    if category:
        query = query.filter(JobRole.category == category)
    if search:
        query = query.filter(JobRole.title.ilike(f"%{search}%"))
    return query.all()

@router.post("/roles/custom", response_model=JobRoleResponse, status_code=status.HTTP_201_CREATED)
def create_custom_job_role(
    role_data: JobRoleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check if role title already exists
    existing = db.query(JobRole).filter(JobRole.title.ilike(role_data.title)).first()
    if existing:
        return existing
        
    custom_role = JobRole(
        title=role_data.title,
        category=role_data.category or "Custom",
        description=role_data.description or f"Custom job role entered by candidate for interview preparation.",
        is_custom=True
    )
    db.add(custom_role)
    db.commit()
    db.refresh(custom_role)
    return custom_role

# ----------------- MOCK INTERVIEW CORE FLOW -----------------

@router.post("/configure", response_model=InterviewStartResponse)
def configure_interview(
    req: InterviewConfigureRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Resolve Job Role
    job_role = None
    role_title = ""
    
    if req.job_role_id:
        job_role = db.query(JobRole).filter(JobRole.id == req.job_role_id).first()
        if not job_role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Selected Job Role not found"
            )
        role_title = job_role.title
    elif req.custom_role_title:
        # Check if already exists, else create custom
        existing = db.query(JobRole).filter(JobRole.title.ilike(req.custom_role_title)).first()
        if existing:
            job_role = existing
        else:
            job_role = JobRole(
                title=req.custom_role_title,
                category="Custom",
                description="Custom target role entered during configuration.",
                is_custom=True
            )
            db.add(job_role)
            db.commit()
            db.refresh(job_role)
        role_title = job_role.title
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either job_role_id or custom_role_title must be provided"
        )
        
    # 2. Get Resume Context if present
    resume_context = None
    latest_resume = db.query(Resume).filter(Resume.user_id == current_user.id).order_by(Resume.created_at.desc()).first()
    if latest_resume:
        resume_context = latest_resume.extracted_info
        
    # 3. Call AI question generator
    ai_questions = generate_questions_with_llm(
        role=role_title,
        experience_level=req.experience_level,
        difficulty=req.difficulty,
        interview_type=req.type,
        resume_info=resume_context,
        num_questions=req.num_questions
    )
    
    # 4. Save Interview
    new_interview = Interview(
        user_id=current_user.id,
        job_role_id=job_role.id,
        experience_level=req.experience_level,
        difficulty=req.difficulty,
        type=req.type,
        num_questions=req.num_questions
    )
    db.add(new_interview)
    db.commit()
    db.refresh(new_interview)
    
    # 5. Save Questions
    first_question = None
    for index, q_data in enumerate(ai_questions):
        question = InterviewQuestion(
            interview_id=new_interview.id,
            question_text=q_data["question_text"],
            expected_concepts=q_data.get("expected_concepts", []),
            difficulty=q_data.get("difficulty", req.difficulty),
            order_index=index + 1
        )
        db.add(question)
        if index == 0:
            first_question = question
            
    db.commit()
    
    # Return starting payload
    return {
        "interview_id": new_interview.id,
        "job_role_title": role_title,
        "total_questions": req.num_questions,
        "first_question": {
            "id": first_question.id if first_question else 0,
            "question_text": first_question.question_text if first_question else "",
            "difficulty": first_question.difficulty if first_question else req.difficulty,
            "order_index": 1
        } if first_question else None
    }

@router.post("/{interview_id}/answers", response_model=AnswerSubmitResponse)
def submit_answer(
    interview_id: int,
    req: AnswerSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Fetch Interview & Question
    interview = db.query(Interview).filter(Interview.id == interview_id, Interview.user_id == current_user.id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
        
    question = db.query(InterviewQuestion).filter(InterviewQuestion.id == req.question_id, InterviewQuestion.interview_id == interview.id).first()
    if not question:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Question not found")
        
    # Check if answer already submitted
    existing_answer = db.query(Answer).filter(Answer.question_id == question.id).first()
    if existing_answer:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Answer already submitted for this question")
        
    # 2. Save Answer
    new_answer = Answer(
        question_id=question.id,
        answer_text=req.answer_text,
        response_time_seconds=req.response_time_seconds
    )
    db.add(new_answer)
    db.commit()
    db.refresh(new_answer)
    
    # 3. Evaluate Answer via LLM
    is_behavioral = (interview.type.lower() == "behavioral")
    role_title = interview.job_role.title if interview.job_role else "Professional"
    
    evaluation_data = evaluate_answer_with_llm(
        question_text=question.question_text,
        user_answer=req.answer_text,
        expected_concepts=question.expected_concepts or [],
        experience_level=interview.experience_level,
        role=role_title,
        is_behavioral=is_behavioral
    )
    
    # 4. Save Evaluation
    new_eval = AnswerEvaluation(
        answer_id=new_answer.id,
        score=evaluation_data.get("score", 70),
        relevance_score=evaluation_data.get("relevance_score", 70),
        technical_score=evaluation_data.get("technical_score", 70),
        completeness_score=evaluation_data.get("completeness_score", 70),
        communication_score=evaluation_data.get("communication_score", 70),
        reasoning_score=evaluation_data.get("reasoning_score", 70),
        star_score=evaluation_data.get("star_score", 0),
        feedback=evaluation_data.get("feedback", {"strengths": [], "weaknesses": [], "details": ""}),
        missing_concepts=evaluation_data.get("missing_concepts", []),
        improved_answer=evaluation_data.get("improved_answer", "")
    )
    db.add(new_eval)
    db.commit()
    
    # 5. Fetch next question & Apply Adaptive logic
    next_question = db.query(InterviewQuestion).filter(
        InterviewQuestion.interview_id == interview.id,
        InterviewQuestion.order_index == question.order_index + 1
    ).first()
    
    is_completed = (next_question is None)
    
    # Adaptive Logic check:
    # If candidate scored < 50 on this question, and a next question exists, and interview type is technical or mixed:
    # We dynamically adapt the next question's text to be a simpler diagnostic checkpoint
    if next_question and evaluation_data.get("score", 70) < 50 and interview.type.lower() in ["technical", "mixed"]:
        adapted_text = f"As a follow-up, let's step back slightly: {next_question.question_text}"
        # We can also generate a simpler topic question
        next_question.question_text = adapted_text
        next_question.difficulty = "Easy"
        db.commit()
        db.refresh(next_question)
        
    return {
        "evaluation": new_eval,
        "next_question": next_question,
        "is_completed": is_completed
    }

@router.get("/{id}/results", response_model=InterviewResultResponse)
def get_interview_results(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    interview = db.query(Interview).filter(Interview.id == id, Interview.user_id == current_user.id).first()
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
        
    # Check if results are already computed, else calculate
    questions = db.query(InterviewQuestion).filter(InterviewQuestion.interview_id == interview.id).order_by(InterviewQuestion.order_index).all()
    
    # Check if all questions are answered
    answered_count = 0
    scores = []
    competency_sums = {"technical": 0, "communication": 0, "relevance": 0, "completeness": 0, "reasoning": 0, "star": 0}
    
    questions_review = []
    weaknesses = []
    
    for q in questions:
        q_review = {
            "id": q.id,
            "question_text": q.question_text,
            "expected_concepts": q.expected_concepts or [],
            "user_answer": None,
            "evaluation": None
        }
        
        if q.answer:
            answered_count += 1
            q_review["user_answer"] = q.answer.answer_text
            
            if q.answer.evaluation:
                eval_obj = q.answer.evaluation
                q_review["evaluation"] = eval_obj
                scores.append(eval_obj.score)
                
                # Add competencies
                competency_sums["technical"] += eval_obj.technical_score
                competency_sums["communication"] += eval_obj.communication_score
                competency_sums["relevance"] += eval_obj.relevance_score
                competency_sums["completeness"] += eval_obj.completeness_score
                competency_sums["reasoning"] += eval_obj.reasoning_score
                competency_sums["star"] += eval_obj.star_score
                
                # Collect weaknesses details
                w_list = eval_obj.feedback.get("weaknesses", [])
                weaknesses.extend(w_list)
                
        questions_review.append(q_review)
        
    if answered_count == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Interview has no answered questions yet."
        )
        
    avg_score = int(sum(scores) / len(scores))
    interview.overall_score = avg_score
    
    # Calculate competency averages
    comp_averages = {k: int(v / answered_count) for k, v in competency_sums.items()}
    
    # Generate overall summary feedback and Learning Prep plan if not saved
    if not interview.feedback or not interview.recommendations:
        role_title = interview.job_role.title if interview.job_role else "Professional"
        
        history_summary = [{"q_id": q.id, "score": q.answer.evaluation.score if q.answer and q.answer.evaluation else 0} for q in questions]
        
        prep_plan = generate_prep_plan_with_llm(
            role=role_title,
            scores_history=history_summary,
            weaknesses=list(set(weaknesses))[:5]
        )
        
        interview.feedback = f"You completed the interview with an overall score of {avg_score}%. You performed best in communication and logic, but have clear growth opportunities in {', '.join(prep_plan.get('weak_areas', ['technical theory']))}."
        interview.recommendations = prep_plan
        
        # Save Progress History point
        new_progress = ProgressHistory(
            user_id=current_user.id,
            interview_id=interview.id,
            overall_score=avg_score,
            competencies_scores=comp_averages
        )
        db.add(new_progress)
        
        # Update User Performance Summary
        metrics = db.query(PerformanceMetrics).filter(PerformanceMetrics.user_id == current_user.id).first()
        if not metrics:
            metrics = PerformanceMetrics(user_id=current_user.id)
            db.add(metrics)
            
        all_interviews = db.query(Interview).filter(Interview.user_id == current_user.id, Interview.overall_score.isnot(None)).all()
        total_ints = len(all_interviews)
        avg_overall = sum(i.overall_score for i in all_interviews) / total_ints if total_ints > 0 else avg_score
        
        metrics.total_interviews = total_ints
        metrics.average_score = avg_overall
        
        # Simple extraction of best/weakest skill from weaknesses/strengths list
        if prep_plan.get("weak_areas"):
            metrics.weakest_skill = prep_plan["weak_areas"][0]
        else:
            metrics.weakest_skill = "Technical Concept Depth"
            
        metrics.best_performing_skill = "Verbal Communication"
        
        db.commit()
        
    return {
        "id": interview.id,
        "job_role_title": interview.job_role.title if interview.job_role else "Custom Role",
        "experience_level": interview.experience_level,
        "difficulty": interview.difficulty,
        "type": interview.type,
        "num_questions": interview.num_questions,
        "overall_score": interview.overall_score,
        "feedback": interview.feedback,
        "recommendations": interview.recommendations,
        "created_at": interview.created_at,
        "questions_review": questions_review
    }

@router.get("/history", response_model=List[InterviewHistoryItem])
def get_interview_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    interviews = db.query(Interview).filter(Interview.user_id == current_user.id).order_by(Interview.created_at.desc()).all()
    history = []
    for i in interviews:
        history.append({
            "id": i.id,
            "job_role_title": i.job_role.title if i.job_role else "Custom Role",
            "experience_level": i.experience_level,
            "difficulty": i.difficulty,
            "type": i.type,
            "num_questions": i.num_questions,
            "overall_score": i.overall_score,
            "created_at": i.created_at
        })
    return history

# ----------------- PRACTICE MODE ENDPOINTS -----------------

@router.post("/practice/configure", response_model=PracticeQuestionResponse)
def configure_practice_session(
    req: PracticeConfigureRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    role_title = "Software Engineer"
    if req.job_role_id:
        role = db.query(JobRole).filter(JobRole.id == req.job_role_id).first()
        if role:
            role_title = role.title
            
    # Generate multiple targeted practice questions via LLM
    questions = generate_practice_questions_with_llm(
        role=role_title,
        topic=req.topic,
        difficulty=req.difficulty,
        num_questions=req.num_questions
    )

    first_q_text = questions[0]["question_text"] if questions else f"Explain {req.topic}"

    # Format questions list
    formatted_questions = []
    for idx, q in enumerate(questions):
        formatted_questions.append({
            "index": idx,
            "question_text": q.get("question_text", ""),
            "topic": q.get("topic", req.topic),
            "difficulty": q.get("difficulty", req.difficulty),
            "expected_concepts": q.get("expected_concepts", [req.topic])
        })
    
    new_session = PracticeSession(
        user_id=current_user.id,
        job_role_id=req.job_role_id,
        topic=req.topic,
        difficulty=req.difficulty,
        question_text=first_q_text,
        num_questions=len(formatted_questions),
        questions_data=formatted_questions,
        answers_data=[]
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    
    return {
        "id": new_session.id,
        "topic": new_session.topic,
        "difficulty": new_session.difficulty,
        "num_questions": new_session.num_questions,
        "questions": formatted_questions,
        "question_text": first_q_text
    }

@router.post("/practice/submit", response_model=PracticeSubmitResponse)
def submit_practice_response(
    req: PracticeSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    session = db.query(PracticeSession).filter(PracticeSession.id == req.practice_id, PracticeSession.user_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice session not found")
        
    role_title = session.job_role.title if session.job_role else "Software Developer"

    questions = session.questions_data or []
    target_q = None
    if questions and 0 <= req.question_index < len(questions):
        target_q = questions[req.question_index]

    question_text = target_q["question_text"] if target_q else session.question_text
    expected_concepts = target_q.get("expected_concepts", [session.topic]) if target_q else [session.topic]

    # Evaluate practice answer with strict, accurate LLM scoring
    evaluation = evaluate_answer_with_llm(
        question_text=question_text,
        user_answer=req.user_answer,
        expected_concepts=expected_concepts,
        experience_level="Intermediate",
        role=role_title,
        is_behavioral=False
    )
    
    # Update answers_data
    answers = list(session.answers_data or [])
    updated = False
    for item in answers:
        if item.get("question_index") == req.question_index:
            item["user_answer"] = req.user_answer
            item["evaluation"] = evaluation
            item["question_text"] = question_text
            updated = True
            break

    if not updated:
        answers.append({
            "question_index": req.question_index,
            "question_text": question_text,
            "user_answer": req.user_answer,
            "evaluation": evaluation
        })

    session.answers_data = answers

    # Check overall drill completeness and compute average score
    total_q = session.num_questions or len(questions) or 1
    answered_indices = {item.get("question_index") for item in answers}
    is_completed = (len(answered_indices) >= total_q)

    scores = [item["evaluation"].get("score", 0) for item in answers if "evaluation" in item and "score" in item["evaluation"]]
    overall_score = int(sum(scores) / len(scores)) if scores else evaluation.get("score", 0)

    # Backward compatibility fields
    session.user_answer = req.user_answer
    session.feedback = evaluation
    db.commit()
    
    return {
        "practice_id": session.id,
        "question_index": req.question_index,
        "is_completed": is_completed,
        "evaluation": evaluation,
        "feedback": evaluation,
        "all_evaluations": answers,
        "overall_score": overall_score
    }
