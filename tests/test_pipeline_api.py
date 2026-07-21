from fastapi.testclient import TestClient

import backend.app.main as main_module
from backend.app.main import app
from tests.test_ranking_graph import _batch_ranking, _reranked

client = TestClient(app)


def _patch_pipeline_services(monkeypatch, *, eligible=True, alice_score=90, bob_score=70, persist_calls=None):
    def fake_rank(jd, candidates):
        return _batch_ranking(eligible=eligible, alice_score=alice_score, bob_score=bob_score)

    def fake_rerank(jd, batch_rankings, candidates, top_n=10):
        return _reranked(eligible=eligible)

    def fake_persist(rankings, run_name, source_file="api_payload"):
        if persist_calls is not None:
            persist_calls.append(rankings)
        return {"run_id": 1, "saved_rankings": len(rankings.get("results", []))}

    monkeypatch.setattr("backend.app.services.ranking_service.rank_candidates_for_jd", fake_rank)
    monkeypatch.setattr("backend.app.services.reranking_service.rerank_shortlist_for_jd", fake_rerank)
    monkeypatch.setattr("backend.app.services.persistence_service.save_rankings_payload", fake_persist)

    # Fake the durable review store (in-memory dict) instead of hitting real MySQL,
    # matching this test suite's convention of mocking at the service boundary.
    fake_store: dict[str, dict] = {}

    def fake_save_pending_review(thread_id, jd, candidates, batch_ranking, reranked, run_name, source_file, top_n):
        fake_store[thread_id] = {
            "thread_id": thread_id,
            "jd": jd,
            "candidates": candidates,
            "batch_ranking": batch_ranking,
            "reranked": reranked,
            "run_name": run_name,
            "source_file": source_file,
            "top_n": top_n,
            "status": "awaiting_review",
        }

    def fake_get_pending_review(thread_id):
        return fake_store.get(thread_id)

    def fake_mark_review_resolved(thread_id, status):
        fake_store[thread_id]["status"] = status

    monkeypatch.setattr(main_module, "save_pending_review", fake_save_pending_review)
    monkeypatch.setattr(main_module, "get_pending_review", fake_get_pending_review)
    monkeypatch.setattr(main_module, "mark_review_resolved", fake_mark_review_resolved)

    return fake_store


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
    # Below the relative-score floor (50) too, so this is a genuine dead end -
    # see test_run_pipeline_falls_back_to_relative_scoring below for the case
    # where nobody's hard-eligible but some candidates still clear that floor.
    _patch_pipeline_services(monkeypatch, eligible=False, alice_score=40, bob_score=20)

    response = client.post("/pipeline/run", json=_run_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "no_eligible_candidates"
    assert body["review_payload"] is None


def test_run_pipeline_falls_back_to_relative_scoring(monkeypatch):
    _patch_pipeline_services(monkeypatch, eligible=False, alice_score=90, bob_score=70)

    response = client.post("/pipeline/run", json=_run_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "awaiting_review"
    assert body["review_payload"]["used_relative_fallback"] is True


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


def test_resume_pipeline_returns_404_for_unknown_thread_id(monkeypatch):
    _patch_pipeline_services(monkeypatch, eligible=True)

    response = client.post(
        "/pipeline/resume", json={"thread_id": "does-not-exist", "action": "approve"}
    )

    assert response.status_code == 404


def test_resume_pipeline_returns_409_when_already_resolved(monkeypatch):
    persist_calls = []
    _patch_pipeline_services(monkeypatch, eligible=True, persist_calls=persist_calls)

    run_response = client.post("/pipeline/run", json=_run_payload())
    thread_id = run_response.json()["thread_id"]

    first = client.post("/pipeline/resume", json={"thread_id": thread_id, "action": "approve"})
    assert first.status_code == 200

    second = client.post("/pipeline/resume", json={"thread_id": thread_id, "action": "approve"})
    assert second.status_code == 409
    assert len(persist_calls) == 1


def test_resume_pipeline_uses_durable_fallback_when_checkpoint_is_gone(monkeypatch):
    # Simulates a process restart: a thread_id that was never invoked through
    # this process's pipeline_graph (so get_state().next is empty, same as a
    # fresh process would see), but whose /pipeline/run row is already sitting
    # in the durable store - exactly what a Render/HF Spaces restart looks like.
    persist_calls = []
    fake_store = _patch_pipeline_services(monkeypatch, eligible=True, persist_calls=persist_calls)

    thread_id = "cold-thread-from-a-dead-process"
    fake_store[thread_id] = {
        "thread_id": thread_id,
        "jd": {"job_title": "Backend Engineer"},
        "candidates": [{"name": "Alice"}, {"name": "Bob"}],
        "batch_ranking": _batch_ranking(eligible=True),
        "reranked": _reranked(eligible=True),
        "run_name": "Durable fallback test",
        "source_file": "test",
        "top_n": 1,
        "status": "awaiting_review",
    }

    response = client.post(
        "/pipeline/resume", json={"thread_id": thread_id, "action": "approve"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "persisted"
    assert len(persist_calls) == 1
    assert fake_store[thread_id]["status"] == "persisted"
