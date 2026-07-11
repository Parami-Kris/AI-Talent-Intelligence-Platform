import json
import os
import re

import httpx

from backend.app.query_expansion_repository import get_cached_expansion, save_expansion

ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"
JOOBLE_BASE_URL = "https://jooble.org/api"
REMOTIVE_BASE_URL = "https://remotive.com/api/remote-jobs"
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
MAX_RELATED_TITLES = 3


def _strip_html(text: str | None) -> str | None:
    if not text:
        return text
    return re.sub(r"<[^>]+>", " ", text).strip()


def _search_adzuna(query: str, location: str | None, country: str, page: int, results_per_page: int) -> list[dict]:
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return []

    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results_per_page,
        "what": query,
        "content-type": "application/json",
    }
    if location:
        params["where"] = location

    try:
        response = httpx.get(f"{ADZUNA_BASE_URL}/{country}/search/{page}", params=params, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    data = response.json()
    return [
        {
            "source": "adzuna",
            "id": str(job.get("id", "")),
            "title": job.get("title"),
            "company": (job.get("company") or {}).get("display_name"),
            "location": (job.get("location") or {}).get("display_name"),
            "description": _strip_html(job.get("description")),
            "url": job.get("redirect_url"),
            "posted_at": job.get("created"),
        }
        for job in data.get("results", [])
    ]


def _search_jooble(query: str, location: str | None, page: int) -> list[dict]:
    api_key = os.environ.get("JOOBLE_API_KEY")
    if not api_key:
        return []

    payload: dict = {"keywords": query, "page": str(page)}
    if location:
        payload["location"] = location

    try:
        response = httpx.post(f"{JOOBLE_BASE_URL}/{api_key}", json=payload, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    data = response.json()
    return [
        {
            "source": "jooble",
            "id": str(job.get("id") or job.get("link", "")),
            "title": job.get("title"),
            "company": job.get("company"),
            "location": job.get("location"),
            "description": _strip_html(job.get("snippet")),
            "url": job.get("link"),
            "posted_at": job.get("updated"),
        }
        for job in data.get("jobs", [])
    ]


def _search_remotive(query: str) -> list[dict]:
    try:
        response = httpx.get(REMOTIVE_BASE_URL, params={"search": query}, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    data = response.json()
    return [
        {
            "source": "remotive",
            "id": str(job.get("id", "")),
            "title": job.get("title"),
            "company": job.get("company_name"),
            "location": job.get("candidate_required_location"),
            "description": _strip_html(job.get("description")),
            "url": job.get("url"),
            "posted_at": job.get("publication_date"),
        }
        for job in data.get("jobs", [])
    ]


def _expand_query_via_groq(query: str) -> list[str]:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return []

    prompt = (
        f"A job seeker is searching for {query!r} roles. List up to {MAX_RELATED_TITLES} other job "
        "titles they would also be a strong fit for and should search, including titles that use "
        "different wording for a similar role (for example, for \"ML Engineer\" include \"Applied "
        "Scientist\"). Respond with only a JSON object of the form {\"titles\": [\"...\", \"...\"]}."
    )

    try:
        response = httpx.post(
            GROQ_BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 200,
                "response_format": {"type": "json_object"},
            },
            timeout=15,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        titles = json.loads(content).get("titles", [])
        return [str(title) for title in titles if title][:MAX_RELATED_TITLES]
    except (httpx.HTTPError, KeyError, IndexError, TypeError, json.JSONDecodeError):
        return []


def expand_query(query: str) -> list[str]:
    normalized = query.strip().lower()
    if not normalized:
        return []

    try:
        cached = get_cached_expansion(normalized)
        if cached is not None:
            return cached
    except Exception:
        # MySQL unavailable shouldn't block search - fall through and expand uncached.
        return _expand_query_via_groq(query)

    related_titles = _expand_query_via_groq(query)
    try:
        save_expansion(normalized, related_titles)
    except Exception:
        pass
    return related_titles


def search_jobs(
    query: str,
    location: str | None = None,
    country: str = "us",
    page: int = 1,
    results_per_page: int = 10,
) -> dict:
    related_titles = expand_query(query)
    all_queries = [query] + [title for title in related_titles if title.strip().lower() != query.strip().lower()]

    seen: set[tuple[str, str]] = set()
    results: list[dict] = []
    for search_term in all_queries:
        batch = (
            _search_adzuna(search_term, location, country, page, results_per_page)
            + _search_jooble(search_term, location, page)
            + _search_remotive(search_term)
        )
        for job in batch:
            key = (job["source"], job["id"])
            if key in seen:
                continue
            seen.add(key)
            results.append(job)

    return {"count": len(results), "results": results, "expanded_titles": related_titles}
