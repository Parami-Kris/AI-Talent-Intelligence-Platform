import json
from typing import Any

from backend.app.services.llm_provider import chat_completion_json
from backend.app.services.profile_gap_service import analyze_profile_gap


def _candidate_for_prompt(candidate: dict[str, Any]) -> dict[str, Any]:
    # raw_text is the full original resume blob - the structured fields below
    # already carry the meaningful content for this task, so including both
    # would just double token cost with no proportional value.
    return {key: value for key, value in candidate.items() if key not in ("raw_text",)}


def tailor_resume(
    jd: dict[str, Any],
    candidate: dict[str, Any],
    target_role: str | None = None,
) -> dict[str, Any]:
    """Rewrites the candidate's resume content for one specific job. Grounds
    the LLM call in analyze_profile_gap's existing deterministic gap analysis
    (backend/app/services/profile_gap_service.py) for context, then asks for
    two specific transformations - see the prompt below - both constrained to
    what's actually in the source resume, never inventing experience or
    skills. Returns tailored_resume_text=None (and an empty changes list) if
    the LLM call fails entirely (both providers down/unconfigured), rather
    than raising - the route decides how to surface that to the user.
    """
    gap = analyze_profile_gap(jd, candidate, target_role)

    prompt = f"""
You are tailoring a job seeker's resume for one specific job listing.

Job description:
{json.dumps(jd, indent=2)}

Candidate's full resume data:
{json.dumps(_candidate_for_prompt(candidate), indent=2)}

Deterministic fit analysis already computed for this pairing (context only - don't just repeat it verbatim):
{json.dumps(gap["qualification_gaps"], indent=2)}

Rewrite the resume content for this job in two specific ways:

1. Rephrase the professional summary and reorder/emphasize experience bullet
   points to foreground what's most relevant to this job's stated
   requirements and responsibilities.

2. Surface missing skills: read the candidate's experience and project
   descriptions carefully. If a skill this job requires or prefers is
   genuinely demonstrated there but not already listed in the candidate's
   skills, add it to the tailored skills list. This must be a contextual
   read of what the work actually involved, not a keyword search. For
   example: "built REST APIs with Flask and deployed them on AWS" genuinely
   demonstrates Flask and AWS, so add those if relevant to this job - but the
   word "container" appearing somewhere does NOT by itself demonstrate
   "Kubernetes", so do not add that. Never invent a skill or experience that
   isn't genuinely evidenced somewhere in the resume data above.

Return ONLY valid JSON:
{{
  "tailored_resume_text": "The full tailored resume as plain formatted text (summary, skills, experience with dates/companies/bullets, education) - ready to copy into a document.",
  "summary_of_changes": ["One line per meaningful change, e.g. 'Added Flask to skills - demonstrated in your Acme Corp role' or 'Reordered experience to lead with the most relevant project.'"]
}}
"""
    result = chat_completion_json(prompt, max_tokens=3000)
    if result is None:
        return {"tailored_resume_text": None, "summary_of_changes": []}

    return {
        "tailored_resume_text": result.get("tailored_resume_text"),
        "summary_of_changes": result.get("summary_of_changes", []),
    }
