# Enhanced AI Interview Answer Evaluator
import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY_1")
if not api_key:
    raise ValueError("GEMINI_API_KEY not found.")

genai.configure(api_key=api_key)

# Use a simpler model configuration for better reliability
model = genai.GenerativeModel("gemini-1.5-pro-latest")

# Enhanced evaluation criteria with detailed descriptions
EVALUATION_CRITERIA = {
    "Relevance and Clarity": {
        "description": "How well the answer addresses the question and communicates ideas clearly",
        "1": "Answer is completely irrelevant or incomprehensible",
        "2": "Answer is mostly off-topic or very unclear",
        "3": "Answer is somewhat relevant but lacks clarity",
        "4": "Answer is relevant and mostly clear",
        "5": "Answer directly addresses the question with excellent clarity"
    },
    "Technical Knowledge": {
        "description": "Demonstration of role-specific technical skills and knowledge",
        "1": "No technical knowledge demonstrated",
        "2": "Very basic or incorrect technical understanding",
        "3": "Some technical knowledge but with gaps",
        "4": "Good technical knowledge with minor gaps",
        "5": "Excellent technical knowledge and understanding"
    },
    "Communication Skills": {
        "description": "Ability to articulate thoughts clearly and professionally",
        "1": "Poor communication, difficult to understand",
        "2": "Basic communication with many issues",
        "3": "Adequate communication with some issues",
        "4": "Good communication with minor issues",
        "5": "Excellent communication skills"
    },
    "Problem-Solving Approach": {
        "description": "Logical thinking and systematic approach to problems",
        "1": "No logical approach or problem-solving skills",
        "2": "Weak problem-solving approach",
        "3": "Some logical thinking but incomplete approach",
        "4": "Good problem-solving approach",
        "5": "Excellent systematic problem-solving approach"
    },
    "Experience and Examples": {
        "description": "Use of relevant examples and practical experience",
        "1": "No examples or relevant experience mentioned",
        "2": "Very few or irrelevant examples",
        "3": "Some examples but not very relevant",
        "4": "Good examples with relevant experience",
        "5": "Excellent examples with rich relevant experience"
    }
}

ENHANCED_EVALUATION_PROMPT = """
You are an expert HR evaluator conducting technical and behavioral interviews.

EVALUATE the candidate's answer based on the following criteria (1-5 stars each):

{criteria_text}

QUESTION: "{question}"
CANDIDATE ANSWER: "{answer}"
ANSWER MODE: {mode}
ROLE: {role}
DESIGNATION: {designation}

EVALUATION INSTRUCTIONS:
1. Rate each criterion from 1-5 based on the descriptions provided
2. Consider the role context: {role} - {designation}
3. For audio answers, evaluate based on transcribed content
4. Be fair but thorough in assessment
5. Provide specific, actionable feedback

IMPORTANT: Return ONLY valid JSON in this exact format:
{{
  "Relevance and Clarity": <number 1-5>,
  "Technical Knowledge": <number 1-5>,
  "Communication Skills": <number 1-5>,
  "Problem-Solving Approach": <number 1-5>,
  "Experience and Examples": <number 1-5>,
  "Overall Score": <number 1-5>,
  "Strengths": ["strength1", "strength2"],
  "Areas for Improvement": ["improvement1", "improvement2"],
  "Detailed Feedback": "comprehensive feedback explaining the evaluation",
  "Recommendation": "brief recommendation for this candidate"
}}

Do not include any other text, only the JSON response.
"""

def clean_answer_text(answer):
    """Clean and normalize answer text for evaluation."""
    if not answer or answer.strip() == "":
        return ""
    
    # Remove extra whitespace and normalize
    cleaned = re.sub(r'\s+', ' ', answer.strip())
    
    # Handle common audio transcription artifacts
    cleaned = re.sub(r'\[.*?\]', '', cleaned)  # Remove [inaudible] type markers
    cleaned = re.sub(r'\(.*?\)', '', cleaned)  # Remove (background noise) type markers
    
    return cleaned

def detect_answer_quality(answer):
    """Detect if answer is too short, meaningless, or contains issues."""
    cleaned = clean_answer_text(answer)
    
    # Check for very short answers
    if len(cleaned) < 10:
        return False, "Answer is too short to evaluate properly"
    
    # Check for meaningless responses
    meaningless_patterns = [
        r'^\s*(i don\'t know|idk|no idea|not sure|maybe|perhaps)\s*$',
        r'^\s*(yes|no)\s*$',
        r'^\s*(ok|okay)\s*$',
        r'^\s*(skip|pass|next)\s*$'
    ]
    
    for pattern in meaningless_patterns:
        if re.match(pattern, cleaned.lower()):
            return False, "Answer is too brief or non-substantive"
    
    # Check for repetitive text
    words = cleaned.split()
    if len(words) > 3:
        unique_words = len(set(words))
        if unique_words / len(words) < 0.3:  # Less than 30% unique words
            return False, "Answer appears to be repetitive or nonsensical"
    
    return True, "Answer appears valid for evaluation"

def build_criteria_text():
    """Build detailed criteria text for the prompt."""
    criteria_text = ""
    for criterion, details in EVALUATION_CRITERIA.items():
        criteria_text += f"\n{criterion}:\n"
        criteria_text += f"Description: {details['description']}\n"
        for score, description in details.items():
            if score.isdigit():
                criteria_text += f"{score} star: {description}\n"
        criteria_text += "\n"
    return criteria_text

def extract_json_from_response(response_text):
    """Extract JSON from AI response, handling various formats."""
    try:
        # Try to find JSON in the response
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            json_str = json_match.group()
            return json.loads(json_str)
    except:
        pass
    
    # If no JSON found, try to parse the entire response
    try:
        return json.loads(response_text.strip())
    except:
        return None

def evaluate_answer(question, answer, role="", designation="", mode="text"):
    """
    Enhanced evaluation of candidate answers using AI.
    
    Args:
        question (str): The interview question
        answer (str): Candidate's answer (text or transcribed audio)
        role (str): Role context (IT/Non-IT)
        designation (str): Specific designation
        mode (str): Answer mode ("text" or "voice")
    
    Returns:
        dict: Comprehensive evaluation results
    """
    
    # Clean and validate answer
    cleaned_answer = clean_answer_text(answer)
    is_valid, validation_message = detect_answer_quality(cleaned_answer)
    
    if not is_valid:
        return {
            "Relevance and Clarity": 1,
            "Technical Knowledge": 1,
            "Communication Skills": 1,
            "Problem-Solving Approach": 1,
            "Experience and Examples": 1,
            "Overall Score": 1,
            "Strengths": [],
            "Areas for Improvement": [validation_message],
            "Detailed Feedback": f"Unable to evaluate: {validation_message}",
            "Recommendation": "Candidate should provide more detailed answers"
        }
    
    try:
        # Build enhanced prompt
        criteria_text = build_criteria_text()
        prompt = ENHANCED_EVALUATION_PROMPT.format(
            criteria_text=criteria_text,
            question=question.strip(),
            answer=cleaned_answer,
            mode=mode,
            role=role or "Professional",
            designation=designation or "Role"
        )
        
        # Generate evaluation with retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = model.generate_content(prompt)
                response_text = response.text.strip()
                
                # Extract JSON from response
                evaluation = extract_json_from_response(response_text)
                
                if evaluation and isinstance(evaluation, dict):
                    # Validate and normalize scores
                    validated_evaluation = {}
                    for criterion in EVALUATION_CRITERIA.keys():
                        score = evaluation.get(criterion, 1)
                        if isinstance(score, (int, float)) and 1 <= score <= 5:
                            validated_evaluation[criterion] = int(score)
                        else:
                            validated_evaluation[criterion] = 1
                    
                    # Calculate overall score
                    scores = [validated_evaluation[criterion] for criterion in EVALUATION_CRITERIA.keys()]
                    overall_score = sum(scores) / len(scores)
                    validated_evaluation["Overall Score"] = round(overall_score, 1)
                    
                    # Ensure other fields exist
                    validated_evaluation["Strengths"] = evaluation.get("Strengths", [])
                    validated_evaluation["Areas for Improvement"] = evaluation.get("Areas for Improvement", [])
                    validated_evaluation["Detailed Feedback"] = evaluation.get("Detailed Feedback", "Evaluation completed")
                    validated_evaluation["Recommendation"] = evaluation.get("Recommendation", "Standard evaluation")
                    
                    return validated_evaluation
                
            except Exception as e:
                print(f"Attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    raise e
                continue
        
        # If all retries failed, return manual evaluation
        return manual_evaluate_answer(question, cleaned_answer, role, designation)
        
    except Exception as e:
        print(f"Evaluation error: {e}")
        # Return manual evaluation for failed cases
        return manual_evaluate_answer(question, cleaned_answer, role, designation)

def manual_evaluate_answer(question, answer, role, designation):
    """Manual evaluation fallback when AI fails."""
    # Basic scoring based on answer length and content
    answer_length = len(answer)
    word_count = len(answer.split())
    
    # Score based on answer quality indicators
    if answer_length < 50:
        base_score = 1
    elif answer_length < 100:
        base_score = 2
    elif answer_length < 200:
        base_score = 3
    elif answer_length < 300:
        base_score = 4
    else:
        base_score = 5
    
    # Role-specific keyword analysis
    if role == "IT":
        tech_keywords = ['java', 'python', 'database', 'api', 'framework', 'git', 'testing', 'deployment', 'code', 'programming', 'software', 'development']
        tech_count = sum(1 for keyword in tech_keywords if keyword.lower() in answer.lower())
        if tech_count >= 3:
            base_score = min(5, base_score + 1)
        
        # IT-specific feedback
        if base_score <= 2:
            feedback = "Answer lacks technical depth. Provide more specific technical details and examples."
            improvements = ["Include specific programming languages or technologies", "Mention technical tools and frameworks", "Provide code examples or technical scenarios"]
            strengths = ["Attempted to answer the question"]
        elif base_score <= 3:
            feedback = "Basic technical understanding shown but needs more depth."
            improvements = ["Add more technical specifications", "Include specific tools or technologies", "Provide technical examples"]
            strengths = ["Clear communication", "Basic technical knowledge demonstrated"]
        else:
            feedback = "Good technical answer with relevant details and examples."
            improvements = ["Consider adding more advanced technical concepts", "Include specific project examples with technical details"]
            strengths = ["Good technical knowledge", "Clear communication", "Relevant examples provided"]
    
    elif role == "Non-IT":
        # Non-IT keywords for different designations
        hr_keywords = ['recruitment', 'onboarding', 'employee', 'policy', 'payroll', 'attendance', 'engagement', 'training', 'performance']
        sales_keywords = ['customer', 'client', 'sales', 'target', 'revenue', 'negotiation', 'relationship', 'market', 'product']
        marketing_keywords = ['campaign', 'brand', 'social media', 'content', 'analytics', 'strategy', 'audience', 'engagement']
        
        # Check designation-specific keywords
        if 'hr' in designation.lower() or 'human resource' in designation.lower():
            relevant_keywords = hr_keywords
        elif 'sales' in designation.lower():
            relevant_keywords = sales_keywords
        elif 'marketing' in designation.lower():
            relevant_keywords = marketing_keywords
        else:
            relevant_keywords = hr_keywords + sales_keywords + marketing_keywords
        
        keyword_count = sum(1 for keyword in relevant_keywords if keyword.lower() in answer.lower())
        if keyword_count >= 2:
            base_score = min(5, base_score + 1)
        
        # Non-IT specific feedback
        if base_score <= 2:
            feedback = "Answer is too brief. Provide more detailed explanations with specific examples from your field."
            improvements = ["Expand your answer with role-specific examples", "Include specific processes or procedures you follow", "Mention relevant tools or software you use"]
            strengths = ["Attempted to answer the question"]
        elif base_score <= 3:
            feedback = "Answer shows basic understanding but could be more detailed with specific examples."
            improvements = ["Add more specific examples from your experience", "Include details about tools or processes you use", "Mention specific challenges and how you handle them"]
            strengths = ["Clear communication", "Basic understanding demonstrated"]
        else:
            feedback = "Good answer with relevant details and examples from your field."
            improvements = ["Consider adding more specific project examples", "Include metrics or results from your work", "Mention any innovative approaches you've used"]
            strengths = ["Good communication", "Relevant knowledge", "Clear examples provided"]
    
    else:
        # Generic professional feedback
        if base_score <= 2:
            feedback = "Answer is too brief. Provide more detailed explanations with examples."
            improvements = ["Expand your answer with specific examples", "Include details about your approach", "Mention relevant tools or methods"]
            strengths = ["Attempted to answer the question"]
        elif base_score <= 3:
            feedback = "Answer shows basic understanding but could be more detailed."
            improvements = ["Add more specific examples", "Include details about your process", "Mention specific tools or methods"]
            strengths = ["Clear communication", "Basic understanding demonstrated"]
        else:
            feedback = "Good answer with relevant details and examples."
            improvements = ["Consider adding more specific examples", "Include results or outcomes", "Mention any best practices you follow"]
            strengths = ["Good communication", "Relevant knowledge", "Clear examples provided"]
    
    return {
        "Relevance and Clarity": base_score,
        "Technical Knowledge": base_score,
        "Communication Skills": base_score,
        "Problem-Solving Approach": base_score,
        "Experience and Examples": base_score,
        "Overall Score": float(base_score),
        "Strengths": strengths,
        "Areas for Improvement": improvements,
        "Detailed Feedback": feedback,
        "Recommendation": "Continue improving with more detailed responses"
    }

def evaluate_audio_answer(question, transcribed_audio, role="", designation=""):
    """
    Specialized evaluation for audio answers.
    
    Args:
        question (str): The interview question
        transcribed_audio (str): Transcribed audio content
        role (str): Role context
        designation (str): Specific designation
    
    Returns:
        dict: Evaluation results with audio-specific considerations
    """
    
    # Use the main evaluation function with audio mode
    evaluation = evaluate_answer(question, transcribed_audio, role, designation, "voice")
    
    # Add audio-specific feedback if needed
    if "Communication Skills" in evaluation:
        comm_score = evaluation["Communication Skills"]
        if comm_score <= 2:
            evaluation["Areas for Improvement"].append("Consider improving voice clarity and confidence in verbal communication")
        elif comm_score >= 4:
            evaluation["Strengths"].append("Good verbal communication skills demonstrated")
    
    return evaluation

# Legacy compatibility function
def evaluate_answer_legacy(question, answer):
    """Legacy function for backward compatibility."""
    return evaluate_answer(question, answer)