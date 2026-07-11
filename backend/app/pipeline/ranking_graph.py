from typing import Any, Literal, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt


class PipelineState(TypedDict, total=False):
    jd: dict[str, Any]
    candidates: list[dict[str, Any]]
    run_name: str
    source_file: str
    top_n: int
    batch_ranking: dict[str, Any]
    eligible_count: int
    reranked: dict[str, Any]
    review_decision: dict[str, Any]
    persistence_result: dict[str, Any]
    status: str


def rank_node(state: PipelineState) -> dict:
    from backend.app.services.ranking_service import rank_candidates_for_jd

    batch_ranking = rank_candidates_for_jd(jd=state["jd"], candidates=state["candidates"])
    eligible_count = sum(1 for result in batch_ranking["results"] if result.get("is_eligible"))
    return {"batch_ranking": batch_ranking, "eligible_count": eligible_count, "status": "ranked"}


def no_eligible_node(state: PipelineState) -> dict:
    return {"status": "no_eligible_candidates"}


def rerank_node(state: PipelineState) -> dict:
    from backend.app.services.reranking_service import rerank_shortlist_for_jd

    reranked = rerank_shortlist_for_jd(
        jd=state["jd"],
        batch_rankings=state["batch_ranking"],
        candidates=state["candidates"],
        top_n=state.get("top_n", 10),
    )
    return {"reranked": reranked, "status": "reranked"}


def build_review_payload(reranked: dict, batch_ranking: dict) -> dict:
    # rerank_shortlist_for_jd carries *every* first-pass candidate forward into
    # "results"/"summary" - top_n only controls who actually gets an LLM relevance
    # call, not who's present in the output. So "shortlisted" vs "everyone else" is
    # derived by whether experience_relevance_score is set, not by list membership.
    summary = reranked.get("summary") or []
    shortlisted = [item for item in summary if item.get("experience_relevance_score") is not None]
    other_candidates = [item for item in summary if item.get("experience_relevance_score") is None]

    return {
        "type": "shortlist_review",
        "job_title": reranked.get("job_title"),
        "shortlist_size": reranked.get("shortlist_size"),
        "shortlist": shortlisted,
        "other_candidates": other_candidates,
        "message": (
            "Review the shortlist. Resume with action='approve' to persist as-is, "
            "action='edit' (optionally with manual_additions and/or edited_results) "
            "to persist a modified list, or action='reject' to discard this run. "
            "manual_additions lets you flag a candidate from other_candidates "
            "(e.g. one who interviewed well but wasn't LLM-shortlisted) with a reason."
        ),
    }


def apply_review_decision(reranked: dict, batch_ranking: dict, decision: dict) -> dict:
    """Applies an approve/edit/reject decision to a reranked payload.

    Pure function (no graph/state dependency) so it can be reused both by
    human_review_node (same-process resume via the graph) and by the
    MySQL-backed /pipeline/resume route (durable resume, works even after a
    process restart - see backend/app/pipeline_review_repository.py).
    Returns the updated reranked dict; only meaningful when action == "edit".
    """
    results = list(reranked.get("results", []))

    edited_results = decision.get("edited_results")
    if edited_results is not None:
        results = list(edited_results)

    manual_additions = decision.get("manual_additions") or []
    if manual_additions:
        results_by_name = {result["candidate_name"]: result for result in results}
        batch_results_by_name = {
            result["candidate_name"]: result for result in batch_ranking.get("results", [])
        }

        for addition in manual_additions:
            name = addition.get("candidate_name")
            override_reason = addition.get("override_reason")
            added_by = addition.get("added_by")

            existing = results_by_name.get(name)
            if existing is not None:
                existing["manually_added"] = True
                existing["override_reason"] = override_reason
                existing["added_by"] = added_by
                continue

            source = batch_results_by_name.get(name)
            if source is None:
                continue

            new_entry = {
                **source,
                "experience_relevance": None,
                "final_score": source.get("overall_score"),
                "manually_added": True,
                "override_reason": override_reason,
                "added_by": added_by,
            }
            results.append(new_entry)
            results_by_name[name] = new_entry

    return {**reranked, "results": results}


def human_review_node(state: PipelineState) -> dict:
    reranked = state["reranked"]
    batch_ranking = state["batch_ranking"]

    decision = interrupt(build_review_payload(reranked, batch_ranking))

    action = decision.get("action", "reject")
    updates: dict[str, Any] = {"review_decision": decision}

    if action != "edit":
        updates["status"] = "approved" if action == "approve" else "rejected"
        return updates

    updates["reranked"] = apply_review_decision(reranked, batch_ranking, decision)
    updates["status"] = "approved"
    return updates


def persist_node(state: PipelineState) -> dict:
    from backend.app.services.persistence_service import save_rankings_payload

    result = save_rankings_payload(
        rankings=state["reranked"],
        run_name=state.get("run_name", "LangGraph pipeline run"),
        source_file=state.get("source_file", "langgraph_pipeline"),
    )
    return {"persistence_result": result, "status": "persisted"}


def reject_end_node(state: PipelineState) -> dict:
    return {"status": "rejected"}


def route_after_ranking(state: PipelineState) -> Literal["rerank", "no_eligible"]:
    return "rerank" if state.get("eligible_count", 0) > 0 else "no_eligible"


def route_after_review(state: PipelineState) -> Literal["persist", "reject_end"]:
    action = state.get("review_decision", {}).get("action")
    return "persist" if action in ("approve", "edit") else "reject_end"


def build_pipeline_graph():
    builder = StateGraph(PipelineState)
    builder.add_node("rank", rank_node)
    builder.add_node("no_eligible", no_eligible_node)
    builder.add_node("rerank", rerank_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("persist", persist_node)
    builder.add_node("reject_end", reject_end_node)

    builder.add_edge(START, "rank")
    builder.add_conditional_edges(
        "rank", route_after_ranking, {"rerank": "rerank", "no_eligible": "no_eligible"}
    )
    builder.add_edge("no_eligible", END)
    builder.add_edge("rerank", "human_review")
    builder.add_conditional_edges(
        "human_review", route_after_review, {"persist": "persist", "reject_end": "reject_end"}
    )
    builder.add_edge("persist", END)
    builder.add_edge("reject_end", END)

    return builder.compile(checkpointer=InMemorySaver())


pipeline_graph = build_pipeline_graph()


def extract_interrupt_payload(result: dict) -> dict | None:
    interrupts = result.get("__interrupt__")
    if not interrupts:
        return None
    first = interrupts[0]
    return getattr(first, "value", first)
