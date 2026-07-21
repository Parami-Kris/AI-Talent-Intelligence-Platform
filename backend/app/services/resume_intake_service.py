from typing import Any, Callable

from pipeline.jd_parser import extract_structured_jd
from pipeline.llm_parser import extract_structured_resume
from pipeline.parser import extract_email, extract_links, extract_phone

from backend.app.services.input_service import extract_text_from_upload


def parse_resume_upload(content: bytes, filename: str) -> dict[str, Any]:
    text = extract_text_from_upload(content, filename)
    llm_data = extract_structured_resume(text)

    if "error" in llm_data:
        raise ValueError(f"Failed to parse resume '{filename}': {llm_data['error']}")

    links = extract_links(text)

    return {
        "name": llm_data.get("name"),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "linkedin": links["linkedin"],
        "github": links["github"],
        "raw_skills": llm_data.get("raw_skills"),
        "normalized_skills": llm_data.get("normalized_skills"),
        "skill_categories": llm_data.get("skill_categories"),
        "education": llm_data.get("education"),
        "experience": llm_data.get("experience"),
        "projects": llm_data.get("projects"),
        "certifications": llm_data.get("certifications"),
        "raw_text": text,
    }


def parse_jd_upload(content: bytes, filename: str) -> dict[str, Any]:
    text = extract_text_from_upload(content, filename)
    jd = extract_structured_jd(text)

    if "error" in jd:
        raise ValueError(f"Failed to parse job description '{filename}': {jd['error']}")

    return jd


def parse_resumes_batch(
    files: list[tuple[bytes, str]],
    on_progress: Callable[..., None] | None = None,
) -> dict[str, Any]:
    candidates = []
    failures = []

    for content, filename in files:
        if on_progress:
            on_progress(current_filename=filename)
        try:
            candidates.append(parse_resume_upload(content, filename))
        except Exception as exc:
            failures.append({"filename": filename, "reason": str(exc)})
        if on_progress:
            on_progress(processed_increment=True)

    return {"candidates": candidates, "failures": failures}