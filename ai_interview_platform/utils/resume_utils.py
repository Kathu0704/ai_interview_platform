import os
import tempfile
import requests
from typing import Dict, Any, List
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage


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


def parse_resume_and_detect_field(resume_path_or_url: str) -> Dict[str, Any]:
    """
    Best-effort resume parsing that is safe for deployment:
    - Accepts either a local file path or a Cloudinary URL
    - Downloads from URL if needed, then uses pdfminer.six to extract plain text
    - Classifies IT / Non-IT based on keyword hits in the text
    - Avoids heavy spaCy/pyresparser dependencies that often fail on servers
    """
    if not resume_path_or_url:
        print("⚠️ parse_resume_and_detect_field: resume_path_or_url is empty")
        return {"field": "", "skills": [], "raw_text": ""}

    temp_file_path = None
    resume_path = resume_path_or_url

    # Check if it's a URL (Cloudinary or HTTP/HTTPS)
    if resume_path_or_url.startswith(('http://', 'https://')):
        try:
            print(f"📥 Downloading resume from URL: {resume_path_or_url[:50]}...")
            response = requests.get(resume_path_or_url, timeout=30)
            response.raise_for_status()
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_file_path = temp_file.name
            temp_file.write(response.content)
            temp_file.close()
            
            resume_path = temp_file_path
            print(f"✅ Resume downloaded to temp file: {temp_file_path}")
        except Exception as e:
            print(f"⚠️ Failed to download resume from URL: {e}")
            return {"field": "", "skills": [], "raw_text": ""}
    elif not os.path.exists(resume_path):
        print(f"⚠️ parse_resume_and_detect_field: resume_path does not exist: {resume_path}")
        return {"field": "", "skills": [], "raw_text": ""}

    raw_text = ""

    # Try pdfminer first
    try:
        from pdfminer.high_level import extract_text  # type: ignore
        raw_text = extract_text(resume_path) or ""
    except Exception as e:
        print(f"⚠️ pdfminer extract_text failed: {e}")
        try:
            # As a very last resort, read as plain text
            with open(resume_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_text = f.read()
        except Exception as e2:
            print(f"⚠️ Fallback plain-text read failed: {e2}")
            raw_text = ""
    finally:
        # Clean up temporary file if we created one
        if temp_file_path and os.path.exists(temp_file_path):
            try:
                os.unlink(temp_file_path)
                print(f"🧹 Cleaned up temp file: {temp_file_path}")
            except Exception as e:
                print(f"⚠️ Failed to delete temp file: {e}")

    classified = _simple_text_classification(raw_text)
    print("📝 Resume classification result:", classified)

    return {
        **classified,
        "raw_text": raw_text,
    }


