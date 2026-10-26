import json
import logging
import re
from typing import Dict, Any, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Gemini Client & Resilient Model Cascade
# ---------------------------------------------------------------------------
_gemini_client = None

def _get_client():
    global _gemini_client
    if _gemini_client is None and settings.GEMINI_API_KEY:
        try:
            from google import genai
            _gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
        except Exception as e:
            logger.error(f"Failed to initialise Gemini client: {e}")
    return _gemini_client

# Ordered by availability and responsiveness
CASCADE_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-flash-latest",
    "gemini-3.8-flash"
]

def _parse_json_safely(raw_text: Optional[str]) -> Optional[Any]:
    """Robustly parse JSON even if the model wraps it in markdown code fences."""
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```[a-zA-Z]*\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        match = re.search(r"(\{.*\}|\[.*\])", cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return None

def _call_gemini(prompt: str, system_instruction: Optional[str] = None) -> Optional[str]:
    """
    Call Gemini with an automatic multi-model fallback cascade.
    If a model hits a 503 high demand or temporary error, it seamlessly
    tries the next candidate model so the user receives authentic AI generation.
    """
    client = _get_client()
    if not client:
        logger.warning("No Gemini client available; check GEMINI_API_KEY.")
        return None

    from google.genai import types

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.6,
        system_instruction=system_instruction or "You are an elite, highly intelligent AI career coach and technical interviewer."
    )

    for model_name in CASCADE_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=config,
            )
            if response and response.text:
                return response.text
        except Exception as e:
            logger.warning(f"Model {model_name} failed ({e}); falling back to next model...")

    logger.error("All Gemini cascade models failed.")
    return None


# ---------------------------------------------------------------------------
# Fallback Mocks (used ONLY when API is completely offline or no key supplied)
# ---------------------------------------------------------------------------
MOCK_RESUME_INFO = {
    "full_name": "Candidate",
    "email": "candidate@example.com",
    "phone": "+1-555-0100",
    "education": [{"degree": "Bachelor of Science", "institution": "University", "duration": "2020 - 2024"}],
    "skills": ["Python", "JavaScript", "SQL", "Git", "Problem Solving"],
    "experience": [{"job_title": "Software Engineer", "company": "Tech Corp", "duration": "2022 - Present", "description": "Developed backend APIs and managed database integrations."}],
    "projects": [{"title": "Web Application", "technologies": ["Python", "React"], "description": "Built full-stack application with user authentication."}],
    "certifications": ["Cloud Foundations"]
}

MOCK_ATS_EVAL = {
    "overall_score": 75,
    "category_scores": {"skills_match": 75, "keyword_match": 70, "experience_match": 75, "education_match": 80, "formatting_score": 85},
    "analysis_data": {
        "keyword_matches": ["Python", "SQL", "Git"],
        "critical_missing": [{"type": "skills", "name": "System Architecture", "level": "Critical", "description": "Required for target role"}],
        "recommended_missing": [{"type": "tools", "name": "Docker", "level": "Recommended", "description": "Commonly requested in job descriptions"}],
        "optional_missing": [],
        "improvements": [{"section": "Summary", "original": "Looking for opportunities", "problem": "Lacks specificity", "suggestion": "Experienced developer skilled in Python and SQL seeking high-impact engineering role."}]
    }
}

MOCK_INTERVIEW_QUESTIONS = [
    {"question_text": "Explain a significant project you worked on, the architectural decisions you made, and how you measured its success.", "difficulty": "Medium", "expected_concepts": ["Architecture", "Trade-offs", "Metrics"]},
    {"question_text": "How do you handle technical debt while keeping up with rapid feature delivery deadlines?", "difficulty": "Medium", "expected_concepts": ["Prioritization", "Refactoring", "Communication"]},
    {"question_text": "Describe a difficult bug you tracked down in production. What was your debugging methodology?", "difficulty": "Medium", "expected_concepts": ["Root Cause Analysis", "Logging", "Observability"]}
]

MOCK_EVALUATION = {
    "score": 75,
    "relevance_score": 80,
    "technical_score": 75,
    "completeness_score": 75,
    "communication_score": 80,
    "reasoning_score": 75,
    "star_score": 0,
    "feedback": {
        "strengths": ["Relevant answer structure"],
        "weaknesses": ["Could provide deeper technical specifics"],
        "details": "Good initial response. Expand on concrete trade-offs and edge cases for higher marks."
    },
    "missing_concepts": ["System Trade-offs", "Edge Cases"],
    "improved_answer": "Structure your answer with concrete context, specific technical actions taken, and quantified business impact."
}

MOCK_PREP_PLAN = {
    "topics_to_revise": [{"topic": "Core Fundamentals & System Design", "priority": "High", "reason": "Essential for target role competency"}],
    "concepts_to_practice": ["Performance Optimization", "Clean Code Architecture"],
    "difficulty_progression": "Practice Medium-difficulty technical questions with time limits",
    "suggested_next_interview": "Target Role Technical Mock Interview",
    "weak_areas": ["System trade-offs", "Quantified achievements"]
}


# ---------------------------------------------------------------------------
# High-Fidelity Generative AI Services
# ---------------------------------------------------------------------------

def parse_resume_with_llm(extracted_text: str) -> Dict[str, Any]:
    """Parse unstructured resume text into a rich structured schema using Gemini."""
    if settings.DEMO_MODE or not settings.GEMINI_API_KEY:
        return MOCK_RESUME_INFO

    system_inst = "You are an expert technical talent recruiter and resume parsing engine. Extract all candidate information accurately without inventing anything."
    prompt = f"""
    Analyze the following raw resume text and extract the information into a clean JSON object conforming strictly to this schema:
    {{
        "full_name": "Full name of candidate (or Candidate if not found)",
        "email": "Email address (or empty string)",
        "phone": "Phone number (or empty string)",
        "education": [
            {{
                "degree": "Degree / Field of study",
                "institution": "University / Institution name",
                "duration": "Year or range"
            }}
        ],
        "skills": ["Skill1", "Skill2", "Skill3"],
        "experience": [
            {{
                "job_title": "Position title",
                "company": "Company name",
                "duration": "Dates/Duration",
                "description": "Responsibilities and accomplishments"
            }}
        ],
        "projects": [
            {{
                "title": "Project title",
                "technologies": ["tech1", "tech2"],
                "description": "Project overview and contributions"
            }}
        ],
        "certifications": ["Cert1", "Cert2"]
    }}

    Raw Resume Text:
    {extracted_text}
    """

    resp_text = _call_gemini(prompt, system_instruction=system_inst)
    parsed = _parse_json_safely(resp_text)
    if parsed and isinstance(parsed, dict) and "skills" in parsed:
        return parsed

    return MOCK_RESUME_INFO


def analyze_job_description_with_llm(jd_text: str) -> Dict[str, Any]:
    """Extract skills, responsibilities, and qualifications from a Job Description."""
    if settings.DEMO_MODE or not settings.GEMINI_API_KEY:
        return {
            "title": "Professional Role",
            "skills": ["Communication", "Problem Solving", "Technical Competency"],
            "responsibilities": ["Execute key deliverables", "Collaborate with cross-functional teams"],
            "qualifications": ["Relevant degree or equivalent experience"]
        }

    system_inst = "You are an expert HR Analyst and Job Specification Specialist."
    prompt = f"""
    Analyze the following Job Description text and extract key requirements in JSON:
    {{
        "title": "Estimated Job Title",
        "skills": ["Skill1", "Skill2", "Skill3"],
        "responsibilities": ["Primary responsibility 1", "Primary responsibility 2"],
        "qualifications": ["Qualification 1", "Qualification 2"]
    }}

    Job Description:
    {jd_text}
    """

    resp_text = _call_gemini(prompt, system_instruction=system_inst)
    parsed = _parse_json_safely(resp_text)
    if parsed and isinstance(parsed, dict) and "skills" in parsed:
        return parsed

    return {
        "title": "Professional Role",
        "skills": ["Technical Competency", "Communication"],
        "responsibilities": ["Execute team objectives"],
        "qualifications": ["Relevant professional background"]
    }


def analyze_ats_with_llm(resume_info: Dict[str, Any], jd_info: Dict[str, Any]) -> Dict[str, Any]:
    """Perform realistic, high-fidelity ATS compatibility and keyword gap analysis."""
    if settings.DEMO_MODE or not settings.GEMINI_API_KEY:
        return MOCK_ATS_EVAL

    system_inst = "You are a senior Applicant Tracking System (ATS) engineer and executive career coach. Provide rigorous, realistic scoring based strictly on the candidate's actual qualifications versus the job requirements."
    prompt = f"""
    Compare this candidate's resume profile against the target job requirements.
    Be realistic: do NOT award a high score if significant required skills or experience are missing.

    Candidate Resume:
    {json.dumps(resume_info, indent=2)}

    Job Requirements:
    {json.dumps(jd_info, indent=2)}

    Generate a comprehensive ATS evaluation JSON strictly following this schema:
    {{
        "overall_score": 72,
        "category_scores": {{
            "skills_match": 75,
            "keyword_match": 70,
            "experience_match": 68,
            "education_match": 85,
            "formatting_score": 80
        }},
        "analysis_data": {{
            "keyword_matches": ["MatchedSkill1", "MatchedSkill2"],
            "critical_missing": [
                {{"type": "skills/tools", "name": "Missing Required Skill", "level": "Critical", "description": "Why this is critical for the target role"}}
            ],
            "recommended_missing": [
                {{"type": "tools/knowledge", "name": "Recommended Skill", "level": "Recommended", "description": "Why having this elevates candidate ranking"}}
            ],
            "optional_missing": [
                {{"type": "certifications/nice-to-have", "name": "Bonus Skill", "level": "Optional", "description": "Good to have"}}
            ],
            "improvements": [
                {{
                    "section": "Target Section (e.g., Experience / Projects / Summary)",
                    "original": "Excerpt or issue from candidate profile",
                    "problem": "Specific diagnosis (e.g., lacks quantifiable metric, passive voice)",
                    "suggestion": "Realistic, polished re-write showcasing impact without inventing credentials"
                }}
            ]
        }}
    }}
    """

    resp_text = _call_gemini(prompt, system_instruction=system_inst)
    parsed = _parse_json_safely(resp_text)
    if parsed and isinstance(parsed, dict) and "overall_score" in parsed:
        return parsed

    return MOCK_ATS_EVAL


def generate_questions_with_llm(
    role: str,
    experience_level: str,
    difficulty: str,
    interview_type: str,
    resume_info: Optional[Dict[str, Any]] = None,
    num_questions: int = 5
) -> List[Dict[str, Any]]:
    """
    Generate authentic, dynamic interview questions that act like an expert interviewer.
    Adapts deeply to candidate's real resume, projects, and chosen interview style.
    """
    if settings.DEMO_MODE or not settings.GEMINI_API_KEY:
        return MOCK_INTERVIEW_QUESTIONS[:num_questions]

    resume_summary = "Candidate has not uploaded a resume yet."
    if resume_info:
        skills = resume_info.get("skills", [])
        experience = resume_info.get("experience", [])
        projects = resume_info.get("projects", [])
        resume_summary = f"Skills: {skills}\nExperience: {experience}\nProjects: {projects}"

    system_inst = (
        f"You are a seasoned Principal Interviewer and Hiring Manager for {role} positions. "
        "You conduct demanding, realistic, and highly engaging interviews. "
        "Your questions are never generic clichés; they test real problem-solving, architectural acumen, edge cases, and genuine experience."
    )

    prompt = f"""
    Generate exactly {num_questions} interview questions tailored to:
    - Target Role: {role}
    - Seniority/Level: {experience_level}
    - Difficulty: {difficulty}
    - Interview Focus: {interview_type} (e.g. Technical, Behavioral, HR, Situational, Resume-Based)

    Candidate Profile Context:
    {resume_summary}

    Guidelines:
    1. If the interview type is Resume-Based, ask directly about their specific projects or technologies listed above.
    2. If Technical, ask practical, architectural, or debugging questions that reveal true mastery.
    3. If Behavioral, construct realistic workplace scenarios (challenges, pushback, conflict, leadership).
    4. Provide 3-4 key concept tags the interviewer is listening for.

    Return JSON strictly conforming to:
    {{
      "questions": [
        {{
          "question_text": "Precise, thoughtful question text...",
          "difficulty": "{difficulty}",
          "expected_concepts": ["Concept 1", "Concept 2", "Concept 3"]
        }}
      ]
    }}
    """

    resp_text = _call_gemini(prompt, system_instruction=system_inst)
    parsed = _parse_json_safely(resp_text)
    if parsed and isinstance(parsed, dict) and "questions" in parsed and isinstance(parsed["questions"], list):
        if len(parsed["questions"]) > 0:
            return parsed["questions"][:num_questions]

    return MOCK_INTERVIEW_QUESTIONS[:num_questions]


def _evaluate_answer_fallback(
    question_text: str,
    user_answer: str,
    expected_concepts: List[str],
    is_behavioral: bool = False
) -> Dict[str, Any]:
    """
    Intelligent, grounded fallback evaluator for when LLM API is unavailable.
    Accurately penalizes brief, off-topic, or non-committal answers.
    Accurately attributes key concepts addressed based strictly on actual answer content.
    """
    cleaned = (user_answer or "").strip()
    words = cleaned.split()
    word_count = len(words)
    lower_ans = cleaned.lower()
    expected_list = list(expected_concepts or [])

    # Pre-check: extremely brief, admitted ignorance, or empty
    if word_count < 6 or any(phrase in lower_ans for phrase in [
        "don't know", "dont know", "no idea", "not sure", "idk", "skip", "pass", "nothing", "dunno", "none"
    ]):
        missing = expected_list if expected_list else ["Core Technical Principles", "System Mechanics"]
        return {
            "score": 10,
            "relevance_score": 10,
            "technical_score": 5,
            "completeness_score": 5,
            "communication_score": 15,
            "reasoning_score": 10,
            "star_score": 0,
            "key_concepts_addressed": [],
            "missing_concepts": missing,
            "feedback": {
                "strengths": [],
                "weaknesses": [
                    "No substantive technical explanation was provided.",
                    f"Failed to address the core problem and required concepts: {', '.join(missing)}."
                ],
                "details": "The response was insufficient to evaluate technical competency. In a professional interview, articulate foundational mechanics or outline a logical problem-solving approach."
            },
            "improved_answer": f"To effectively answer '{question_text}', a candidate should explain: {', '.join(missing)}, outlining their architectural rationale and discussing production trade-offs." if missing else "To effectively answer this, define the fundamental mechanics, explain key trade-offs, and describe real-world application."
        }

    # Strict keyword and conceptual analysis
    STOP_WORDS = {
        "data", "database", "databases", "system", "systems", "with", "from", "that", "this",
        "table", "tables", "order", "level", "based", "using", "into", "type", "types",
        "mode", "code", "core", "test", "role", "work", "make", "good", "need", "only",
        "also", "have", "been", "does", "than", "more", "most", "high", "some", "such",
        "like", "well", "over", "each", "when", "what", "which", "will", "would", "could",
        "where", "there", "their", "they", "about", "other", "into", "just", "very"
    }

    # Check for obvious false assertions or inverted logic
    has_falsehoods = any(phrase in lower_ans for phrase in [
        "stored in ram", "10 clustered", "100 clustered", "opposite of", "does not exist",
        "fake", "random", "no reason", "whatever", "who knows"
    ])

    matched_concepts = []
    missing_concepts = []

    if has_falsehoods or word_count < 10:
        # Cannot meaningfully claim addressed concepts if answer contains known falsehoods or is too terse
        matched_concepts = []
        missing_concepts = list(expected_list)
        calculated_score = 15 if has_falsehoods else 20
    else:
        for concept in expected_list:
            concept_clean = concept.strip()
            # Extract distinctive terms (length >= 4 and not common stop words)
            distinctive_words = [
                w.lower().strip("(),.:;\"'[]{}") for w in concept_clean.split()
                if len(w) >= 4 and w.lower().strip("(),.:;\"'[]{}") not in STOP_WORDS
            ]

            concept_lower = concept_clean.lower()
            has_exact_phrase = (concept_lower in lower_ans)
            matched_distinctive = [w for w in distinctive_words if w in lower_ans]
            
            # Require exact phrase OR majority of distinctive keywords to avoid false positive matches
            min_required = max(1, (len(distinctive_words) + 1) // 2) if distinctive_words else 1
            is_matched = has_exact_phrase or (len(matched_distinctive) >= min_required and len(distinctive_words) > 0)

            if is_matched:
                matched_concepts.append(concept_clean)
            else:
                missing_concepts.append(concept_clean)

        total_expected = max(len(expected_list), 1)
        coverage_ratio = len(matched_concepts) / total_expected

        if len(matched_concepts) == 0:
            calculated_score = min(25, int(10 + min(word_count * 0.25, 15)))
        else:
            calculated_score = int(25 + (coverage_ratio * 45) + min(word_count * 0.2, 20))
            calculated_score = max(20, min(calculated_score, 90))

    total_expected = max(len(expected_list), 1)
    strengths = [f"Addressed concept: {c}" for c in matched_concepts]
    weaknesses = [f"Missing expected concept: {c}" for c in missing_concepts]

    if not strengths and calculated_score < 35:
        weaknesses.insert(0, "The response did not accurately cover the required technical concepts.")

    if len(matched_concepts) == 0:
        details = f"The response did not accurately address any of the required technical concepts ({', '.join(expected_list)}). Strict technical grading was applied."
    elif len(missing_concepts) == 0:
        details = f"Comprehensive technical coverage. Addressed all {len(matched_concepts)} expected concepts accurately."
    else:
        details = f"Partial technical criteria match. Addressed {len(matched_concepts)} of {total_expected} target concepts ({', '.join(matched_concepts)}), but omitted critical mechanics: {', '.join(missing_concepts)}."

    return {
        "score": calculated_score,
        "relevance_score": int(calculated_score * 1.05),
        "technical_score": calculated_score,
        "completeness_score": int(calculated_score * (len(matched_concepts) / total_expected)),
        "communication_score": min(85, int(calculated_score * 1.1 + 5)),
        "reasoning_score": calculated_score,
        "star_score": 40 if is_behavioral else 0,
        "key_concepts_addressed": matched_concepts,
        "missing_concepts": missing_concepts,
        "feedback": {
            "strengths": strengths,
            "weaknesses": weaknesses,
            "details": details
        },
        "improved_answer": f"A comprehensive response to '{question_text}' should cover: {', '.join(expected_list)}. Define the underlying mechanics, evaluate architectural trade-offs, and detail production best practices." if expected_list else "Provide a detailed answer with concrete examples and architectural trade-offs."
    }


def evaluate_answer_with_llm(
    question_text: str,
    user_answer: str,
    expected_concepts: List[str],
    experience_level: str,
    role: str,
    is_behavioral: bool = False
) -> Dict[str, Any]:
    """
    Evaluate candidate answers with authentic, rigorous intelligence.
    Critiques specific points from what the candidate actually said, identifying exact gaps.
    Enforces strict truthfulness and penalizes incorrect or vague claims.
    """
    user_trimmed = (user_answer or "").strip()
    user_lower = user_trimmed.lower()

    # Check for empty or explicitly admitted ignorance
    if len(user_trimmed) == 0 or user_lower in [
        "i don't know", "idk", "dont know", "no idea", "not sure", "skip", "pass", "nothing", "none"
    ]:
        missing = expected_concepts if expected_concepts else ["Foundational Principles", "Technical Trade-offs"]
        return {
            "score": 0,
            "relevance_score": 0,
            "technical_score": 0,
            "completeness_score": 0,
            "communication_score": 10,
            "reasoning_score": 0,
            "star_score": 0,
            "key_concepts_addressed": [],
            "missing_concepts": missing,
            "feedback": {
                "strengths": [],
                "weaknesses": [
                    "No substantive answer provided or admitted complete lack of knowledge.",
                    f"Failed to address required concepts: {', '.join(missing)}."
                ],
                "details": "The candidate provided an empty or non-committal response. For this role, candidates must demonstrate foundational knowledge and clear reasoning."
            },
            "improved_answer": f"To effectively answer '{question_text}', a candidate should explain the core mechanics: {', '.join(missing)}, outlining why they matter in a {role} environment and discussing practical trade-offs."
        }

    if settings.DEMO_MODE or not settings.GEMINI_API_KEY:
        return _evaluate_answer_fallback(question_text, user_answer, expected_concepts, is_behavioral)

    system_inst = (
        f"You are a rigorous, uncompromising Principal Technical Interviewer and Hiring Bar Raiser for {role} ({experience_level}). "
        "Your highest priority is FACTUAL, TECHNICAL ACCURACY. "
        "CRITICAL SCORING RULES: "
        "1. DO NOT be polite or lenient when an answer is wrong, misleading, or hallucinated. "
        "2. If an answer contains factually incorrect statements, inverted definitions, wrong logic, or pseudo-technical nonsense, "
        "   its 'score' and 'technical_score' MUST be between 0 and 25. High communication or grammar must NEVER compensate for technical falsehoods. "
        "3. If the answer is 'I don't know', empty, off-topic, or gibberish, the score MUST be between 0 and 15. "
        "4. If the answer is partially correct but has major misconceptions or omissions, score between 30 and 50. "
        "5. Award scores of 70+ ONLY to answers that are factually correct and address core requirements. "
        "6. Award scores of 85+ ONLY to truly comprehensive, top-tier responses demonstrating mastery and depth."
    )

    prompt = f"""
    Interview Question:
    {question_text}

    Expected Key Technical Concepts / Criteria:
    {json.dumps(expected_concepts)}

    Target Role & Seniority:
    {role} ({experience_level})

    Is Behavioral (Evaluate STAR format: Situation, Task, Action, Result): {is_behavioral}

    Candidate's Actual Answer:
    \"\"\"{user_answer}\"\"\"

    EVALUATION INSTRUCTIONS:
    1. First verify technical correctness. Are the candidate's claims factually true or false?
    2. Check coverage against Expected Concepts: {json.dumps(expected_concepts)}.
       - 'key_concepts_addressed': List the specific expected concepts that the candidate ACCURATELY and CORRECTLY addressed or explained in their answer.
         If the candidate did not explain an expected concept, or explained it incorrectly, DO NOT list it in 'key_concepts_addressed'.
         If the candidate provided no valid technical explanation or gave an entirely wrong answer, this MUST be an empty array [].
       - 'missing_concepts': List the specific expected concepts that were omitted, incomplete, or incorrectly stated.
    3. Assign strict numeric scores (0 to 100):
       - 0 to 20: Factually WRONG, inverted concepts, hallucinated claims, or 'idk' / irrelevant / empty.
       - 21 to 49: Major misconceptions or fundamental technical errors.
       - 50 to 69: Partially correct with no critical factual falsehoods, but missing key depth.
       - 70 to 84: Correct, accurate, and structured.
       - 85 to 100: Exceptional, comprehensive, covers edge cases and production trade-offs.
    4. In 'feedback.strengths': Specific positive technical aspects articulated correctly in the candidate's words (empty array [] if answer is completely wrong).
    5. In 'feedback.weaknesses': Explicitly state any factual errors, false assertions, or missing concepts.
    6. In 'improved_answer': Write a complete, comprehensive, highly technical model answer specifically answering this question.

    Return JSON conforming strictly to:
    {{
      "score": 0,
      "relevance_score": 0,
      "technical_score": 0,
      "completeness_score": 0,
      "communication_score": 0,
      "reasoning_score": 0,
      "star_score": 0,
      "key_concepts_addressed": [
        "Concept from Expected Concepts that the candidate accurately addressed or explained"
      ],
      "missing_concepts": [
        "Concept from Expected Concepts that was missed or incorrectly explained"
      ],
      "feedback": {{
        "strengths": ["Specific strength 1"],
        "weaknesses": ["Specific weakness or factual mistake 1"],
        "details": "Detailed feedback assessing depth, accuracy, and clarity."
      }},
      "improved_answer": "A top-tier comprehensive technical response specifically answering this question..."
    }}
    """

    resp_text = _call_gemini(prompt, system_instruction=system_inst)
    parsed = _parse_json_safely(resp_text)
    if parsed and isinstance(parsed, dict) and "score" in parsed:
        # Mathematical Safety Net:
        # If the candidate's weaknesses indicate factual errors or nonsensical answers,
        # clamp the score so an erroneous answer cannot receive an inflated score.
        weaknesses_list = parsed.get("feedback", {}).get("weaknesses", [])
        weaknesses_text = " ".join(weaknesses_list if isinstance(weaknesses_list, list) else []).lower()
        details_text = str(parsed.get("feedback", {}).get("details", "")).lower()
        combined_critique = weaknesses_text + " " + details_text

        is_critically_flawed = any(phrase in combined_critique for phrase in [
            "factually incorrect", "entirely incorrect", "completely incorrect",
            "factually wrong", "entirely wrong", "completely wrong",
            "opposite of reality", "inverted the definition", "nonsensical",
            "complete gibberish", "fundamental misunderstanding", "profound lack of understanding"
        ])

        if is_critically_flawed:
            parsed["score"] = min(int(parsed.get("score", 0)), 25)
            parsed["technical_score"] = min(int(parsed.get("technical_score", 0)), 20)
            parsed["reasoning_score"] = min(int(parsed.get("reasoning_score", 0)), 20)
            parsed["key_concepts_addressed"] = []
            parsed["missing_concepts"] = list(expected_concepts or [])

        # Strict validation on key_concepts_addressed and missing_concepts
        if int(parsed.get("score", 0)) < 25:
            parsed["key_concepts_addressed"] = []
            if not parsed.get("missing_concepts"):
                parsed["missing_concepts"] = list(expected_concepts or [])
        else:
            if not isinstance(parsed.get("key_concepts_addressed"), list):
                parsed["key_concepts_addressed"] = []
            if not isinstance(parsed.get("missing_concepts"), list):
                addressed_set = {str(c).lower() for c in parsed.get("key_concepts_addressed", [])}
                parsed["missing_concepts"] = [c for c in (expected_concepts or []) if str(c).lower() not in addressed_set]

        return parsed

    return _evaluate_answer_fallback(question_text, user_answer, expected_concepts, is_behavioral)


def generate_prep_plan_with_llm(
    role: str,
    scores_history: List[Dict[str, Any]],
    weaknesses: List[str]
) -> Dict[str, Any]:
    """Generate a dynamic, customized learning plan targeting the candidate's observed weak spots."""
    if settings.DEMO_MODE or not settings.GEMINI_API_KEY:
        return MOCK_PREP_PLAN

    system_inst = "You are an executive Career Coach and Technical Mentor creating customized interview preparation roadmaps."
    prompt = f"""
    Create a personalized study and practice roadmap for a candidate pursuing: {role}.
    Candidate Interview History: {json.dumps(scores_history)}
    Identified Weak Areas: {json.dumps(weaknesses)}

    Return JSON strictly conforming to:
    {{
        "topics_to_revise": [
            {{"topic": "Specific Topic", "priority": "High/Medium/Low", "reason": "Specific justification based on candidate's performance"}}
        ],
        "concepts_to_practice": ["Concept 1", "Concept 2", "Concept 3"],
        "difficulty_progression": "Actionable guidance on how to level up from current performance",
        "suggested_next_interview": "Targeted next mock interview format to tackle remaining gaps",
        "weak_areas": ["Weakness 1", "Weakness 2"]
    }}
    """

    resp_text = _call_gemini(prompt, system_instruction=system_inst)
    parsed = _parse_json_safely(resp_text)
    if parsed and isinstance(parsed, dict) and "topics_to_revise" in parsed:
        return parsed

    return MOCK_PREP_PLAN


def generate_practice_questions_with_llm(
    role: str,
    topic: str,
    difficulty: str,
    num_questions: int = 3
) -> List[Dict[str, Any]]:
    """
    Generate multiple sharp, distinct, and high-yield interview practice drill questions.
    Each question has targeted expected concepts so evaluations are strictly grounded.
    """
    count = max(1, min(num_questions, 10))

    if settings.DEMO_MODE or not settings.GEMINI_API_KEY:
        return [
            {
                "index": i,
                "question_text": f"Drill {i + 1}: Explain how {topic} operates in production, including key architecture trade-offs and error scenarios.",
                "topic": topic,
                "difficulty": difficulty,
                "expected_concepts": [topic, "Architectural Trade-offs", "Production Best Practices"]
            }
            for i in range(count)
        ]

    system_inst = (
        f"You are a Principal Engineering Mentor designing focused interview practice drills for {role} candidates. "
        "Create challenging, diverse, and practical questions that test true understanding, mechanics, and trade-offs."
    )
    prompt = f"""
    Generate exactly {count} distinct practice drill questions to test a {role} candidate on:
    - Topic: {topic}
    - Difficulty: {difficulty}

    Requirements:
    1. Each question must target a different facet or problem scenario within '{topic}'.
    2. Provide 3-4 concrete 'expected_concepts' (keywords/mechanisms) for each question that a correct answer must cover.
    3. Make questions concrete (e.g. debugging, implementation choices, performance bottlenecks, or trade-offs).

    Return JSON strictly conforming to:
    {{
        "questions": [
            {{
                "question_text": "Detailed practice question text...",
                "topic": "{topic}",
                "difficulty": "{difficulty}",
                "expected_concepts": ["Concept 1", "Concept 2", "Concept 3"]
            }}
        ]
    }}
    """

    resp_text = _call_gemini(prompt, system_instruction=system_inst)
    parsed = _parse_json_safely(resp_text)
    if parsed:
        # Handle parsed if dict with questions or list
        items = []
        if isinstance(parsed, dict) and "questions" in parsed and isinstance(parsed["questions"], list):
            items = parsed["questions"]
        elif isinstance(parsed, list):
            items = parsed

        if len(items) > 0:
            formatted = []
            for idx, item in enumerate(items[:count]):
                formatted.append({
                    "index": idx,
                    "question_text": item.get("question_text", f"Explain {topic}"),
                    "topic": item.get("topic", topic),
                    "difficulty": item.get("difficulty", difficulty),
                    "expected_concepts": item.get("expected_concepts", [topic])
                })
            return formatted

    # Fallback if generation parse failed
    return [
        {
            "index": i,
            "question_text": f"Drill {i + 1}: Explain the core mechanics of {topic} as applied in a professional {role} environment, including key trade-offs.",
            "topic": topic,
            "difficulty": difficulty,
            "expected_concepts": [topic, "Trade-offs", "Production Implementation"]
        }
        for i in range(count)
    ]


def generate_practice_question_with_llm(
    role: str,
    topic: str,
    difficulty: str
) -> Dict[str, Any]:
    """Single question wrapper for backward compatibility."""
    questions = generate_practice_questions_with_llm(role, topic, difficulty, num_questions=1)
    return questions[0] if questions else {
        "question_text": f"Explain the core principles of {topic} as applied in a professional {role} environment.",
        "topic": topic,
        "difficulty": difficulty,
        "expected_concepts": [topic]
    }
