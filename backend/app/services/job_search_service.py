import html as html_module
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from backend.app.candidate_job_events_repository import get_recommended_query, log_event
from backend.app.query_expansion_repository import get_cached_expansion, save_expansion

SERPAPI_BASE_URL = "https://serpapi.com/search"
BRIGHT_DATA_REQUEST_URL = "https://api.brightdata.com/request"
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
MAX_RELATED_TITLES = 3


def _strip_tag_html(raw_tag_str: str) -> str:
    # BeautifulSoup's get_text() unreliably returns empty strings against this
    # page's markup (confirmed against live responses) - stringify the tag and
    # strip markup manually instead.
    inner = re.sub(r"^<span[^>]*>|</span>$", "", raw_tag_str)
    inner = re.sub(r"<br\s*/?>", "\n", inner)
    inner = re.sub(r"<[^>]+>", " ", inner)
    return html_module.unescape(inner).strip()


def _search_serpapi(query: str, location: str | None, country: str, results_per_page: int) -> list[dict] | None:
    """Returns None (not []) on failure/quota-exhaustion so the caller can fall back to Bright Data."""
    api_key = os.environ.get("SERP_API_KEY")
    if not api_key:
        return None

    params = {"engine": "google_jobs", "q": query, "gl": country, "hl": "en", "api_key": api_key}
    if location:
        params["location"] = location

    try:
        response = httpx.get(SERPAPI_BASE_URL, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, json.JSONDecodeError):
        return None

    if "error" in data:
        return None

    results = []
    for job in data.get("jobs_results", [])[:results_per_page]:
        apply_options = job.get("apply_options") or []
        url = apply_options[0]["link"] if apply_options else job.get("share_link")
        results.append(
            {
                "source": "serpapi",
                "id": str(job.get("job_id", "")),
                "title": job.get("title"),
                "company": job.get("company_name"),
                "location": job.get("location"),
                "description": job.get("description"),
                "url": url,
                "posted_at": (job.get("detected_extensions") or {}).get("posted_at"),
            }
        )
    return results


def _search_bright_data(query: str, location: str | None, country: str, results_per_page: int) -> list[dict]:
    """Fallback for when SerpApi's quota is exhausted. Uses Bright Data's Web
    Unlocker product to fetch Google's Jobs vertical (udm=8) and parses the
    HTML directly - Google preloads full descriptions for every job on the
    page (confirmed live), just CSS-hidden until clicked, which a plain SERP
    API static fetch does not expose but Web Unlocker's full render does.
    More fragile than SerpApi (tied to Google's current markup) - only used
    as a fallback, not primary, for that reason.
    """
    api_key = os.environ.get("BRIGHT_DATA_API_KEY")
    zone = os.environ.get("BRIGHT_DATA_SERP_ZONE")
    if not api_key or not zone:
        return []

    search_text = f"{query} {location}" if location else query
    target_url = f"https://www.google.com/search?q={quote_plus(search_text)}&gl={country}&hl=en&udm=8"

    try:
        response = httpx.post(
            BRIGHT_DATA_REQUEST_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"zone": zone, "url": target_url, "format": "raw"},
            timeout=90,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return []

    try:
        soup = BeautifulSoup(response.text, "lxml")
    except Exception:
        return []

    results = []
    for description_span in soup.find_all("span", attrs={"jsname": "QAWWu"}):
        detail_card = next((p for p in description_span.parents if p.has_attr("data-title")), None)
        if detail_card is None:
            continue

        continuation_span = detail_card.find("span", attrs={"jsname": "ij8cu"})
        description = _strip_tag_html(str(description_span))
        if continuation_span:
            description += _strip_tag_html(str(continuation_span))

        outer_card = detail_card.parent
        meta_div = outer_card.find("div", class_="aW97bd") if outer_card else None
        company = location_text = None
        if meta_div:
            parts = [p.strip() for p in _strip_tag_html(str(meta_div)).split("·")]
            if len(parts) >= 2:
                company, location_text = parts[0], parts[1]

        apply_link = None
        if outer_card:
            link_tag = outer_card.find("a", href=True)
            apply_link = link_tag["href"] if link_tag else None

        results.append(
            {
                "source": "brightdata",
                "id": str(detail_card.get("data-encoded-docid", "")),
                "title": detail_card.get("data-title"),
                "company": company,
                "location": location_text,
                "description": description,
                "url": apply_link,
                "posted_at": None,
            }
        )
        if len(results) >= results_per_page:
            break

    return results


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


def _search_one_term(search_term: str, location: str | None, country: str, results_per_page: int) -> list[dict]:
    batch = _search_serpapi(search_term, location, country, results_per_page)
    if batch is None:
        # SerpApi quota exhausted or unavailable - fall back to Bright Data.
        batch = _search_bright_data(search_term, location, country, results_per_page)
    return batch


def log_searched_event_safely(candidate_id: str, query_text: str) -> None:
    """Meant to be scheduled as a FastAPI BackgroundTask (see main.py's /jobs/search
    route) so it runs *after* the response is sent - log_event opens a fresh,
    unpooled connection to a remote MySQL/TiDB instance per call, which previously
    ran synchronously in the middle of every search request and added real
    latency to every /jobs/search call regardless of candidate_id's presence.
    """
    try:
        log_event(candidate_id, "searched", query_text=query_text)
    except Exception:
        pass  # history logging must never block or fail a real search


def search_jobs(
    query: str,
    location: str | None = None,
    country: str = "us",
    results_per_page: int = 10,
    candidate_id: str | None = None,
) -> dict:
    used_query = query.strip()
    recommended = False

    if not used_query:
        if candidate_id:
            try:
                used_query = get_recommended_query(candidate_id) or ""
            except Exception:
                used_query = ""  # history lookup must never block a real search
        recommended = bool(used_query)
        if not used_query:
            raise ValueError(
                "Enter a keyword to search. Once you've viewed, applied to, or liked a few jobs, "
                "you'll be able to search with just your activity history."
            )

    query = used_query
    related_titles = expand_query(query)
    all_queries = [query] + [title for title in related_titles if title.strip().lower() != query.strip().lower()]

    # Each search term is an independent, slow (multi-second) HTTP call - run them
    # concurrently instead of sequentially, or total latency stacks up linearly
    # (confirmed live: ~15s sequential for 4 terms vs. ~5s, the slowest single call,
    # in parallel).
    with ThreadPoolExecutor(max_workers=len(all_queries)) as executor:
        batches = executor.map(
            lambda term: _search_one_term(term, location, country, results_per_page), all_queries
        )

        seen: set[tuple[str, str]] = set()
        results: list[dict] = []
        for batch in batches:
            for job in batch:
                key = (job["source"], job["id"])
                if key in seen:
                    continue
                seen.add(key)
                results.append(job)

    return {
        "count": len(results),
        "results": results,
        "expanded_titles": related_titles,
        "used_query": query,
        "recommended": recommended,
    }
