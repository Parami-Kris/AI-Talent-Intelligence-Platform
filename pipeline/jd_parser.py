import json
import os
import logging
from dotenv import load_dotenv
from google import genai

from backend.app.utils.llm_json import parse_llm_json

load_dotenv()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format="%(asctime)s %(levelname)s %(name)s: %(message)s")

logger = logging.getLogger(__name__)

MODEL_ID = os.getenv("GENAI_MODEL", "gemini-2.5-flash")
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY")) 

def extract_structured_jd(text):
    prompt = f"""
    You are an expert recruiter.
    Extract information from the job description below:
    Return ONLY valid JSON.
    Do not wrap in ```json blocks. 

    Schema:
    {{
        "job_title": "",
        "required_skills": ["Skill1", "Skill2", ...],
        "preferred_skills": ["SkillA", "SkillB", ...],
        "skill_categories": {{
            "Category1": ["SkillX", "SkillY", ...]
        }},
        "experience_required": "X years",
        "education_required": "Degree or Certification",
        "responsibilities": []
    }}

    Skill naming:
    - Write required_skills and preferred_skills using canonical, full
      technology or capability names.
    - Expand abbreviations and use official names consistently.
    - Do not include both an abbreviation and its expanded form.

    Job Description:
    {text}
    """

    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    return parse_llm_json(response.text)

if __name__ == "__main__":
    try:
        logger.info("Starting job description parsing pipeline")
        with open("job_description.txt", "r",encoding="utf-8") as f:
            jd_text = f.read()
        data = extract_structured_jd(jd_text)
        with open("parsed_jd.json", "w") as f:
            json.dump(data, f, indent=4)
        print("Parsed JD data:", json.dumps(data, indent=4))
    except Exception as e:
        logger.exception("An error occurred during parsing: %s", e)
