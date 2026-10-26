import os
import re
from typing import Dict, Any, List
from pdfminer.high_level import extract_text as extract_pdf_text
from docx import Document as DocxDocument
from app.services.ai_client import parse_resume_with_llm

# A list of standard common skills for quick local taxonomy check
COMMON_SKILLS = [
    "python", "javascript", "react", "fastapi", "sql", "docker", "git", "machine learning",
    "kubernetes", "aws", "ci/cd", "redis", "postgresql", "mysql", "java", "spring boot",
    "c++", "c#", "html", "css", "typescript", "angular", "vue", "node.js", "express",
    "mongodb", "dynamodb", "linux", "jenkins", "terraform", "django", "flask",
    "data science", "nlp", "statistics", "project management", "scrum", "agile",
    "communication", "leadership", "problem solving", "teamwork"
]

def extract_text_from_pdf(file_path: str) -> str:
    """Extract clean text from PDF using pdfminer."""
    try:
        text = extract_pdf_text(file_path)
        # Clean basic whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except Exception as e:
        raise ValueError(f"Failed to parse PDF file: {str(e)}")

def extract_text_from_docx(file_path: str) -> str:
    """Extract text from Word Document."""
    try:
        doc = DocxDocument(file_path)
        full_text = []
        for para in doc.paragraphs:
            full_text.append(para.text)
        text = "\n".join(full_text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except Exception as e:
        raise ValueError(f"Failed to parse Word Document: {str(e)}")

def extract_contact_info(text: str) -> Dict[str, str]:
    """Helper to extract email and phone number using simple regex."""
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    phone_pattern = r'(\+?\d{1,4}[-.\s]??\d{1,4}[-.\s]??\d{4,10}|\(\d{3}\)\s*\d{3}[-.\s]??\d{4})'
    
    emails = re.findall(email_pattern, text)
    phones = re.findall(phone_pattern, text)
    
    return {
        "email": emails[0] if emails else "",
        "phone": phones[0] if phones else ""
    }

def local_skill_matcher(text: str) -> List[str]:
    """Identify skills from the resume text using simple local matching."""
    text_lower = text.lower()
    matched = []
    for skill in COMMON_SKILLS:
        # Match word boundaries to prevent substring overlaps (e.g. 'c' matching in 'cat')
        pattern = r'\b' + re.escape(skill) + r'\b'
        if re.search(pattern, text_lower):
            # Capitalize properly based on standard dictionary representation
            matched.append(skill.title() if skill not in ["aws", "sql", "nlp", "ci/cd"] else skill.upper())
    return list(set(matched))

def parse_resume(file_path: str, filename: str) -> Dict[str, Any]:
    """Parse resume by extracting text locally and structuring it using the LLM."""
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        extracted_text = extract_text_from_pdf(file_path)
    elif ext in [".docx", ".doc"]:
        extracted_text = extract_text_from_docx(file_path)
    else:
        raise ValueError("Unsupported file format. Please upload PDF or DOCX.")
        
    if not extracted_text:
        raise ValueError("The uploaded resume file is empty or could not be parsed.")
        
    # Extract metadata using local fast methods
    local_info = extract_contact_info(extracted_text)
    local_skills = local_skill_matcher(extracted_text)
    
    # Process structured information through the LLM
    structured_info = parse_resume_with_llm(extracted_text)
    
    # Merge local checks for completeness if LLM missed basic regex details
    if not structured_info.get("email") and local_info["email"]:
        structured_info["email"] = local_info["email"]
    if not structured_info.get("phone") and local_info["phone"]:
        structured_info["phone"] = local_info["phone"]
        
    # Combine skills
    llm_skills = structured_info.get("skills", [])
    combined_skills = list(set([s.lower() for s in llm_skills] + [s.lower() for s in local_skills]))
    # Format properly
    formatted_skills = []
    for s in combined_skills:
        if s in ["aws", "sql", "nlp", "ci/cd"]:
            formatted_skills.append(s.upper())
        else:
            formatted_skills.append(s.title())
    structured_info["skills"] = formatted_skills
    
    return {
        "text": extracted_text,
        "structured_info": structured_info
    }
