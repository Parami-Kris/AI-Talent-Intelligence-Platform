import json
import os
from typing import Any

from backend.app.services.llm_provider import chat_completion_json

# Single batch, no multi-call chunking in v1 - deliberately caps how many jobs
# one request scores rather than fanning out multiple LLM calls per search.
JOB_MATCH_BATCH_CAP = 25

# Neither Mistral's nor Groq's exact daily ceiling is fully confirmed (Mistral
# doesn't publish one; Groq's is shared org-wide, not per-user) - rather than
# derive a precise number from incomplete data, this is a plain configurable
# constant enforced by our own job_match_usage table. Bump via env var if real
# usage data says otherwise; the Mistral->Groq fallback in llm_provider.py is
# the actual safety net if a provider's true ceiling is lower than expected.
JOB_MATCH_DAILY_LIMIT = int(os.environ.get("JOB_MATCH_DAILY_LIMIT", "100"))

# Bounds prompt tokens regardless of batch size - full job descriptions can be
# long, and this is a batched call (many jobs per request), not a per-job one.
_DESCRIPTION_CHAR_LIMIT = 600


def _truncate(text: str | None, limit: int = _DESCRIPTION_CHAR_LIMIT) -> str:
    if not text:
        return ""
    return text if len(text) <= limit else text[:limit] + "..."


def _resume_summary_for_prompt(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "skills": candidate.get("normalized_skills") or candidate.get("raw_skills") or [],
        "experience": [
            {
                "job_title": item.get("job_title"),
                "duration": item.get("duration"),
                "description": _truncate(item.get("description"), 300),
            }
            for item in candidate.get("experience", [])
        ],
        "education": candidate.get("education", []),
    }


def score_jobs_for_resume(candidate: dict[str, Any], jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Batches up to JOB_MATCH_BATCH_CAP jobs into a single LLM call scoring each
    against the resume - one call for many jobs, not one call per job, same
    batching shape pipeline/shortlist_reranker.py uses on the recruiter side.

    Returns the (possibly truncated to the batch cap) jobs list with
    match_percentage/match_reason attached. If the LLM call fails entirely,
    every job gets match_percentage=None so the caller/UI can distinguish
    "scored low" from "couldn't score" rather than silently dropping results.
    """
    batch = jobs[:JOB_MATCH_BATCH_CAP]
    if not batch:
        return []

    payload = [
        {
            "job_index": index,
            "title": job.get("title"),
            "company": job.get("company"),
            "description": _truncate(job.get("description")),
        }
        for index, job in enumerate(batch)
    ]

    prompt = f"""
You are scoring how well a job seeker's resume matches each job listing below.

Candidate resume summary:
{json.dumps(_resume_summary_for_prompt(candidate), indent=2)}

Job listings:
{json.dumps(payload, indent=2)}

For each job, score 0-100 how well the candidate's actual skills and experience
match the listing's stated requirements - base this on the listing text given,
not assumptions about the role title alone.

Return ONLY valid JSON as an object with a "scores" key, one entry per job,
preserving job_index:

{{
  "scores": [
    {{"job_index": 0, "match_percentage": 0, "match_reason": "Short evidence-based explanation"}}
  ]
}}
"""
    raw = chat_completion_json(prompt, max_tokens=2500)
    scores_by_index: dict[int, dict[str, Any]] = {}
    if isinstance(raw, dict):
        for item in raw.get("scores", []):
            if isinstance(item, dict) and isinstance(item.get("job_index"), int):
                scores_by_index[item["job_index"]] = item

    scored = []
    for index, job in enumerate(batch):
        score = scores_by_index.get(index)
        scored.append(
            {
                **job,
                "match_percentage": score.get("match_percentage") if score else None,
                "match_reason": score.get("match_reason") if score else None,
            }
        )
    return scored
