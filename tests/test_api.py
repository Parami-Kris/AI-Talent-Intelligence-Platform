from fastapi.testclient import TestClient

from backend.app.main import app
from tests._fakes import FakeGenAIClient


client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_rank_candidates_endpoint_without_education_requirement():
    jd = {
        "job_title": "Backend Engineer",
        "required_skills": ["Python"],
        "preferred_skills": [],
        "experience_required": "1 year",
        "education_required": "",
    }
    candidates = [
        {
            "name": "Strong Candidate",
            "normalized_skills": ["Python"],
            "experience": [
                {"job_title": "Dev", "company": "Acme", "duration": "Jan 2020 - Jan 2023"}
            ],
        }
    ]

    response = client.post(
        "/rank-candidates",
        json={"jd": jd, "candidates": candidates},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["candidate_name"] == "Strong Candidate"
    assert body["results"][0]["is_eligible"] is True


def _jd():
    return {
        "job_title": "Backend Engineer",
        "required_skills": ["Python"],
        "preferred_skills": [],
        "experience_required": "1 year",
        "education_required": "",
    }


def _candidates():
    return [
        {
            "name": "Strong Candidate",
            "normalized_skills": ["Python"],
            "experience": [
                {"job_title": "Dev", "company": "Acme", "duration": "Jan 2020 - Jan 2023"}
            ],
        }
    ]


def test_rerank_shortlist_endpoint_validates_against_response_model(monkeypatch):
    from pipeline import shortlist_reranker

    batch_response = client.post(
        "/rank-candidates", json={"jd": _jd(), "candidates": _candidates()}
    )
    batch_rankings = batch_response.json()

    fake_response_text = (
        '[{"candidate_name": "Strong Candidate", "experience_relevance_score": 85, '
        '"seniority_fit": "strong", "domain_fit": "strong", "reason": "Relevant.", '
        '"matched": [], "missing": [], "evidence": []}]'
    )
    monkeypatch.setattr(shortlist_reranker, "client", FakeGenAIClient(response_text=fake_response_text))

    response = client.post(
        "/rerank-shortlist",
        json={
            "jd": _jd(),
            "batch_rankings": batch_rankings,
            "candidates": _candidates(),
            "top_n": 5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["candidate_name"] == "Strong Candidate"
    assert body["results"][0]["final_score"] > 0


def test_analyze_profile_gap_endpoint_validates_against_response_model():
    response = client.post(
        "/analyze-profile-gap",
        json={"jd": _jd(), "candidate": _candidates()[0], "target_role": "Backend Engineer"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["candidate_name"] == "Strong Candidate"
    assert body["current_fit"] in {"strong", "partial", "weak"}


def test_save_rankings_endpoint_validates_against_response_model(monkeypatch):
    import backend.app.services.persistence_service as persistence_service

    def fake_save_rankings_payload(rankings, run_name, source_file="api_payload"):
        return {"run_id": 42, "saved_rankings": len(rankings.get("results", []))}

    monkeypatch.setattr(persistence_service, "save_rankings_payload", fake_save_rankings_payload)

    response = client.post(
        "/save-rankings",
        json={"rankings": {"results": [{"candidate_name": "Strong Candidate"}]}},
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {"run_id": 42, "saved_rankings": 1}


def test_upload_rank_candidates_endpoint_validates_against_response_model(monkeypatch):
    import backend.app.main as main_module

    monkeypatch.setattr(main_module, "parse_jd_upload", lambda content, filename: _jd())
    monkeypatch.setattr(
        main_module, "parse_resumes_batch", lambda files: {"candidates": _candidates(), "failures": []}
    )

    response = client.post(
        "/upload/rank-candidates",
        files={
            "jd_file": ("jd.txt", b"job description", "text/plain"),
            "resume_files": ("resume.txt", b"resume text", "text/plain"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["candidate_name"] == "Strong Candidate"
    assert body["parse_failures"] == []


def test_upload_parse_endpoint_returns_parsed_jd_and_candidates(monkeypatch):
    import backend.app.main as main_module

    monkeypatch.setattr(main_module, "parse_jd_upload", lambda content, filename: _jd())
    monkeypatch.setattr(
        main_module, "parse_resumes_batch", lambda files: {"candidates": _candidates(), "failures": []}
    )

    response = client.post(
        "/upload/parse",
        files={
            "jd_file": ("jd.txt", b"job description", "text/plain"),
            "resume_files": ("resume.txt", b"resume text", "text/plain"),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["jd"]["job_title"] == "Backend Engineer"
    assert body["candidates"][0]["name"] == "Strong Candidate"
    assert body["failures"] == []


def test_upload_parse_endpoint_returns_422_on_jd_parse_failure(monkeypatch):
    import backend.app.main as main_module

    def fake_parse_jd_upload(content, filename):
        raise ValueError(f"Failed to parse job description '{filename}': bad json")

    monkeypatch.setattr(main_module, "parse_jd_upload", fake_parse_jd_upload)

    response = client.post(
        "/upload/parse",
        files={
            "jd_file": ("jd.txt", b"job description", "text/plain"),
            "resume_files": ("resume.txt", b"resume text", "text/plain"),
        },
    )

    assert response.status_code == 422
    assert "bad json" in response.json()["detail"]


def test_upload_parse_endpoint_returns_422_when_no_resumes_parsed(monkeypatch):
    import backend.app.main as main_module

    monkeypatch.setattr(main_module, "parse_jd_upload", lambda content, filename: _jd())
    monkeypatch.setattr(
        main_module,
        "parse_resumes_batch",
        lambda files: {"candidates": [], "failures": [{"filename": "bad.pdf", "reason": "boom"}]},
    )

    response = client.post(
        "/upload/parse",
        files={
            "jd_file": ("jd.txt", b"job description", "text/plain"),
            "resume_files": ("bad.pdf", b"not a real pdf", "application/pdf"),
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["failures"][0]["filename"] == "bad.pdf"


def test_start_upload_parse_reports_progress_and_completes(monkeypatch):
    import backend.app.main as main_module

    monkeypatch.setattr(main_module, "parse_jd_upload", lambda content, filename: _jd())

    def fake_parse_resumes_batch(files, on_progress=None):
        for _content, filename in files:
            if on_progress:
                on_progress(current_filename=filename)
            if on_progress:
                on_progress(processed_increment=True)
        return {"candidates": _candidates(), "failures": []}

    monkeypatch.setattr(main_module, "parse_resumes_batch", fake_parse_resumes_batch)

    start_response = client.post(
        "/upload/parse/start",
        files={
            "jd_file": ("jd.txt", b"job description", "text/plain"),
            "resume_files": ("resume.txt", b"resume text", "text/plain"),
        },
    )

    assert start_response.status_code == 200
    job_id = start_response.json()["job_id"]
    assert start_response.json()["total"] == 1

    # TestClient runs BackgroundTasks synchronously as part of the request, so the
    # job is already "done" by the time /upload/parse/start returns.
    status_response = client.get(f"/upload/parse/status/{job_id}")
    assert status_response.status_code == 200
    body = status_response.json()
    assert body["status"] == "done"
    assert body["processed"] == 1
    assert body["total"] == 1
    assert body["jd"]["job_title"] == "Backend Engineer"
    assert body["candidates"][0]["name"] == "Strong Candidate"


def test_upload_parse_status_returns_404_for_unknown_job():
    response = client.get("/upload/parse/status/does-not-exist")
    assert response.status_code == 404


def test_start_upload_parse_marks_job_failed_on_jd_parse_error(monkeypatch):
    import backend.app.main as main_module

    def fake_parse_jd_upload(content, filename):
        raise ValueError(f"Failed to parse job description '{filename}': bad json")

    monkeypatch.setattr(main_module, "parse_jd_upload", fake_parse_jd_upload)

    start_response = client.post(
        "/upload/parse/start",
        files={
            "jd_file": ("jd.txt", b"job description", "text/plain"),
            "resume_files": ("resume.txt", b"resume text", "text/plain"),
        },
    )
    job_id = start_response.json()["job_id"]

    status_response = client.get(f"/upload/parse/status/{job_id}")
    body = status_response.json()
    assert body["status"] == "error"
    assert "bad json" in body["error"]


def test_search_jobs_endpoint_returns_422_when_no_query_and_no_history(monkeypatch):
    import backend.app.main as main_module

    def fake_search_jobs_service(**kwargs):
        raise ValueError("Enter a keyword to search.")

    monkeypatch.setattr(main_module, "search_jobs_service", fake_search_jobs_service)

    response = client.get("/jobs/search", params={"query": ""})

    assert response.status_code == 422


def test_search_jobs_endpoint_passes_candidate_id_through(monkeypatch):
    import backend.app.main as main_module

    captured = {}

    def fake_search_jobs_service(**kwargs):
        captured.update(kwargs)
        return {"count": 0, "results": [], "expanded_titles": [], "used_query": "ML Engineer", "recommended": True}

    monkeypatch.setattr(main_module, "search_jobs_service", fake_search_jobs_service)

    response = client.get("/jobs/search", params={"query": "", "candidate_id": "cand-1"})

    assert response.status_code == 200
    assert response.json()["recommended"] is True
    assert captured["candidate_id"] == "cand-1"


def test_log_job_event_endpoint_calls_repository(monkeypatch):
    import backend.app.main as main_module

    calls = []
    monkeypatch.setattr(main_module, "log_event", lambda *a, **k: calls.append((a, k)))

    response = client.post(
        "/jobs/events",
        json={
            "candidate_id": "cand-1",
            "event_type": "liked",
            "job_source": "serpapi",
            "job_external_id": "123",
            "job_title": "ML Engineer",
            "company": "Acme",
            "location": "Remote",
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert calls == [
        (
            ("cand-1", "liked"),
            {
                "job_source": "serpapi",
                "job_external_id": "123",
                "job_title": "ML Engineer",
                "company": "Acme",
                "location": "Remote",
            },
        )
    ]


def test_log_job_event_endpoint_rejects_invalid_event_type():
    response = client.post("/jobs/events", json={"candidate_id": "cand-1", "event_type": "bogus"})

    assert response.status_code == 422