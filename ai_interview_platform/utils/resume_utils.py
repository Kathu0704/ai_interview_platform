import os
from typing import Dict, Any, List


def _simple_text_classification(text: str) -> Dict[str, Any]:
    """
    Very lightweight fallback classifier that:
    - extracts a rough list of "skills" as unique keywords
    - classifies the profile as IT / Non-IT based on keyword hits
    """
    text_lower = text.lower()

    it_keywords = [
        "python", "java", "javascript", "react", "django", "flask", "api",
        "sql", "database", "docker", "kubernetes", "aws", "azure",
        "git", "github", "devops", "linux", "cloud", "node.js",
        "html", "css", "c++", "c#", ".net", "spring", "microservices",
        "machine learning", "data science", "tensorflow", "pytorch",
    ]
    non_it_keywords = [
        "hr", "recruiter", "talent acquisition", "payroll", "onboarding",
        "sales", "business development", "marketing", "seo", "content",
        "customer support", "operations", "accountant", "finance",
        "teacher", "administration", "office assistant",
    ]

    it_hits = sum(1 for kw in it_keywords if kw in text_lower)
    non_it_hits = sum(1 for kw in non_it_keywords if kw in text_lower)

    if it_hits == 0 and non_it_hits == 0:
        field = ""
    elif it_hits >= non_it_hits:
        field = "IT"
    else:
        field = "Non-IT"

    # Very rough "skills" list: top unique keywords that matched
    skills: List[str] = []
    for kw in it_keywords + non_it_keywords:
        if kw in text_lower:
            skills.append(kw)

    return {
        "field": field,
        "skills": skills,
    }


def parse_resume_and_detect_field(resume_path: str) -> Dict[str, Any]:
    """
    Best-effort resume parsing:
    1. Try pyresparser.ResumeParser (if available and working)
    2. If that fails, fall back to a very lightweight PDF/text classifier
    """
    if not resume_path or not os.path.exists(resume_path):
        return {"field": "", "skills": [], "raw_text": ""}

    raw_text = ""

    # -------- 1) Try pyresparser if available --------
    try:
        from pyresparser import ResumeParser  # type: ignore

        data = ResumeParser(resume_path).get_extracted_data()
        if not data:
            raise ValueError("Empty data from ResumeParser")

        skills = [s.lower() for s in (data.get("skills") or [])]

        # Simple IT / Non-IT classification based on skills
        it_skills = [
            "python", "java", "javascript", "html", "css", "sql",
            "database", "api", "git", "docker", "kubernetes",
            "aws", "azure", "react", "angular", "vue", "node.js",
            "php", "c++", "c#", ".net", "ruby", "go", "rust", "swift",
            "kotlin", "scala", "r", "matlab", "tensorflow", "pytorch",
            "machine learning", "artificial intelligence",
            "data science", "devops", "cloud computing",
        ]
        field = "IT" if any(skill.lower() in it_skills for skill in skills) else "Non-IT"

        return {
            "field": field,
            "skills": skills,
            "raw_data": data,
        }
    except Exception:
        # Fall through to lightweight classifier
        pass

    # -------- 2) Fallback: extract plain text and classify ----------
    try:
        from pdfminer.high_level import extract_text  # type: ignore

        raw_text = extract_text(resume_path) or ""
    except Exception:
        try:
            # As a very last resort, read as plain text
            with open(resume_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        except Exception:
            raw_text = ""

    return {
        **_simple_text_classification(raw_text),
        "raw_text": raw_text,
    }

