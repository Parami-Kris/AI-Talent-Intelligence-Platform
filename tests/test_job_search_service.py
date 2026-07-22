import pytest

from backend.app.services import job_search_service


def _stub_search_pipeline(monkeypatch, *, expanded_titles=None, jobs_by_term=None):
    monkeypatch.setattr(job_search_service, "expand_query", lambda query: expanded_titles or [])
    jobs_by_term = jobs_by_term or {}

    def fake_search_one_term(search_term, location, country, results_per_page):
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


def test_search_jobs_history_lookup_failure_does_not_crash_search(monkeypatch):
    _stub_search_pipeline(monkeypatch)

    def boom(candidate_id):
        raise RuntimeError("db unavailable")

    monkeypatch.setattr(job_search_service, "get_recommended_query", boom)

    with pytest.raises(ValueError):
        # DB failure degrades to "no history" rather than a 500.
        job_search_service.search_jobs("", candidate_id="cand-1")
