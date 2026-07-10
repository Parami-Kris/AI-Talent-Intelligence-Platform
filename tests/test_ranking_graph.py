from uuid import uuid4

from langgraph.types import Command

from backend.app.pipeline.ranking_graph import extract_interrupt_payload, pipeline_graph


def _batch_ranking(eligible=True):
    alice_eligible = eligible
    return {
        "job_title": "Backend Engineer",
        "ranking_rule": "Eligible candidates first, then overall_score, then skill_score.",
        "summary": [
            {"rank": 1, "candidate_name": "Alice", "is_eligible": alice_eligible, "overall_score": 90},
            {"rank": 2, "candidate_name": "Bob", "is_eligible": eligible, "overall_score": 70},
        ],
        "results": [
            {
                "candidate_name": "Alice",
                "email": "alice@example.com",
                "is_eligible": alice_eligible,
                "overall_score": 90,
                "rank": 1,
            },
            {
                "candidate_name": "Bob",
                "email": "bob@example.com",
                "is_eligible": eligible,
                "overall_score": 70,
                "rank": 2,
            },
        ],
    }


def _reranked(eligible=True):
    # Mirrors the real shortlist_reranker.merge_rerank_results behavior: every
    # first-pass candidate is carried into results/summary, not just the top_n
    # shortlist - only the shortlisted ones get a non-null experience_relevance.
    return {
        "job_title": "Backend Engineer",
        "ranking_rule": "Eligible candidates first, then final_score.",
        "shortlist_size": 1,
        "summary": [
            {
                "final_rank": 1,
                "candidate_name": "Alice",
                "is_eligible": True,
                "final_score": 92,
                "experience_relevance_score": 95,
            },
            {
                "final_rank": 2,
                "candidate_name": "Bob",
                "is_eligible": eligible,
                "final_score": 70,
                "experience_relevance_score": None,
            },
        ],
        "results": [
            {
                "candidate_name": "Alice",
                "email": "alice@example.com",
                "is_eligible": True,
                "overall_score": 90,
                "final_score": 92,
                "experience_relevance": {"experience_relevance_score": 95},
            },
            {
                "candidate_name": "Bob",
                "email": "bob@example.com",
                "is_eligible": eligible,
                "overall_score": 70,
                "final_score": 70,
                "experience_relevance": None,
            },
        ],
    }


def _config():
    return {"configurable": {"thread_id": str(uuid4())}}


def _initial_state(jd=None, candidates=None):
    return {
        "jd": jd or {"job_title": "Backend Engineer"},
        "candidates": candidates or [{"name": "Alice"}, {"name": "Bob"}],
        "run_name": "test run",
        "source_file": "test",
        "top_n": 1,
    }


def _patch_pipeline_services(monkeypatch, *, eligible=True, rerank_calls=None, persist_calls=None):
    def fake_rank(jd, candidates):
        return _batch_ranking(eligible=eligible)

    def fake_rerank(jd, batch_rankings, candidates, top_n=10):
        if rerank_calls is not None:
            rerank_calls.append((batch_rankings, top_n))
        return _reranked(eligible=eligible)

    def fake_persist(rankings, run_name, source_file="api_payload"):
        if persist_calls is not None:
            persist_calls.append(rankings)
        return {"run_id": 1, "saved_rankings": len(rankings.get("results", []))}

    monkeypatch.setattr("backend.app.services.ranking_service.rank_candidates_for_jd", fake_rank)
    monkeypatch.setattr("backend.app.services.reranking_service.rerank_shortlist_for_jd", fake_rerank)
    monkeypatch.setattr("backend.app.services.persistence_service.save_rankings_payload", fake_persist)


def test_pauses_at_review_showing_shortlisted_and_other_candidates(monkeypatch):
    persist_calls = []
    _patch_pipeline_services(monkeypatch, eligible=True, persist_calls=persist_calls)

    result = pipeline_graph.invoke(_initial_state(), config=_config())

    payload = extract_interrupt_payload(result)
    assert payload is not None
    assert payload["shortlist_size"] == 1
    shortlist_names = {item["candidate_name"] for item in payload["shortlist"]}
    other_names = {item["candidate_name"] for item in payload["other_candidates"]}
    assert shortlist_names == {"Alice"}
    assert other_names == {"Bob"}
    assert persist_calls == []


def test_no_eligible_candidates_short_circuits(monkeypatch):
    rerank_calls = []
    persist_calls = []
    _patch_pipeline_services(monkeypatch, eligible=False, rerank_calls=rerank_calls, persist_calls=persist_calls)

    result = pipeline_graph.invoke(_initial_state(), config=_config())

    assert "__interrupt__" not in result
    assert result["status"] == "no_eligible_candidates"
    assert rerank_calls == []
    assert persist_calls == []


def test_resume_approve_persists(monkeypatch):
    persist_calls = []
    _patch_pipeline_services(monkeypatch, eligible=True, persist_calls=persist_calls)

    config = _config()
    pipeline_graph.invoke(_initial_state(), config=config)

    result = pipeline_graph.invoke(Command(resume={"action": "approve"}), config=config)

    assert result["status"] == "persisted"
    assert len(persist_calls) == 1
    # merge_rerank_results already carries every first-pass candidate forward,
    # not just the top_n shortlist - approving persists everyone as-is.
    assert {item["candidate_name"] for item in persist_calls[0]["results"]} == {"Alice", "Bob"}
    assert result["persistence_result"]["run_id"] == 1


def test_resume_reject_does_not_persist(monkeypatch):
    persist_calls = []
    _patch_pipeline_services(monkeypatch, eligible=True, persist_calls=persist_calls)

    config = _config()
    pipeline_graph.invoke(_initial_state(), config=config)

    result = pipeline_graph.invoke(Command(resume={"action": "reject"}), config=config)

    assert result["status"] == "rejected"
    assert persist_calls == []


def test_resume_edit_with_edited_results_overrides_persisted_list(monkeypatch):
    persist_calls = []
    _patch_pipeline_services(monkeypatch, eligible=True, persist_calls=persist_calls)

    config = _config()
    pipeline_graph.invoke(_initial_state(), config=config)

    custom_results = [{"candidate_name": "Custom Pick"}]
    result = pipeline_graph.invoke(
        Command(resume={"action": "edit", "edited_results": custom_results}),
        config=config,
    )

    assert result["status"] == "persisted"
    assert persist_calls[0]["results"] == custom_results


def test_resume_edit_with_manual_addition_flags_existing_non_shortlisted_candidate(monkeypatch):
    # Bob is already present in reranked["results"] (merge_rerank_results carries
    # everyone forward) but was never LLM-shortlisted - this is the "recruiter felt
    # they were exceptional in interview despite not being shortlisted" scenario.
    persist_calls = []
    _patch_pipeline_services(monkeypatch, eligible=True, persist_calls=persist_calls)

    config = _config()
    pipeline_graph.invoke(_initial_state(), config=config)

    result = pipeline_graph.invoke(
        Command(
            resume={
                "action": "edit",
                "manual_additions": [
                    {
                        "candidate_name": "Bob",
                        "override_reason": "Exceptional in interview despite resume gap.",
                        "added_by": "recruiter@example.com",
                    }
                ],
            }
        ),
        config=config,
    )

    assert result["status"] == "persisted"
    persisted = persist_calls[0]["results"]
    bobs = [item for item in persisted if item["candidate_name"] == "Bob"]
    assert len(bobs) == 1, "manual addition must not duplicate an already-present candidate"

    bob = bobs[0]
    assert bob["manually_added"] is True
    assert bob["final_score"] == 70
    assert bob["experience_relevance"] is None
    assert bob["override_reason"] == "Exceptional in interview despite resume gap."
    assert bob["added_by"] == "recruiter@example.com"


def test_resume_edit_with_manual_addition_appends_candidate_missing_from_reranked_results(monkeypatch):
    # Defensive fallback: if a candidate is somehow absent from reranked["results"]
    # entirely, the manual addition should pull their first-pass data from
    # batch_ranking and append it, rather than silently dropping the request.
    persist_calls = []

    def fake_rank(jd, candidates):
        batch = _batch_ranking(eligible=True)
        batch["results"].append(
            {
                "candidate_name": "Carol",
                "email": "carol@example.com",
                "is_eligible": False,
                "overall_score": 55,
                "rank": 3,
            }
        )
        return batch

    def fake_rerank(jd, batch_rankings, candidates, top_n=10):
        # Carol is intentionally omitted, unlike real merge_rerank_results.
        return _reranked(eligible=True)

    def fake_persist(rankings, run_name, source_file="api_payload"):
        persist_calls.append(rankings)
        return {"run_id": 1, "saved_rankings": len(rankings.get("results", []))}

    monkeypatch.setattr("backend.app.services.ranking_service.rank_candidates_for_jd", fake_rank)
    monkeypatch.setattr("backend.app.services.reranking_service.rerank_shortlist_for_jd", fake_rerank)
    monkeypatch.setattr("backend.app.services.persistence_service.save_rankings_payload", fake_persist)

    config = _config()
    pipeline_graph.invoke(_initial_state(), config=config)

    result = pipeline_graph.invoke(
        Command(
            resume={
                "action": "edit",
                "manual_additions": [
                    {"candidate_name": "Carol", "override_reason": "Strong take-home exercise."}
                ],
            }
        ),
        config=config,
    )

    assert result["status"] == "persisted"
    carol = next(item for item in persist_calls[0]["results"] if item["candidate_name"] == "Carol")
    assert carol["manually_added"] is True
    assert carol["final_score"] == 55
    assert carol["override_reason"] == "Strong take-home exercise."
