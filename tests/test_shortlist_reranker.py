import shortlist_reranker
from shortlist_reranker import (
    build_shortlist_payload,
    candidate_lookup,
    merge_rerank_results,
    rerank_experience_relevance,
)
from tests._fakes import FakeGenAIClient


def test_candidate_lookup_indexes_by_name():
    candidates = [{"name": "Alice"}, {"name": "Bob"}]
    lookup = candidate_lookup(candidates)
    assert lookup["Alice"]["name"] == "Alice"
    assert lookup["Bob"]["name"] == "Bob"


def test_build_shortlist_payload_limits_to_top_n():
    first_pass_results = [
        {
            "candidate_name": f"Candidate {i}",
            "rank": i,
            "overall_score": 100 - i,
            "is_eligible": True,
            "eligibility": {"missing_must_haves": []},
            "match_scores": {
                "skills": {"matched": []},
                "experience": {"years_experience": 2},
            },
        }
        for i in range(1, 5)
    ]
    candidates_by_name = {r["candidate_name"]: {} for r in first_pass_results}

    payload = build_shortlist_payload(first_pass_results, candidates_by_name, top_n=2)

    assert len(payload) == 2
    assert payload[0]["candidate_name"] == "Candidate 1"


def test_merge_rerank_results_blends_scores_and_ranks():
    first_pass = [
        {"candidate_name": "Alice", "overall_score": 80, "is_eligible": True, "rank": 1},
        {"candidate_name": "Bob", "overall_score": 90, "is_eligible": True, "rank": 2},
    ]
    rerank_results = [
        {"candidate_name": "Alice", "experience_relevance_score": 100},
        {"candidate_name": "Bob", "experience_relevance_score": 0},
    ]

    merged = merge_rerank_results(first_pass, rerank_results)

    alice = next(item for item in merged if item["candidate_name"] == "Alice")
    bob = next(item for item in merged if item["candidate_name"] == "Bob")

    assert alice["final_score"] == round(80 * 0.6 + 100 * 0.4, 2)
    assert bob["final_score"] == round(90 * 0.6 + 0 * 0.4, 2)
    # Alice's blended score (88) beats Bob's (54) despite lower first-pass rank.
    assert merged[0]["candidate_name"] == "Alice"
    assert merged[0]["final_rank"] == 1


def test_rerank_experience_relevance_success_parses_response(monkeypatch):
    fake_text = (
        '[{"candidate_name": "Alice", "experience_relevance_score": 88, '
        '"seniority_fit": "strong", "domain_fit": "strong", "reason": "Relevant.", '
        '"matched": [], "missing": [], "evidence": []}]'
    )
    monkeypatch.setattr(shortlist_reranker, "client", FakeGenAIClient(response_text=fake_text))

    shortlist_payload = [{"candidate_name": "Alice", "first_pass_overall_score": 80}]
    results = rerank_experience_relevance(shortlist_payload, {"job_title": "Backend Engineer"})

    assert results[0]["experience_relevance_score"] == 88


def test_rerank_experience_relevance_malformed_json_falls_back_to_first_pass_score(monkeypatch):
    monkeypatch.setattr(shortlist_reranker, "client", FakeGenAIClient(response_text="not json"))

    shortlist_payload = [
        {"candidate_name": "Alice", "first_pass_overall_score": 80},
        {"candidate_name": "Bob", "first_pass_overall_score": 65},
    ]
    results = rerank_experience_relevance(shortlist_payload, {"job_title": "Backend Engineer"})

    for item in results:
        source = next(c for c in shortlist_payload if c["candidate_name"] == item["candidate_name"])
        assert item["experience_relevance_score"] == source["first_pass_overall_score"]
        assert item["seniority_fit"] == "not_evaluated"