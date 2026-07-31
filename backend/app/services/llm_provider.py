import json
import os

import httpx

MISTRAL_BASE_URL = "https://api.mistral.ai/v1/chat/completions"
# Pinned to this exact dated snapshot deliberately - the account this was set up
# against showed a 20x higher TPM ceiling on mistral-small-2506 than on the newer
# mistral-small-2603 (2,250,000 vs 50,000, confirmed via the Mistral Admin
# Console's Limits page, which isn't otherwise publicly documented). Don't bump
# this to a "-latest" alias without re-checking the console - other snapshots
# may not carry the same free-tier limits.
MISTRAL_MODEL = "mistral-small-2506"

GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


def _call_mistral(prompt: str, max_tokens: int) -> dict | None:
    api_key = os.environ.get("MISTRAL_API_KEY")
    if not api_key:
        return None

    try:
        response = httpx.post(
            MISTRAL_BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": MISTRAL_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None


def _call_groq(prompt: str, max_tokens: int) -> dict | None:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None

    try:
        response = httpx.post(
            GROQ_BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return json.loads(content)
    except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None


def chat_completion_json(prompt: str, max_tokens: int = 2000) -> dict | None:
    """Shared provider for the job-matching and resume-tailoring features:
    Mistral first (primary, see MISTRAL_MODEL comment above), Groq as fallback
    if Mistral errors, has no key configured, or its response doesn't parse as
    JSON. Returns None (never raises) if both fail or neither key is set, so
    callers degrade gracefully the same way job_search_service.py's Groq query
    expansion already does - a missing/failed LLM call skips the feature, not
    the whole request.
    """
    result = _call_mistral(prompt, max_tokens)
    if result is not None:
        return result
    return _call_groq(prompt, max_tokens)
