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