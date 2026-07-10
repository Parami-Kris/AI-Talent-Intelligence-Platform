from docling.document_converter import DocumentConverter
from pipeline.llm_parser import extract_structured_resume
import re
import json
import logging
import os
from dotenv import load_dotenv

load_dotenv()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

def extract_text(file_path):
    converter = DocumentConverter()
    result = converter.convert(file_path)
    return result.document.export_to_text()

def extract_email(text):
    emails = re.findall(r'[\w\.-]+@[\w\.-]+',text)
    return emails[0] if emails else None

def extract_phone(text):
    phn = re.findall(r'\+?\d[\d -]{10,}\d',text)
    return phn[0] if phn else None

def extract_links(text):
    links = re.findall(r'https?://[^\s]+', text)
    
    linkedin = [l for l in links if "linkedin" in l.lower()]
    github = [l for l in links if "github" in l.lower()]
    return {"all": links, "linkedin": linkedin if linkedin else None, "github": github if github else None}


if __name__ == "__main__":
    try:
        logger.info("Starting resume parsing pipeline")
        txt = extract_text("Parami_Resume.pdf")
        logger.info("Extracted text from document (length=%d)", len(txt) if txt else 0)

        links = extract_links(txt)

        llm_data = extract_structured_resume(txt)
        logger.info("LLM parsing completed")

        data = {
            "name": llm_data.get("name"),

            "email": extract_email(txt),
            "phone": extract_phone(txt),
            
            "linkedin": links["linkedin"],
            "github": links["github"],
            
            "raw_skills": llm_data.get("raw_skills"),
            "normalized_skills": llm_data.get("normalized_skills"),
            "skill_categories": llm_data.get("skill_categories"),
            
            "education": llm_data.get("education"),
            "experience": llm_data.get("experience"),
            "projects": llm_data.get("projects"),
            "certifications": llm_data.get("certifications")
        }

        with open("candidate_profiles.json", "w") as f:
            json.dump(data, f, indent=4)
        logger.info("Wrote parsed data to candidate_profiles.json")
        logger.debug("Parsed data: %s", json.dumps(data))
    except Exception:
        logger.exception("Unexpected error during parsing pipeline")