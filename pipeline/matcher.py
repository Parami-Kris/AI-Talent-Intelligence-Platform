from google import genai
from dotenv import load_dotenv
import os
import json
import re
from datetime import date

from backend.app.utils.llm_json import parse_llm_json

load_dotenv()

MODEL_ID = os.getenv("GENAI_MODEL", "gemini-2.5-flash")
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

with open("parsed_jd.json", "r") as f:
    jd_data = json.load(f)

with open("candidate_profiles.json", "r") as f:
    candidate_data = json.load(f)

def normalize_skill(skill):
    return re.sub(r"[^a-z0-9]+", "", skill.lower())


def contains_skill_text(text, skill):
    if not text:
        return False

    text = str(text)
    normalized_text = normalize_skill(text)
    normalized_skill = normalize_skill(skill)

    if not normalized_skill:
        return False

    return (
        re.search(rf"(?<![A-Za-z0-9]){re.escape(skill)}(?![A-Za-z0-9])", text, re.IGNORECASE)
        is not None
        or normalized_skill in normalized_text
    )


def skill_evidence(resume, skill):
    evidence = []

    for raw_skill in resume.get("raw_skills", []):
        if normalize_skill(raw_skill) == normalize_skill(skill):
            evidence.append(f"{raw_skill} listed in raw skills")
            break

    for normalized_skill in resume.get("normalized_skills", []):
        if normalize_skill(normalized_skill) == normalize_skill(skill):
            evidence.append(f"{normalized_skill} listed in normalized skills")
            break

    for experience in resume.get("experience", []):
        description = experience.get("description", "")
        if contains_skill_text(description, skill):
            role = experience.get("job_title", "experience")
            company = experience.get("company", "").strip()
            label = f"{role} at {company}" if company else role
            evidence.append(f"{skill} mentioned in {label}")
            break

    for project in resume.get("projects", []):
        project_text = json.dumps(project)
        if contains_skill_text(project_text, skill):
            title = project.get("title") or project.get("name") or "project"
            evidence.append(f"{skill} shown in {title}")
            break

    return evidence or [f"{skill} matched from resume skills"]


def skill_match(resume,jd):
    resume_skills = {
        normalize_skill(skill): skill
        for skill in (resume.get("normalized_skills") or [])
    }
    jd_required = set(jd.get("required_skills") or [])
    jd_preferred = set(jd.get("preferred_skills") or [])

    common_skills = {
        skill for skill in jd_required
        if normalize_skill(skill) in resume_skills
    }
    preferred_skills = {
        skill for skill in jd_preferred
        if normalize_skill(skill) in resume_skills
    }
    
    denominator = len(jd_required) * 2 + len(jd_preferred)
    score = (
        (len(common_skills) * 2 + len(preferred_skills)) / denominator * 100
        if denominator
        else 0
    )
    return {
        "score": round(score, 2),
        "common_skills": list(common_skills),
        "required_skills": list(jd_required),
        "preferred_skills": list(preferred_skills),
        "matched": sorted(common_skills | preferred_skills),
        "missing": sorted(
            skill for skill in jd_required | jd_preferred
            if normalize_skill(skill) not in resume_skills
        ),
        "evidence": [
            item
            for skill in sorted(common_skills | preferred_skills)
            for item in skill_evidence(resume, skill)
        ]
    }

def education_match(resume,jd):
    jd_edu = (jd.get("education_required") or "").strip()
    
    if not jd_edu:
        return {
            "score": None,
            "status": "not_specified",
            "reason": "No education requirement specified in the job description.",
            "matched": [],
            "missing": [],
            "evidence": ["The job description does not specify an education requirement."]
        }
    prompt = f"""
You are evaluating a candidate's education against a job requirement.

Candidate education:
{json.dumps(resume.get("education", []), indent=2)}

Job education requirement:
{jd_edu}

Consider:
- Degree or qualification level
- Relevant field of study
- Equivalent qualifications
- Certifications explicitly accepted by the requirement
- Do not assume unstated qualifications

Return ONLY valid JSON:

{{
  "score": X,
  "status": "matched|partially_matched|not_matched",
  "reason": "Short evidence-based explanation",
  "matched": ["Education requirements the candidate meets"],
  "missing": ["Education requirements the candidate does not meet"],
  "evidence": ["Specific degree, institution, certification, or resume fact"]
}}
"""

    response = client.models.generate_content(model=MODEL_ID,contents=prompt)
    return parse_llm_json(response.text)

def experience_match(resume,jd):
    prompt = f"""
    You are an expert recruiter.
    Current date: {date.today().isoformat()}
    Candidate's experience:
    {resume.get("experience", [])}
    Job description experience requirement:
    {jd.get("experience_required", "")}
    Evaluate:
    1. Relevance of work.
    2. Years of experience.
    3. Similarity to JD requirements.

    Return ONLY valid JSON:

    {{
        "score": X,
        "relevance": "High/Medium/Low",
        "years_experience": Y,
        "matches_requirements": true/false,
        "matched": ["Experience requirements demonstrated by the candidate"],
        "missing": ["Experience requirements not demonstrated by the candidate"],
        "evidence": ["Specific role, duration, responsibility, or project"]
    }}
    """
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    return parse_llm_json(response.text)


def eligibility_match(skill_result, exp_result):
    required_skills = set(skill_result.get("required_skills", []))
    matched_skills = set(skill_result.get("common_skills", []))

    return {
        "meets_experience": exp_result.get("matches_requirements", False),
        "missing_must_haves": sorted(required_skills - matched_skills)
    }



def analyze_match(resume, jd, scores):
    prompt = f"""
    You are an expert recruiter.
    Candidate Resume:
    {json.dumps(resume, indent=4)}

    Job Description:
    {json.dumps(jd, indent=4)}

    Match Scores:
    {json.dumps(scores, indent=4)}

    Generate:
    {{
        "overall_fit": "High/Medium/Low",
        "strengths": ["Strength1", "Strength2", ...],
        "weaknesses": ["Weakness1", "Weakness2", ...]       
    }}

    Maximum 3 strengths and 3 weaknesses

    Return ONLY valid JSON.
    """
    response = client.models.generate_content(model=MODEL_ID, contents=prompt)
    return parse_llm_json(response.text)

def overall_match(skill_result,edu_result,exp_result):

    if edu_result["score"] is None:
        overall_score = (skill_result["score"] * 0.625) + (exp_result["score"] * 0.375)
    else:
        overall_score = (skill_result["score"] * 0.5) + (edu_result["score"] * 0.2) + (exp_result["score"] * 0.3)
    
    return {
        "overall_score": round(overall_score, 2),
        "skill_match": skill_result,
        "education_match": edu_result,
        "experience_match": exp_result
    }

if __name__ == "__main__":
    skill_result = skill_match(candidate_data, jd_data)
    edu_result = education_match(candidate_data, jd_data)
    exp_result = experience_match(candidate_data, jd_data)

    for label, result in (("education", edu_result), ("experience", exp_result)):
        if isinstance(result, dict) and "error" in result:
            raise SystemExit(f"Failed to parse LLM {label} match response: {result['error']}")

    overall_result = overall_match(skill_result, edu_result, exp_result)
    eligibility = eligibility_match(skill_result, exp_result)
    
    scores = {
        "skills": skill_result,
        "experience": exp_result,
        "education": edu_result
    }
    analysis = analyze_match(candidate_data, jd_data, scores)
    final_result = {
        "eligibility": eligibility,
        "match_scores": scores,
        "overall_score": overall_result["overall_score"],
        "strengths": analysis.get("strengths", []),
        "weaknesses": analysis.get("weaknesses", [])
    }
    with open("match_analysis.json", "w") as f:
        json.dump(final_result, f, indent=4)
    print("Match Analysis:", json.dumps(final_result, indent=4))
