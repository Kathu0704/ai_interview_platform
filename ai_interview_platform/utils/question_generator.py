# Enhanced AI Interview Question Generator
import os
import time
import random
import re
import hashlib
from datetime import datetime
from django.db.models import Count
from candidate.models import InterviewRecord

# Optional Gemini import
try:
    import google.generativeai as genai  # type: ignore
except Exception:
    genai = None

# ================== LOAD & CONFIGURE GEMINI ==================

GEMINI_ENABLED = False
try:
    from dotenv import load_dotenv
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if api_key and genai is not None:
        try:
            genai.configure(api_key=api_key)
            GEMINI_ENABLED = True
        except Exception:
            GEMINI_ENABLED = False
    else:
        GEMINI_ENABLED = False
except Exception:
    GEMINI_ENABLED = False 

# ================== DIFFICULTY PROGRESSION ==================
def get_difficulty_by_interview_count(count: int) -> str:
    """
    Progressive difficulty based on interview count:
    1st interview → very_easy (basic role understanding)
    2-3 interviews → easy (experience and tools)
    4+ interviews → medium (scenarios and problem-solving)
    """
    if count <= 1:
        return "very_easy"
    elif count <= 3:
        return "easy"
    return "medium"

# ================== ENHANCED PROMPT BUILDER ==================
def build_enhanced_prompt(role, designation, difficulty, num_questions, previous_questions, candidate_experience=""):
    """
    Build a comprehensive prompt for accurate, role-specific questions.
    """
    role_context = {
        "IT": "technology and software development",
        "Non-IT": "business operations and management"
    }.get(role, "professional")
    
    difficulty_context = {
        "very_easy": "basic understanding and fundamental concepts",
        "easy": "practical experience and common tools/processes", 
        "medium": "real-world scenarios and problem-solving situations"
    }
    
    exclude_text = ""
    if previous_questions:
        exclude_text = f"\n\nIMPORTANT: Avoid these previously asked questions:\n{chr(10).join(f'- {q}' for q in previous_questions[:5])}"
    
    prompt = f"""You are an expert HR interviewer specializing in {role_context} roles.

Generate {num_questions} interview questions for a {designation} position.

CONTEXT:
- Role: {designation}
- Domain: {role_context}
- Difficulty Level: {difficulty} ({difficulty_context[difficulty]})
- Focus: Real interview scenarios, practical knowledge, and role-specific skills

REQUIREMENTS:
1. Questions must be specific to {designation} responsibilities and skills
2. Difficulty: {difficulty} level only (no expert/hard questions)
3. Mix of technical knowledge, soft skills, and situational questions
4. Questions should be clear, professional, and interview-appropriate
5. Focus on practical experience and problem-solving abilities

FORMAT: Return only numbered questions (1. Question text?)
{exclude_text}

Generate {num_questions} questions:"""

    return prompt

# ================== ENHANCED QUESTION EXTRACTION ==================
def extract_questions(text, num_questions):
    """Extract and clean questions from AI response."""
    questions = []
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        # Match numbered questions (1. Question text?)
        if re.match(r'^\d+\.', line):
            # Extract question text after number
            question_text = re.sub(r'^\d+\.\s*', '', line).strip()
            if question_text and question_text.endswith('?'):
                questions.append(question_text)
        # Also match questions without numbers but ending with ?
        elif line.endswith('?') and len(line) > 10:
            questions.append(line)
    
    return questions[:num_questions]

# ================== PERSISTENT QUESTION HISTORY ==================
def get_previous_questions_for_candidate(candidate_id, designation):
    """Get questions previously asked to this candidate for this designation."""
    try:
        previous_interviews = InterviewRecord.objects.filter(
            candidate_id=candidate_id,
            designation=designation
        ).order_by('-created_at')
        
        previous_questions = set()
        for interview in previous_interviews:
            for eval_item in interview.evaluations:
                if 'question' in eval_item:
                    previous_questions.add(eval_item['question'])
        
        return list(previous_questions)
    except Exception:
        return []

def get_interview_count_for_designation(candidate_id, designation):
    """Get how many times this candidate has been interviewed for this designation."""
    try:
        return InterviewRecord.objects.filter(
            candidate_id=candidate_id,
            designation=designation
        ).count()
    except Exception:
        return 0

# ================== ENHANCED FALLBACK QUESTIONS ==================
def get_fallback_questions(role, designation, difficulty, num_questions):
    """Comprehensive fallback questions organized by role and difficulty."""
    
    # IT Role Questions
    it_questions = {
        "very_easy": [
            f"What programming languages are you most comfortable with for {designation} work?",
            f"Can you explain the basic responsibilities of a {designation}?",
            f"What development tools or IDEs do you use regularly?",
            f"How do you stay updated with the latest technologies in your field?",
            f"What is your understanding of version control systems like Git?"
        ],
        "easy": [
            f"Describe a project where you used {designation} skills to solve a problem.",
            f"What frameworks or libraries are you most experienced with?",
            f"How do you approach debugging and troubleshooting in your work?",
            f"Can you explain your experience with database design and management?",
            f"What is your experience with testing and quality assurance processes?"
        ],
        "medium": [
            f"Walk us through how you would design a scalable system for a {designation} project.",
            f"Describe a challenging technical problem you solved and your approach.",
            f"How do you handle conflicting requirements from different stakeholders?",
            f"Explain your experience with cloud platforms and deployment strategies.",
            f"What is your approach to code review and maintaining code quality?"
        ]
    }
    
    # Non-IT Role Questions
    non_it_questions = {
        "very_easy": [
            f"What are the key responsibilities of a {designation} in your understanding?",
            f"How do you prioritize tasks in a busy work environment?",
            f"What software tools do you use for {designation} work?",
            f"How do you handle customer or client interactions?",
            f"What is your approach to meeting deadlines and targets?"
        ],
        "easy": [
            f"Describe a successful project you managed as a {designation}.",
            f"How do you handle difficult team members or stakeholders?",
            f"What metrics do you use to measure success in your role?",
            f"Can you explain your experience with budget management?",
            f"How do you stay organized when handling multiple projects?"
        ],
        "medium": [
            f"Walk us through how you would handle a crisis situation in your role.",
            f"Describe a time when you had to implement a major change in your organization.",
            f"How do you balance competing priorities from different departments?",
            f"Explain your approach to strategic planning and goal setting.",
            f"What is your experience with cross-functional team leadership?"
        ]
    }
    
    questions = it_questions if role == "IT" else non_it_questions
    available = questions.get(difficulty, questions["easy"])
    random.shuffle(available)
    return available[:num_questions]

# ================== MAIN ENHANCED GENERATOR ==================
def generate_questions(role, designation, num_questions=5, candidate_id=None):
    """
    Enhanced question generator with persistent history and role-specific accuracy.
    """
    if not role or not designation:
        return ["Error: Role and designation required."]
    
    # Get candidate's interview history for this designation
    interview_count = get_interview_count_for_designation(candidate_id, designation) if candidate_id else 0
    previous_questions = get_previous_questions_for_candidate(candidate_id, designation) if candidate_id else []
    
    # Determine difficulty based on interview count
    difficulty = get_difficulty_by_interview_count(interview_count)
    
    # Try AI generation first
    if GEMINI_ENABLED:
        try:
            prompt = build_enhanced_prompt(role, designation, difficulty, num_questions, previous_questions)
            
            # Use Gemini Pro for better question quality
            model = genai.GenerativeModel(
                "gemini-1.5-pro-latest",
                generation_config={
                    "temperature": 0.7,
                    "top_p": 0.9,
                    "max_output_tokens": 800,
                }
            )
            
            response = model.generate_content(prompt)
            ai_questions = extract_questions(response.text, num_questions)
            
            # Filter out previously asked questions
            new_questions = [q for q in ai_questions if q not in previous_questions]
            
            if len(new_questions) >= num_questions:
                return new_questions[:num_questions]
            elif new_questions:
                # Supplement with fallback questions
                remaining = num_questions - len(new_questions)
                fallback = get_fallback_questions(role, designation, difficulty, remaining)
                fallback = [q for q in fallback if q not in previous_questions and q not in new_questions]
                combined = new_questions + fallback[:remaining]
                # If still short, pad with generic templates
                if len(combined) < num_questions:
                    templates = [
                        f"What are your core responsibilities as a {designation}?",
                        f"Describe a challenging situation you handled as a {designation}.",
                        f"Which tools or methods do you rely on most as a {designation}?",
                        f"How do you measure success in your {designation} role?",
                        f"Tell us about a project that best showcases your {designation} skills."
                    ]
                    for t in templates:
                        if t not in combined:
                            combined.append(t)
                        if len(combined) >= num_questions:
                            break
                return combined[:num_questions]
                
        except Exception as e:
            print(f"AI question generation failed: {e}")
    
    # Fallback to predefined questions
    fallback_questions = get_fallback_questions(role, designation, difficulty, num_questions)
    filtered_questions = [q for q in fallback_questions if q not in previous_questions]
    
    # Ensure we always return at least num_questions; pad with generic templates if needed
    if len(filtered_questions) < num_questions:
        templates = [
            f"What interests you most about the {designation} role?",
            f"How do you stay current in {designation}-related practices?",
            f"Can you walk through your typical day as a {designation}?",
            f"Describe a time you improved a process in your {designation} work.",
            f"How do you collaborate with stakeholders in your {designation} responsibilities?"
        ]
        for t in templates:
            if t not in filtered_questions:
                filtered_questions.append(t)
            if len(filtered_questions) >= num_questions:
                break
    
    return filtered_questions[:num_questions]
