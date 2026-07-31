import pytest

from backend.app.services import job_search_service


def _stub_search_pipeline(monkeypatch, *, expanded_titles=None, jobs_by_term=None):
    monkeypatch.setattr(job_search_service, "expand_query", lambda query: expanded_titles or [])
    jobs_by_term = jobs_by_term or {}

    def fake_search_one_term(search_term, location, country, results_per_page, primary_source="serpapi"):
        return jobs_by_term.get(search_term, [])

    monkeypatch.setattr(job_search_service, "_search_one_term", fake_search_one_term)


def test_search_jobs_with_explicit_query_does_not_touch_history(monkeypatch):
    _stub_search_pipeline(monkeypatch)

    result = job_search_service.search_jobs("Backend Engineer")

    assert result["used_query"] == "Backend Engineer"
    assert result["recommended"] is False


def test_search_jobs_raises_on_empty_query_without_candidate_id(monkeypatch):
    _stub_search_pipeline(monkeypatch)

    with pytest.raises(ValueError):
        job_search_service.search_jobs("")


def test_search_jobs_raises_on_empty_query_when_candidate_has_no_history(monkeypatch):
    _stub_search_pipeline(monkeypatch)
    monkeypatch.setattr(job_search_service, "get_recommended_query", lambda candidate_id: None)

    with pytest.raises(ValueError):
        job_search_service.search_jobs("", candidate_id="cand-1")


def test_search_jobs_falls_back_to_recommended_query_when_empty(monkeypatch):
    _stub_search_pipeline(monkeypatch)
    monkeypatch.setattr(job_search_service, "get_recommended_query", lambda candidate_id: "ML Engineer")

    result = job_search_service.search_jobs("", candidate_id="cand-1")

    assert result["used_query"] == "ML Engineer"
    assert result["recommended"] is True


def test_log_searched_event_safely_calls_log_event(monkeypatch):
    calls = []
    monkeypatch.setattr(job_search_service, "log_event", lambda *a, **k: calls.append((a, k)))

    job_search_service.log_searched_event_safely("cand-1", "ML Engineer")

    assert calls == [(("cand-1", "searched"), {"query_text": "ML Engineer"})]


def test_log_searched_event_safely_swallows_errors(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(job_search_service, "log_event", boom)

    job_search_service.log_searched_event_safely("cand-1", "ML Engineer")  # must not raise


def test_search_one_term_defaults_to_serpapi_primary(monkeypatch):
    calls = []
    monkeypatch.setattr(job_search_service, "_search_serpapi", lambda *a: calls.append("serpapi") or [{"id": "1"}])
    monkeypatch.setattr(job_search_service, "_search_bright_data", lambda *a: calls.append("brightdata") or [])

    result = job_search_service._search_one_term("ML Engineer", None, "us", 10)

    assert calls == ["serpapi"]
    assert result == [{"id": "1"}]


def test_search_one_term_brightdata_primary_skips_serpapi_when_brightdata_succeeds(monkeypatch):
    # Personalized matching (job_matching_service.py) passes primary_source="brightdata" -
    # Bright Data's larger free quota should be tried first, SerpApi not touched at all
    # unless Bright Data comes back empty.
    calls = []
    monkeypatch.setattr(job_search_service, "_search_bright_data", lambda *a: calls.append("brightdata") or [{"id": "1"}])
    monkeypatch.setattr(job_search_service, "_search_serpapi", lambda *a: calls.append("serpapi") or [{"id": "2"}])

    result = job_search_service._search_one_term("ML Engineer", None, "us", 10, primary_source="brightdata")

    assert calls == ["brightdata"]
    assert result == [{"id": "1"}]


def test_search_one_term_brightdata_primary_falls_back_to_serpapi_when_empty(monkeypatch):
    calls = []
    monkeypatch.setattr(job_search_service, "_search_bright_data", lambda *a: calls.append("brightdata") or [])
    monkeypatch.setattr(job_search_service, "_search_serpapi", lambda *a: calls.append("serpapi") or [{"id": "2"}])

    result = job_search_service._search_one_term("ML Engineer", None, "us", 10, primary_source="brightdata")

    assert calls == ["brightdata", "serpapi"]
    assert result == [{"id": "2"}]


def test_search_one_term_routes_unsupported_country_to_local_board_scraper(monkeypatch):
    calls = []
    monkeypatch.setattr(job_search_service, "_search_serpapi", lambda *a: calls.append("serpapi") or [{"id": "1"}])
    monkeypatch.setattr(job_search_service, "_search_bright_data", lambda *a: calls.append("brightdata") or [{"id": "2"}])
    monkeypatch.setitem(
        job_search_service.COUNTRY_JOB_BOARD_SCRAPERS,
        "ie",
        lambda *a: calls.append("local_board") or [{"id": "3"}],
    )

    result = job_search_service._search_one_term("Backend Engineer", None, "ie", 10)

    assert calls == ["local_board"]
    assert result == [{"id": "3"}]


def test_search_one_term_local_board_routing_overrides_brightdata_primary(monkeypatch):
    # Country-based routing takes priority over primary_source - a country in
    # COUNTRY_JOB_BOARD_SCRAPERS must never fall through to SerpApi/Bright Data's
    # Google-Jobs scrape even when primary_source="brightdata" (the matches route).
    calls = []
    monkeypatch.setattr(job_search_service, "_search_serpapi", lambda *a: calls.append("serpapi") or [])
    monkeypatch.setattr(job_search_service, "_search_bright_data", lambda *a: calls.append("brightdata") or [])
    monkeypatch.setitem(job_search_service.COUNTRY_JOB_BOARD_SCRAPERS, "ie", lambda *a: calls.append("local_board") or [])

    job_search_service._search_one_term("Backend Engineer", None, "ie", 10, primary_source="brightdata")

    assert calls == ["local_board"]


def test_extract_balanced_json_finds_object_after_marker():
    text = 'window.foo = {"a": 1, "nested": {"b": "}"}, "c": 2}; window.bar = {}'

    result = job_search_service._extract_balanced_json(text, "window.foo")

    assert result == {"a": 1, "nested": {"b": "}"}, "c": 2}


def test_extract_balanced_json_returns_none_when_marker_missing():
    assert job_search_service._extract_balanced_json("no marker here", "window.foo") is None


_INDEED_LIST_HTML = """
<html><script>
window.mosaic.providerData["mosaic-provider-jobcards"]={"metaData": {"mosaicProviderJobCardsModel": {"results": [
  {"jobkey": "abc123", "title": "Backend Engineer", "company": "Acme", "formattedLocation": "Dublin", "snippet": "short preview"}
]}}};
</script></html>
"""

_INDEED_DETAIL_HTML = """
<html><body><div id="jobDescriptionText"><p><b>Full role</b></p><p>Long real description text.</p></div></body></html>
"""


def test_search_indeed_parses_list_and_fetches_full_description(monkeypatch):
    fetched_urls = []

    def fake_fetch(url):
        fetched_urls.append(url)
        return _INDEED_LIST_HTML if "/jobs?q=" in url else _INDEED_DETAIL_HTML

    monkeypatch.setattr(job_search_service, "_fetch_via_bright_data", fake_fetch)

    results = job_search_service._search_indeed("Backend Engineer", "Dublin", "ie", 10)

    assert len(results) == 1
    job = results[0]
    assert job["source"] == "indeed"
    assert job["id"] == "abc123"
    assert job["title"] == "Backend Engineer"
    assert job["company"] == "Acme"
    assert job["location"] == "Dublin"
    assert "Long real description text." in job["description"]
    assert job["url"] == "https://ie.indeed.com/viewjob?jk=abc123"
    assert any("ie.indeed.com/jobs?q=" in url for url in fetched_urls)
    assert any("ie.indeed.com/viewjob?jk=abc123" in url for url in fetched_urls)


def test_search_indeed_falls_back_to_snippet_when_detail_fetch_fails(monkeypatch):
    def fake_fetch(url):
        return _INDEED_LIST_HTML if "/jobs?q=" in url else None

    monkeypatch.setattr(job_search_service, "_fetch_via_bright_data", fake_fetch)

    results = job_search_service._search_indeed("Backend Engineer", None, "ie", 10)

    assert results[0]["description"] == "short preview"


def test_search_indeed_returns_empty_when_list_fetch_fails(monkeypatch):
    monkeypatch.setattr(job_search_service, "_fetch_via_bright_data", lambda url: None)

    assert job_search_service._search_indeed("Backend Engineer", None, "ie", 10) == []


@pytest.mark.parametrize("country", ["ie", "au", "nz"])
def test_country_job_board_scrapers_indeed_countries_route_to_search_indeed(country):
    assert job_search_service.COUNTRY_JOB_BOARD_SCRAPERS[country] is job_search_service._search_indeed


def test_country_job_board_scrapers_pl_routes_to_search_pracuj():
    assert job_search_service.COUNTRY_JOB_BOARD_SCRAPERS["pl"] is job_search_service._search_pracuj


_PRACUJ_LIST_HTML = """
<html><script>__NEXT_DATA__" type="application/json">{"props": {"pageProps": {"dehydratedState": {"queries": [
  {"queryKey": ["jobOffers", {}], "state": {"data": {"groupedOffers": [
    {"groupId": "g1", "jobTitle": "Backend Engineer", "companyName": "Acme", "jobDescription": "short truncated...",
     "lastPublicated": "2026-07-31T00:00:00Z",
     "offers": [{"offerAbsoluteUri": "https://www.pracuj.pl/praca/backend-engineer,oferta,123", "displayWorkplace": "Warszawa"}]}
  ]}}}
]}}}};
</script></html>
"""

_PRACUJ_DETAIL_HTML = """
<html><script>__NEXT_DATA__" type="application/json">{"props": {"pageProps": {"dehydratedState": {"queries": [
  {"queryKey": ["jobOffer", "123", "pl"], "state": {"data": {"textSections": [
    {"sectionType": "about-project", "plainText": "About the project, full real description text here."},
    {"sectionType": "responsibilities", "plainText": "Your responsibilities, do real engineering work."}
  ]}}}
]}}}};
</script></html>
"""


def test_search_pracuj_parses_list_and_fetches_full_sections(monkeypatch):
    fetched_urls = []

    def fake_fetch(url):
        fetched_urls.append(url)
        return _PRACUJ_LIST_HTML if "/praca/" in url and ",oferta," not in url else _PRACUJ_DETAIL_HTML

    monkeypatch.setattr(job_search_service, "_fetch_via_bright_data", fake_fetch)

    results = job_search_service._search_pracuj("backend engineer", "Warszawa", "pl", 10)

    assert len(results) == 1
    job = results[0]
    assert job["source"] == "pracuj"
    assert job["id"] == "g1"
    assert job["title"] == "Backend Engineer"
    assert job["company"] == "Acme"
    assert job["location"] == "Warszawa"
    assert "full real description text here" in job["description"]
    assert "do real engineering work" in job["description"]
    assert job["url"] == "https://www.pracuj.pl/praca/backend-engineer,oferta,123"
    assert any(";wp" in url for url in fetched_urls)


def test_search_pracuj_falls_back_to_truncated_description_when_detail_fetch_fails(monkeypatch):
    def fake_fetch(url):
        return _PRACUJ_LIST_HTML if ",oferta," not in url else None

    monkeypatch.setattr(job_search_service, "_fetch_via_bright_data", fake_fetch)

    results = job_search_service._search_pracuj("backend engineer", None, "pl", 10)

    assert results[0]["description"] == "short truncated..."


def test_search_pracuj_returns_empty_when_list_fetch_fails(monkeypatch):
    monkeypatch.setattr(job_search_service, "_fetch_via_bright_data", lambda url: None)

    assert job_search_service._search_pracuj("backend engineer", None, "pl", 10) == []


def test_search_jobs_history_lookup_failure_does_not_crash_search(monkeypatch):
    _stub_search_pipeline(monkeypatch)

    def boom(candidate_id):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(job_search_service, "get_recommended_query", boom)

    with pytest.raises(ValueError):
        # DB failure degrades to "no history" rather than a 500.
        job_search_service.search_jobs("", candidate_id="cand-1")
