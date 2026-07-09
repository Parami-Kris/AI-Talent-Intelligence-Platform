import json
import os
import logging
from dotenv import load_dotenv
from google import genai

load_dotenv()
# logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

MODEL_ID = os.getenv("GENAI_MODEL", "gemini-2.5-flash")
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

def extract_structured_resume(text):
    prompt = f"""
    You are an expert resume parser. Extract the following information from the resume text:
    Return ONLY valid JSON.
    Do not wrap in ```json blocks.
    Do not include explanations.

    Schema:
    {{
        "name": "Full Name",
        "raw_skills": ["Skill1", "Skill2", ...],
        "normalized_skills": ["Normalized Skill1", "Normalized Skill2", ...],
        "skill_categories": {{
            "Category1": ["SkillA", "SkillB", ...]
        }},
        "education": [
            {{
                "degree": "Degree Name",
                "institution": "Institution Name",
                "year": "Graduation Year"
            }},
            ...
        ],
        "experience": [
            {{
                "job_title": "Job Title",
                "company": "Company Name",
                "duration": "Duration of Employment",
                "description": "Brief Description of Role"
            }},
            ...
        ],
        "projects": [
            {{
                "name": "Project Name",
                "description": "Brief Description of Project",
                "technologies": ["Tech1", "Tech2", ...]
            }},
            ...
        ],
        "certifications": [
            {{
                "name": "Certification Name",
                "issuer": "Issuing Organization", (optional)
                "year": "Year Obtained" (optional)
            }},
            ...
        ]
    }}

    Instructions:
    1) raw skills: Extract skills as they appear in the resume.

    2) normalized skills: Map raw skills to canonical, full technology or
    capability names (e.g. "JS" -> "JavaScript", "Py" -> "Python").
    Expand abbreviations and use official names consistently. Do not include
    both an abbreviation and its expanded form.
    
    3) skill categories: Group normalized skills into categories (e.g. "Programming Languages", "Frameworks", "Tools").

    Resume:
    {text}
    """
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    cleaned_response = response.text.replace("```json", "").replace("```", "").strip()

    try:
        structured_data = json.loads(cleaned_response)
        logger.info("Successfully parsed structured resume data")
        return structured_data
    except json.JSONDecodeError as e:
        logger.error("Error parsing JSON from model response", exc_info=True)
        return {"error": str(e), "raw_response": cleaned_response}
