from fastapi.testclient import TestClient

from backend.app.main import app
from tests.test_ranking_graph import _batch_ranking, _reranked

client = TestClient(app)


def _patch_pipeline_services(monkeypatch, *, eligible=True, persist_calls=None):
    def fake_rank(jd, candidates):
        return _batch_ranking(eligible=eligible)

    def fake_rerank(jd, batch_rankings, candidates, top_n=10):
        return _reranked(eligible=eligible)

    def fake_persist(rankings, run_name, source_file="api_payload"):
        if persist_calls is not None:
            persist_calls.append(rankings)
        return {"run_id": 1, "saved_rankings": len(rankings.get("results", []))}

    monkeypatch.setattr("backend.app.services.ranking_service.rank_candidates_for_jd", fake_rank)
    monkeypatch.setattr("backend.app.services.reranking_service.rerank_shortlist_for_jd", fake_rerank)
    monkeypatch.setattr("backend.app.services.persistence_service.save_rankings_payload", fake_persist)


def _run_payload():
    return {
        "jd": {"job_title": "Backend Engineer"},
        "candidates": [{"name": "Alice"}, {"name": "Bob"}],
        "top_n": 1,
    }


def test_run_pipeline_returns_shortlist_and_other_candidates(monkeypatch):
    _patch_pipeline_services(monkeypatch, eligible=True)

    response = client.post("/pipeline/run", json=_run_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "awaiting_review"
    assert body["thread_id"]
    shortlist_names = {item["candidate_name"] for item in body["review_payload"]["shortlist"]}
    other_names = {item["candidate_name"] for item in body["review_payload"]["other_candidates"]}
    assert shortlist_names == {"Alice"}
    assert other_names == {"Bob"}


def test_run_pipeline_no_eligible_candidates(monkeypatch):
    _patch_pipeline_services(monkeypatch, eligible=False)

    response = client.post("/pipeline/run", json=_run_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_eligible_candidates"
    assert body["review_payload"] is None


def test_resume_pipeline_approve_persists(monkeypatch):
    persist_calls = []
    _patch_pipeline_services(monkeypatch, eligible=True, persist_calls=persist_calls)

    run_response = client.post("/pipeline/run", json=_run_payload())
    thread_id = run_response.json()["thread_id"]

    resume_response = client.post(
        "/pipeline/resume", json={"thread_id": thread_id, "action": "approve"}
    )

    assert resume_response.status_code == 200
    body = resume_response.json()
    assert body["status"] == "persisted"
    assert body["persistence_result"]["run_id"] == 1
    assert len(persist_calls) == 1


def test_resume_pipeline_manual_addition_round_trip(monkeypatch):
    persist_calls = []
    _patch_pipeline_services(monkeypatch, eligible=True, persist_calls=persist_calls)

    run_response = client.post("/pipeline/run", json=_run_payload())
    thread_id = run_response.json()["thread_id"]

    resume_response = client.post(
        "/pipeline/resume",
        json={
            "thread_id": thread_id,
            "action": "edit",
            "manual_additions": [
                {
                    "candidate_name": "Bob",
                    "override_reason": "Exceptional in interview despite resume gap.",
                    "added_by": "recruiter@example.com",
                }
            ],
        },
    )

    assert resume_response.status_code == 200
    body = resume_response.json()
    assert body["status"] == "persisted"
    persisted_names = {item["candidate_name"] for item in persist_calls[0]["results"]}
    assert persisted_names == {"Alice", "Bob"}


def test_resume_pipeline_rejects_manual_addition_without_reason(monkeypatch):
    _patch_pipeline_services(monkeypatch, eligible=True)

    run_response = client.post("/pipeline/run", json=_run_payload())
    thread_id = run_response.json()["thread_id"]

    resume_response = client.post(
        "/pipeline/resume",
        json={
            "thread_id": thread_id,
            "action": "edit",
            "manual_additions": [{"candidate_name": "Bob", "override_reason": ""}],
        },
    )

    assert resume_response.status_code == 422
