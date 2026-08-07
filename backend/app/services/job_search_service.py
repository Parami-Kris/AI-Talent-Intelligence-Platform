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


def _fetch_via_bright_data(url: str) -> str | None:
    """Fetches a URL through Bright Data's Web Unlocker product (full rendered
    HTML, proxy-routed) and returns the raw response text, or None on any
    failure (missing credentials, HTTP error). Shared by every Bright-Data-backed
    scraper below - each just parses this differently for its own target site.
    """
    api_key = os.environ.get("BRIGHT_DATA_API_KEY")
    zone = os.environ.get("BRIGHT_DATA_SERP_ZONE")
    if not api_key or not zone:
        return None

    try:
        response = httpx.post(
            BRIGHT_DATA_REQUEST_URL,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"zone": zone, "url": url, "format": "raw"},
            timeout=90,
        )
        response.raise_for_status()
        return response.text
    except httpx.HTTPError:
        return None


def _extract_balanced_json(text: str, start_marker: str) -> dict | None:
    """Finds `start_marker` in `text`, then extracts the JSON object literal that
    begins at the next `{` after it, using brace-depth counting (string-aware, so
    braces inside quoted values don't throw off the count) rather than a regex -
    sites embed page-state JSON in inline <script> blocks this way, and the blob
    is too large/nested for a regex to reliably bound.
    """
    marker_index = text.find(start_marker)
    if marker_index == -1:
        return None
    brace_start = text.find("{", marker_index)
    if brace_start == -1:
        return None

    depth = 0
    in_string = False
    escape = False
    for i in range(brace_start, len(text)):
        char = text[i]
        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[brace_start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


# Countries SerpApi's google_jobs engine rejects outright, and where Bright Data's
# Google-Jobs-vertical scrape below is also confirmed empty (live-tested) - routed
# straight to the locally-dominant job board for that market instead, scraped
# directly via Bright Data. Checked in _search_one_term before either of the above.
COUNTRY_JOB_BOARD_SCRAPERS = {}

# Full-description scraping costs 1 (list page) + N (detail page) Bright Data
# requests per search term, vs. 1 total for the Google-Jobs-vertical path - capped
# independently of results_per_page to bound both latency and quota burn.
LOCAL_BOARD_DETAIL_FETCH_CAP = 15


def _search_indeed(query: str, location: str | None, country: str, results_per_page: int) -> list[dict]:
    """Local job board scrape for SerpApi-unsupported countries where Indeed has
    a country-specific site (confirmed live for `ie`). Two-stage: the search
    results page embeds a JSON blob with short snippets, so each result's own
    /viewjob page is fetched too, in parallel, for the full description.
    """
    search_url = f"https://{country}.indeed.com/jobs?q={quote_plus(query)}"
    if location:
        search_url += f"&l={quote_plus(location)}"

    list_html = _fetch_via_bright_data(search_url)
    if list_html is None:
        return []

    provider_data = _extract_balanced_json(list_html, 'window.mosaic.providerData["mosaic-provider-jobcards"]')
    if not provider_data:
        return []

    cards = provider_data.get("metaData", {}).get("mosaicProviderJobCardsModel", {}).get("results", [])
    cards = [card for card in cards if card.get("jobkey")][: min(results_per_page, LOCAL_BOARD_DETAIL_FETCH_CAP)]
    if not cards:
        return []

    def fetch_one(card: dict) -> dict:
        job_key = card["jobkey"]
        job_url = f"https://{country}.indeed.com/viewjob?jk={job_key}"
        description = card.get("snippet")
        detail_html = _fetch_via_bright_data(job_url)
        if detail_html:
            try:
                detail_soup = BeautifulSoup(detail_html, "lxml")
            except Exception:
                detail_soup = None
            description_div = detail_soup.find("div", id="jobDescriptionText") if detail_soup else None
            if description_div:
                # Collapse the run of blank lines get_text() leaves behind for
                # each closed <p>/<b> tag boundary in Indeed's markup.
                description = re.sub(r"\n{3,}", "\n\n", description_div.get_text("\n")).strip()

        return {
            "source": "indeed",
            "id": job_key,
            "title": card.get("title"),
            "company": card.get("company"),
            "location": card.get("formattedLocation"),
            "description": description,
            "url": job_url,
            "posted_at": None,
        }

    with ThreadPoolExecutor(max_workers=min(len(cards), 5)) as executor:
        return list(executor.map(fetch_one, cards))


COUNTRY_JOB_BOARD_SCRAPERS["ie"] = _search_indeed
# Indeed also runs country-specific sites for au/nz (confirmed live, same
# mosaic-provider-jobcards + jobDescriptionText structure as `ie`) - reuses
# _search_indeed as-is rather than a SEEK-specific scraper, since SEEK's own
# robots.txt disallows `*/job/*` (its individual job pages), which Bright
# Data's standard access tier respects and blocks - confirmed live, "Request
# Failed (bad_endpoint): ... not available for immediate access mode".
COUNTRY_JOB_BOARD_SCRAPERS["au"] = _search_indeed
COUNTRY_JOB_BOARD_SCRAPERS["nz"] = _search_indeed


def _find_react_query_data(next_data: dict, query_key_prefix: str):
    """pracuj.pl (Next.js + React Query) embeds page state as a list of
    {queryKey, state: {data}} entries under dehydratedState.queries - finds the
    first entry whose queryKey starts with the given string and returns its data.
    """
    try:
        queries = next_data["props"]["pageProps"]["dehydratedState"]["queries"]
    except (KeyError, TypeError):
        return None
    for entry in queries:
        key = entry.get("queryKey")
        if key and key[0] == query_key_prefix:
            return entry.get("state", {}).get("data")
    return None


def _search_pracuj(query: str, location: str | None, country: str, results_per_page: int) -> list[dict]:
    """Poland-only local job board scrape (SerpApi/Bright-Data-Google-Jobs both
    confirmed empty for `pl`). pracuj.pl's search-results listing only carries a
    ~250-char truncated description per job, so each result's own offer page is
    fetched too, in parallel, for the full sectioned description (technologies,
    responsibilities, requirements, offer conditions - genuinely richer than a
    flat text blob, confirmed live).
    """
    path = f"/praca/{quote_plus(query)};kw"
    if location:
        path += f"/{quote_plus(location)};wp"

    list_html = _fetch_via_bright_data(f"https://www.pracuj.pl{path}")
    if list_html is None:
        return []

    next_data = _extract_balanced_json(list_html, '__NEXT_DATA__" type="application/json">')
    if not next_data:
        return []

    job_offers_data = _find_react_query_data(next_data, "jobOffers") or {}
    offer_groups = job_offers_data.get("groupedOffers", [])
    offer_groups = [g for g in offer_groups if g.get("offers")][: min(results_per_page, LOCAL_BOARD_DETAIL_FETCH_CAP)]
    if not offer_groups:
        return []

    def fetch_one(offer_group: dict) -> dict:
        offer = offer_group["offers"][0]
        detail_url = offer["offerAbsoluteUri"]
        description = offer_group.get("jobDescription")

        detail_html = _fetch_via_bright_data(detail_url)
        if detail_html:
            detail_data = _extract_balanced_json(detail_html, '__NEXT_DATA__" type="application/json">')
            job_data = _find_react_query_data(detail_data, "jobOffer") if detail_data else None
            sections = (job_data or {}).get("textSections") or []
            full_text = "\n\n".join(section["plainText"] for section in sections if section.get("plainText"))
            if full_text:
                description = full_text

        return {
            "source": "pracuj",
            "id": str(offer_group.get("groupId", "")),
            "title": offer_group.get("jobTitle"),
            "company": offer_group.get("companyName"),
            "location": offer.get("displayWorkplace"),
            "description": description,
            "url": detail_url,
            "posted_at": offer_group.get("lastPublicated"),
        }

    with ThreadPoolExecutor(max_workers=min(len(offer_groups), 5)) as executor:
        return list(executor.map(fetch_one, offer_groups))


COUNTRY_JOB_BOARD_SCRAPERS["pl"] = _search_pracuj


def _search_bright_data(query: str, location: str | None, country: str, results_per_page: int) -> list[dict]:
    """Fallback for when SerpApi's quota is exhausted. Uses Bright Data's Web
    Unlocker product to fetch Google's Jobs vertical (udm=8) and parses the
    HTML directly - Google preloads full descriptions for every job on the
    page (confirmed live), just CSS-hidden until clicked, which a plain SERP
    API static fetch does not expose but Web Unlocker's full render does.
    More fragile than SerpApi (tied to Google's current markup) - only used
    as a fallback, not primary, for that reason.
    """
    search_text = f"{query} {location}" if location else query
    target_url = f"https://www.google.com/search?q={quote_plus(search_text)}&gl={country}&hl=en&udm=8"

    html = _fetch_via_bright_data(target_url)
    if html is None:
        return []

    try:
        soup = BeautifulSoup(html, "lxml")
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
        # <br> runs in Google's markup become \n runs here - collapse to a
        # single blank line, matching the normalization the other source's
        # detail-page path already does.
        description = re.sub(r"\n{3,}", "\n\n", description).strip()

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


def _search_one_term(
    search_term: str,
    location: str | None,
    country: str,
    results_per_page: int,
    primary_source: str = "serpapi",
) -> list[dict]:
    local_board_scraper = COUNTRY_JOB_BOARD_SCRAPERS.get(country)
    if local_board_scraper:
        # Deterministic country-based routing, not a reactive fallback - SerpApi
        # and Bright Data's Google-Jobs-vertical scrape are both confirmed empty
        # for these countries, so skip straight to the local board instead of
        # spending two calls we already know will fail.
        return local_board_scraper(search_term, location, country, results_per_page)

    if primary_source == "brightdata":
        # Personalized matching (job_matching_service.py) needs a bigger pool per
        # request than a one-off manual search, and Bright Data's free tier
        # (5,000/mo) has far more headroom than SerpApi's (250/mo) - primary/
        # fallback flipped for that caller only, everything else below unchanged.
        batch = _search_bright_data(search_term, location, country, results_per_page)
        return batch if batch else (_search_serpapi(search_term, location, country, results_per_page) or [])

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
    primary_source: str = "serpapi",
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
            lambda term: _search_one_term(term, location, country, results_per_page, primary_source), all_queries
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
