import re
import logging
from typing import Dict, Any, List
from app.services.ai_client import analyze_ats_with_llm

logger = logging.getLogger(__name__)

ACTIVE_VERBS = [
    "managed", "developed", "designed", "led", "architected", "engineered", "built",
    "optimized", "increased", "reduced", "delivered", "implemented", "resolved",
    "created", "spearheaded", "executed", "collaborated", "improved", "launched"
]

def calculate_skills_match(resume_skills: List[str], jd_skills: List[str]) -> int:
    """Calculate overlap of skills (Jaccard similarity style)."""
    if not jd_skills:
        return 80 # default average if JD skills are empty
    resume_set = {s.lower().strip() for s in resume_skills}
    jd_set = {s.lower().strip() for s in jd_skills}
    
    matches = resume_set.intersection(jd_set)
    overlap = len(matches) / len(jd_set)
    return int(overlap * 100)

def calculate_keyword_match(resume_text: str, jd_skills: List[str]) -> int:
    """Check occurrences of job requirements in the raw resume text."""
    if not jd_skills:
        return 75
    text_lower = resume_text.lower()
    matches = 0
    for kw in jd_skills:
        pattern = r'\b' + re.escape(kw.lower()) + r'\b'
        if re.search(pattern, text_lower):
            matches += 1
            
    return int((matches / len(jd_skills)) * 100)

def check_formatting_risks(resume_text: str, structured_info: Dict[str, Any]) -> int:
    """Deduct formatting score based on readability risks."""
    score = 100
    text_lower = resume_text.lower()
    
    # Check if contact details are missing
    if not structured_info.get("email") or not structured_info.get("phone"):
        score -= 15
        
    # Check for text length (extremely short or long)
    words = resume_text.split()
    if len(words) < 100:
        score -= 20 # too short to parse
    elif len(words) > 1500:
        score -= 10 # text wall risk
        
    # Check for presence of common section headings
    headings = ["education", "experience", "skills", "projects"]
    heading_count = 0
    for h in headings:
        if h in text_lower:
            heading_count += 1
            
    if heading_count < 3:
        score -= 20 # poor organization
        
    return max(score, 30)

def evaluate_action_verbs_and_impact(resume_text: str) -> int:
    """Score the presence of active verbs and quantified achievements."""
    text_lower = resume_text.lower()
    verb_count = 0
    for verb in ACTIVE_VERBS:
        if verb in text_lower:
            verb_count += 1
            
    # Check for presence of metrics (numbers representing money, percent, numbers of users, years)
    metric_patterns = [
        r'\b\d+%', # percentages
        r'\$\d+', # currency
        r'\b\d+\s*(?:users|clients|servers|projects|members|years|months|hours|x)\b', # quantities
        r'\b\d+x\b' # speedups
    ]
    metrics_found = 0
    for pattern in metric_patterns:
        if re.search(pattern, text_lower):
            metrics_found += 1
            
    verb_score = min((verb_count / 5) * 50, 50) # max 50 points
    metric_score = min((metrics_found / 3) * 50, 50) # max 50 points
    
    return int(verb_score + metric_score)

def parse_experience_relevance(resume_exp: List[Dict[str, Any]], jd_title: str) -> int:
    """Evaluate experience level fit from resume details against the role title."""
    # Count total work experience items
    exp_count = len(resume_exp)
    if exp_count == 0:
        return 30 # Fresher or low exp
        
    score = 60
    # Add points based on descriptions length and verb usage
    desc_words = 0
    for job in resume_exp:
        desc = job.get("description", "")
        desc_words += len(desc.split())
        
    if desc_words > 200:
        score += 20
    elif desc_words > 50:
        score += 10
        
    # Check if target is senior but experience duration is low
    jd_lower = jd_title.lower()
    is_senior_target = any(w in jd_lower for w in ["senior", "lead", "manager", "architect", "principal"])
    
    if is_senior_target and exp_count < 2:
        score -= 25 # mismatch penalty
    elif not is_senior_target:
        score += 15
        
    return min(max(score, 20), 100)

def score_ats_compatibility(
    resume_text: str,
    resume_info: Dict[str, Any],
    jd_info: Dict[str, Any]
) -> Dict[str, Any]:
    """Calculate the ATS estimated scores using both local analytics and LLM insights."""
    
    # 1. Invoke Gemini for deep qualitative review, semantic matches, and suggestions
    llm_report = analyze_ats_with_llm(resume_info, jd_info)
    
    # 2. Local analytic scores
    skills_score = calculate_skills_match(resume_info.get("skills", []), jd_info.get("skills", []))
    keyword_score = calculate_keyword_match(resume_text, jd_info.get("skills", []))
    formatting_score = check_formatting_risks(resume_text, resume_info)
    action_verb_score = evaluate_action_verbs_and_impact(resume_text)
    experience_score = parse_experience_relevance(resume_info.get("experience", []), jd_info.get("title", ""))
    
    # Simple hardcoded education match
    edu_score = 90
    jd_edu_keywords = ["phd", "master", "ph.d", "m.s", "doctorate"]
    resume_text_lower = resume_text.lower()
    has_advanced_edu = any(k in resume_text_lower for k in jd_edu_keywords)
    jd_reqs_advanced = any(k in jd_info.get("title", "").lower() or k in "\n".join(jd_info.get("qualifications", [])).lower() for k in jd_edu_keywords)
    
    if jd_reqs_advanced and not has_advanced_edu:
        edu_score = 60
    elif has_advanced_edu:
        edu_score = 100
        
    # 3. Aggregate scores with weights matching the ATS Scorer pipeline
    # Weights: 30% Skills, 20% Keywords, 20% Experience, 10% Education, 10% Formatting, 10% Action Impact
    overall_calc = (
        (0.30 * skills_score) +
        (0.20 * keyword_score) +
        (0.20 * experience_score) +
        (0.10 * edu_score) +
        (0.10 * formatting_score) +
        (0.10 * action_verb_score)
    )
    
    # Merge LLM structural reviews into a unified output
    category_scores = {
        "skills_match": int(skills_score),
        "keyword_match": int(keyword_score),
        "experience_match": int(experience_score),
        "education_match": int(edu_score),
        "formatting_score": int(formatting_score)
    }
    
    # Use LLM suggested improvements but update aggregate score to reflect our objective metrics
    return {
        "overall_score": int(overall_calc),
        "category_scores": category_scores,
        "analysis_data": llm_report.get("analysis_data", {
            "keyword_matches": [],
            "critical_missing": [],
            "recommended_missing": [],
            "optional_missing": [],
            "improvements": []
        })
    }
