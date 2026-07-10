from typing import Any

from pipeline.shortlist_reranker import (
    build_shortlist_payload,
    build_summary,
    candidate_lookup,
    merge_rerank_results,
    rerank_experience_relevance,
)


def rerank_shortlist_for_jd(
    jd: dict[str, Any],
    batch_rankings: dict[str, Any],
    candidates: list[dict[str, Any]],
    top_n: int = 10,
) -> dict[str, Any]:
    candidates_by_name = candidate_lookup(candidates)
    first_pass_results = batch_rankings["results"]
    shortlist_payload = build_shortlist_payload(first_pass_results, candidates_by_name, top_n)
    rerank_results = rerank_experience_relevance(shortlist_payload, jd)
    final_results = merge_rerank_results(first_pass_results, rerank_results)

    return {
        "job_title": jd.get("job_title"),
        "ranking_rule": "Eligible candidates first, then final_score. final_score = 60% first-pass overall + 40% LLM experience relevance for shortlisted candidates.",
        "shortlist_size": len(shortlist_payload),
        "summary": build_summary(final_results),
        "results": final_results,
    }
